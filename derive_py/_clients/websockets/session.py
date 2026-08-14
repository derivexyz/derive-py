"""
Asynchronous WebSocket session with automatic reconnection and auth hook.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import random
import uuid
import weakref
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Iterable, Optional, Type, cast

import msgspec
from msgspec import ValidationError
from websockets import Data
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from derive_py._clients.utils import (
    JSONRPCEnvelope,
    RequestParams,
    SubscriptionParams,
    UnsubscribeResult,
    confirm_subscriptions,
    decode_envelope,
    decode_result,
    decoder_for,
    encode_rpc_frame,
)
from derive_py.config import USER_AGENT
from derive_py.data_types import ConnectionState, LoggerType, WebSocketSessionConfig
from derive_py.exceptions import DeriveJSONRPCError, RequestAbandoned
from derive_py.utils.logger import get_logger

if TYPE_CHECKING:
    from derive_py._clients.websockets.api import Handler, MessageT

LifecycleCallback = Callable[[], None] | Callable[[], Awaitable[None]]
StateCallback = Callable[[ConnectionState], None] | Callable[[ConnectionState], Awaitable[None]]


class Subscribe(msgspec.Struct):
    channels: list[str]


@dataclass(slots=True)
class Subscription:
    """A channel's handler and the decoder for its payload type."""

    handler: Handler
    decoder: msgspec.json.Decoder


class ConnectionTracker:
    """Task-safe connection state tracking.

    Two flags rather than one state, because they have different owners: the
    receiver clears `connected`, the reconnect loop owns `reconnecting`.
    `state` is the caller's view of the pair, and connected wins, so a
    reconnect that has restored the session reads as connected whatever its
    claim still says.

    Every transition passes through here, so publishing from inside the lock
    is the one place it cannot be forgotten and cannot arrive out of order.
    """

    def __init__(self, on_change: Callable[[ConnectionState], None] | None = None):
        self._lock = asyncio.Lock()
        self._connected = False
        self._reconnecting = False
        self._on_change = on_change
        self._published = ConnectionState.DISCONNECTED

    @property
    def state(self) -> ConnectionState:
        """The pair as one state."""
        if self._connected:
            return ConnectionState.CONNECTED
        return ConnectionState.RECONNECTING if self._reconnecting else ConnectionState.DISCONNECTED

    def _publish(self) -> None:
        """Announce a transition. Call inside the lock, after mutating."""
        if (current := self.state) is self._published:
            return
        self._published = current
        if self._on_change is not None:
            self._on_change(current)

    async def set_connected(self):
        async with self._lock:
            self._connected = True
            self._publish()

    async def set_connected_if(self, still_valid: Callable[[], bool]) -> bool:
        """Mark connected only while `still_valid` holds.

        Tested and set under the lock a disconnect also takes, so a drop cannot
        land between the two and leave the session claiming a socket that has
        already gone.
        """
        async with self._lock:
            if not still_valid():
                return False
            self._connected = True
            self._publish()
            return True

    async def set_disconnected(self):
        async with self._lock:
            self._connected = False
            self._publish()

    async def begin_reconnect(self) -> bool:
        """Claim the reconnect. False if another loop already holds it."""
        async with self._lock:
            if self._reconnecting:
                return False
            self._reconnecting = True
            self._publish()
            return True

    async def end_reconnect(self) -> bool:
        """Release the claim. True if the session still needs a reconnect."""
        # Released and observed under one lock: a drop that lands while a loop
        # is finishing cannot claim the reconnect, so it has to be seen here.
        async with self._lock:
            self._reconnecting = False
            self._publish()
            return not self._connected

    async def is_connected(self) -> bool:
        async with self._lock:
            return self._connected

    async def is_reconnecting(self) -> bool:
        async with self._lock:
            return self._reconnecting


class WebSocketSession:
    """Asynchronous WebSocket session with automatic reconnection."""

    _on_disconnect: LifecycleCallback | None
    _on_reconnect: LifecycleCallback | None
    _on_before_resubscribe: LifecycleCallback | None

    def __init__(
        self,
        *,
        url: str,
        config: WebSocketSessionConfig | None = None,
        logger: LoggerType | None = None,
        on_disconnect: LifecycleCallback | None = None,
        on_reconnect: LifecycleCallback | None = None,
        on_before_resubscribe: LifecycleCallback | None = None,
        on_state_change: StateCallback | None = None,
    ):
        """
        Args:
            url: WebSocket URL
            config: Transport and reconnection settings
            logger: Logger instance
            on_disconnect: Callback when disconnection is detected
            on_reconnect: Callback after successful reconnection (before resubscribe)
            on_before_resubscribe: Callback before resubscribing channels (for re-auth)
            on_state_change: Callback for connection state transitions
        """
        self._url = url
        self._config = config if config is not None else WebSocketSessionConfig()
        self._logger = logger if logger is not None else get_logger()

        # Live value, seeded from the config: timeout() overrides it per block,
        # and the config is frozen and may be shared between sessions.
        self._request_timeout = self._config.request_timeout

        self._on_disconnect = on_disconnect
        self._on_reconnect = on_reconnect
        self._on_before_resubscribe = on_before_resubscribe

        # Connection state. The queue and its task keep a slow or failing
        # callback off the reconnect path while preserving arrival order.
        self._ws: ClientConnection | None = None
        self._on_state_change = on_state_change
        self._state_queue: asyncio.Queue[ConnectionState] = asyncio.Queue()
        self._notifier_task: asyncio.Task | None = None
        self._state = ConnectionTracker(on_change=self._state_queue.put_nowait)

        # Message routing; one subscription per channel
        self._subscriptions: dict[str, Subscription] = {}

        # RPC tracking
        self._pending_requests: dict[str | int, asyncio.Queue] = {}

        # Background tasks
        self._receiver_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

        # Cleanup
        self._finalizer = weakref.finalize(self, self._finalize, logger=self._logger)

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state.state

    @property
    def on_state_change(self) -> StateCallback | None:
        """Callback for connection state transitions. Settable after construction."""
        return self._on_state_change

    @on_state_change.setter
    def on_state_change(self, callback: StateCallback | None) -> None:
        self._on_state_change = callback

    async def open(self) -> None:
        """Establish WebSocket connection, start receiver task, restore channels."""
        if self._notifier_task is None or self._notifier_task.done():
            self._notifier_task = asyncio.create_task(self._notify_state_changes(), name="ws-state-notifier")

        if await self._state.is_connected():
            self._logger.warning("WebSocket already connected")
            return

        if await self._state.is_reconnecting():
            # Dialling under the reconnect would orphan one of the two sockets.
            self._logger.warning("Reconnection in progress, not opening a second connection")
            return

        await self._connect()
        try:
            # Subscriptions survive close(), so reopening has to restore them.
            if self._subscriptions:
                await self._before_resubscribe()
                await self._resubscribe_all()
        except Exception:
            # A part-way open looks healthy to the venue and delivers nothing,
            # and the next open() would dial on top of its receiver.
            await self._close_connection()
            raise

        await self._state.set_connected()

    async def close(self) -> None:
        """Close connection and stop all tasks. Idempotent."""
        if self._ws is None and not await self._state.is_reconnecting() and self._notifier_task is None:
            return

        self._logger.info("Closing WebSocket session")
        self._stop_event.set()

        # Stop the reconnect loop first: one that is already past its stop
        # check can finish dialling and leave a fresh socket behind us.
        await self._cancel(self._reconnect_task)
        self._reconnect_task = None

        # Close WebSocket, which also stops the receiver task
        await self._close_connection()

        await self._state.set_disconnected()
        await self._fail_pending_requests("session closed")

        # Deliver the transitions this close produced before stopping.
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._state_queue.join(), timeout=5.0)
        await self._cancel(self._notifier_task)
        self._notifier_task = None

        self._logger.info("WebSocket session closed")

    @property
    def subscriptions(self) -> tuple[str, ...]:
        """Channels this session holds a handler for, in subscription order."""
        return tuple(self._subscriptions)

    async def subscribe(
        self,
        channel: str,
        handler: Handler[MessageT],
        notification_type: Optional[Type[MessageT]] = None,
    ) -> JSONRPCEnvelope:
        """
        Subscribe to a channel with a handler.

        Only one handler allowed per channel. If channel already has a handler,
        replaces it and logs a warning.

        Args:
            channel: Channel name (e.g., "BTC-PERP.trades")
            handler: Callback function(data) or async function to handle messages
            notification_type: Type to decode notifications into. Omitting it
                yields plain Python objects rather than a typed payload.

        Returns:
            JSONRPCEnvelope with subscription confirmation
        """
        if not await self._state.is_connected():
            raise RuntimeError("WebSocket not connected. Call open() first.")

        if channel in self._subscriptions:
            self._logger.warning(
                f"Channel {channel} already has a handler - replacing it. "
                "Consider using unsubscribe() first for explicit control."
            )

        # decoder_for is cached, so channels sharing a payload type share a
        # decoder and parameterised generics resolve only once per process.
        decoder = decoder_for(notification_type if notification_type is not None else Any)
        self._subscriptions[channel] = Subscription(handler=handler, decoder=decoder)

        params = Subscribe(channels=[channel])

        self._logger.info(f"Subscribing to channel: {channel}")
        try:
            envelope = await self._send_request("subscribe", params=params)
            # A handler kept for a channel that never subscribed is silent for
            # the life of the session, and asked for again on every reconnect.
            confirmed, refused = confirm_subscriptions([channel], envelope)
            if not confirmed:
                raise ConnectionError(f"{channel} is not subscribed: the venue refuses it ({refused[channel]})")
            self._logger.debug(f"Subscribe RPC response for {channel}: {envelope}")
            return envelope
        except Exception:
            # Rollback registration on failure
            self._subscriptions.pop(channel, None)
            self._logger.exception(f"Subscribe RPC failed for {channel}")
            raise

    async def unsubscribe(self, *channels: str) -> UnsubscribeResult | None:
        """
        Unsubscribe from one or more channels and drop their handlers.

        Handlers are dropped before the request goes out, not after. If the
        request fails the venue keeps sending a channel nothing here routes,
        which the next reconnect clears. Dropping them afterwards would instead
        leave a channel the caller asked to stop being resubscribed on every
        reconnect, which nothing clears.
        """

        requested = dict.fromkeys(channels)
        if unknown := requested.keys() - self._subscriptions.keys():
            self._logger.warning(f"Not subscribed to: {', '.join(sorted(unknown))}")

        known = [channel for channel in requested if channel not in unknown]
        if not known:
            return None

        for channel in known:
            del self._subscriptions[channel]

        self._logger.info(f"Unsubscribing from {len(known)} channels: {', '.join(known)}")
        try:
            envelope = await self._send_request("unsubscribe", {"channels": known})
        except Exception:
            self._logger.exception(f"Unsubscribe RPC failed for {', '.join(known)}")
            raise

        self._logger.debug(f"Unsubscribe RPC response: {envelope}")
        unsubscribe_result = decode_result(envelope, UnsubscribeResult)
        self._note_divergence(unsubscribe_result.remaining_subscriptions)
        return unsubscribe_result

    def _note_divergence(self, live: Iterable[str]) -> None:
        """Log where the venue's view of this connection differs from ours."""

        live = set(live)

        if stray := live - self._subscriptions.keys():
            self._logger.error(f"Subscribed at the venue with no handler here: {', '.join(sorted(stray))}")

        if missing := self._subscriptions.keys() - live:
            self._logger.warning(f"Registered here but not subscribed at the venue: {', '.join(sorted(missing))}")

    async def _connect(self) -> None:
        """Establish WebSocket connection and start receiver task.

        Does not mark the session connected: an open socket is not a usable
        session until its channels are back. Callers decide when that is true.
        """
        self._logger.info(f"Connecting to {self._url}")

        try:
            ws = await connect(
                self._url,
                user_agent_header=USER_AGENT,
                max_size=self._config.max_size,
                open_timeout=self._config.open_timeout,
                close_timeout=self._config.close_timeout,
                ping_interval=self._config.ping_interval,
                ping_timeout=self._config.ping_timeout,
            )
        except Exception as e:
            self._logger.error(f"Connection failed: {e}")
            raise

        self._ws = ws

        # Start receiver task, bound to the connection it was started for, so
        # it can never end up sharing a recv() with a newer connection.
        self._stop_event.clear()
        self._receiver_task = asyncio.create_task(self._receive_loop(ws), name="ws-receiver")

        self._logger.info("WebSocket connected, receiver task started")

    async def _cancel(self, task: asyncio.Task | None) -> None:
        """Cancel a task and wait for it, without adopting how it died."""
        # Callers are tearing a connection down; adopting the task's own
        # exception would abandon that teardown half-finished.
        if task is None or task.done() or task is asyncio.current_task():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.debug(f"Task {task.get_name()} ended with {e!r}")

    async def _close_connection(self) -> None:
        """Close the WebSocket connection and stop the receiver reading it."""
        # Cancelled before the socket closes, so the receiver cannot observe
        # the close and re-enter _handle_disconnect from inside a teardown.
        # Handlers run on the receiver, so one in flight is cancelled with it:
        # handlers are expected to be short, and a teardown must be bounded
        # even when the one we were handed is not.
        task, self._receiver_task = self._receiver_task, None
        await self._cancel(task)

        if self._ws:
            try:
                await self._ws.close()
            except Exception as e:
                self._logger.debug(f"Error closing WebSocket: {e}")
            finally:
                self._ws = None

        # Nothing is left to deliver a reply, so waiters are told now rather
        # than left to time out.
        await self._fail_pending_requests("connection closed")
        await self._state.set_disconnected()

    async def _handle_disconnect(self) -> None:
        """Handle disconnection and trigger reconnection if enabled."""
        if self._stop_event.is_set():
            return

        await self._state.set_disconnected()
        await self._fail_pending_requests("connection lost")
        self._logger.warning("WebSocket disconnected")

        # Start reconnection if enabled. The claim is atomic, so concurrent
        # disconnects cannot each start a loop. Before the hook, not after: a
        # hook that takes seconds must not delay the reconnect by seconds.
        if self._config.reconnect and await self._state.begin_reconnect():
            try:
                self._reconnect_task = asyncio.create_task(
                    self._reconnect_loop(),
                    name="ws-reconnect",
                )
            except Exception:
                # Nothing will release the claim if the loop never starts.
                await self._state.end_reconnect()
                raise

        # Notify user callback
        if self._on_disconnect is not None:
            try:
                res = self._on_disconnect()
                if inspect.isawaitable(res):
                    await cast(Awaitable[None], res)
            except Exception as e:
                self._logger.error(f"Error in on_disconnect callback: {e}")

    async def _notify_state_changes(self) -> None:
        """Deliver state transitions to the caller, in order.

        On its own task so a caller cancelling orders elsewhere cannot hold up
        the reconnect, and so one raising callback cannot end the stream.
        """
        while True:
            state = await self._state_queue.get()
            try:
                if (callback := self._on_state_change) is not None:
                    result = callback(state)
                    if inspect.isawaitable(result):
                        await result
            except Exception as e:
                self._logger.error(f"Error in on_state_change callback for {state}: {e}", exc_info=True)
            finally:
                self._state_queue.task_done()

    async def _reconnect_loop(self) -> None:
        """Reconnection loop with exponential backoff."""
        try:
            await self._reconnect_until_subscribed()
        finally:
            # Releasing here always: a stuck claim would strand the session.
            # A drop that landed while this loop was finishing could not claim
            # the reconnect, so it is handed a fresh loop instead.
            if await self._state.end_reconnect() and self._config.reconnect and not self._stop_event.is_set():
                self._logger.warning("Disconnected while finishing the reconnect, restarting")
                self._reconnect_task = asyncio.create_task(
                    self._reconnect_loop(),
                    name="ws-reconnect",
                )

    async def _reconnect_until_subscribed(self) -> None:
        """Dial, re-authenticate and resubscribe until the session is usable.

        Termination is not derived from the connected flag: another task can
        flip that at any time, and an open socket is not a restored session.
        """
        delay = self._config.reconnect_delay
        attempt = 1

        while not self._stop_event.is_set():
            # Jitter, so a server restart does not bring every client back in
            # lockstep and trip the venue's per-IP connection cap.
            wait = random.uniform(delay / 2, delay)
            self._logger.info(f"Reconnection attempt {attempt} in {wait:.1f}s")
            await asyncio.sleep(wait)

            if self._stop_event.is_set():
                break

            try:
                # Close old connection if exists
                await self._close_connection()

                # Establish new connection
                await self._connect()
                connection = self._ws

                # Call reconnect callback (for re-auth, etc.)
                if self._on_reconnect is not None:
                    try:
                        res = self._on_reconnect()
                        if inspect.isawaitable(res):
                            await cast(Awaitable[None], res)
                    except Exception as e:
                        self._logger.error(f"Error in on_reconnect callback: {e}")
                        # Don't fail reconnection if callback fails

                # Call before_resubscribe callback (for re-authentication)
                await self._before_resubscribe()

                # Resubscribe to all channels
                await self._resubscribe_all()

                # A drop in the window above leaves no receiver to report it,
                # and close_code is set by the transport before anything of
                # ours can observe the loss, so it is the reliable witness.
                still_ours = await self._state.set_connected_if(
                    lambda: connection is not None and self._ws is connection and connection.close_code is None
                )
                if not still_ours:
                    raise ConnectionError("connection dropped before resubscribing finished")

                self._logger.info(f"Reconnected successfully after {attempt} attempts")
                return

            except Exception as e:
                self._logger.error(f"Reconnection attempt {attempt} failed: {e}")
                # A part-way connection looks healthy and delivers nothing.
                await self._close_connection()
                attempt += 1
                delay = min(delay * 2, self._config.max_reconnect_delay)

        await self._state.set_disconnected()
        self._logger.info("Reconnection stopped")

    async def _before_resubscribe(self) -> None:
        """Run the re-auth callback. Its failure has to fail the attempt."""
        if self._on_before_resubscribe is None:
            return
        try:
            res = self._on_before_resubscribe()
            if inspect.isawaitable(res):
                await cast(Awaitable[None], res)
        except Exception as e:
            self._logger.error(f"Error in on_before_resubscribe callback: {e}")
            raise  # Re-auth failure should trigger retry

    async def _resubscribe_all(self) -> None:
        """Resubscribe every channel, and raise unless some came back."""
        channels = list(self._subscriptions)

        if not channels:
            self._logger.debug("No channels to resubscribe")
            return

        self._logger.info(f"Resubscribing to {len(channels)} channels")
        confirmed, refused = await self._subscribe_batch(channels)

        # Nothing subscribed is a connection failure - a rejected re-auth looks
        # exactly like this - but a channel the venue will not serve must not
        # fail the attempt, or one delisted instrument would end all market
        # data. It stays registered, is reported, and is tried again next time.
        if not confirmed:
            raise ConnectionError(f"no channel came back: {refused}")

        for channel, reason in refused.items():
            self._logger.error(f"{channel} is not subscribed: the venue refuses it ({reason})")

        self._logger.debug(f"Resubscribed to {len(confirmed)} channels")

    async def _subscribe_batch(self, channels: list[str]) -> tuple[list[str], dict[str, str]]:
        """Subscribe in one request, falling back to one at a time."""
        # One request, not one per channel: a trader profile has five
        # non-matching requests per second, which a channel at a time spends on
        # every reconnect. A single bad channel is answered with `Invalid
        # params` for the whole request, hence the fallback below.
        envelope = await self._send_request("subscribe", params=Subscribe(channels=channels))
        if envelope.error is msgspec.UNSET:
            return confirm_subscriptions(channels, envelope)

        self._logger.warning(f"Subscribe rejected for {len(channels)} channels at once, asking one at a time")
        confirmed: list[str] = []
        refused: dict[str, str] = {}
        for channel in channels:
            try:
                reply = await self._send_request("subscribe", params=Subscribe(channels=[channel]))
                accepted, rejected = confirm_subscriptions([channel], reply)
            except DeriveJSONRPCError as e:
                # The venue rejected this one channel. Anything else - an
                # abandoned request, a timeout - is the connection itself, and
                # has to fail the attempt rather than be filed as a refusal.
                refused[channel] = str(e)
                continue
            confirmed.extend(accepted)
            refused.update(rejected)
        return confirmed, refused

    async def _send_request(self, method: str, params: RequestParams) -> JSONRPCEnvelope:
        """Send RPC request and return decoded envelope."""
        # Bound once: the reconnect loop can replace self._ws while this
        # coroutine is suspended in send(), and the frame belongs to the socket
        # that was checked, not to whichever one exists on resumption.
        ws = self._ws
        if ws is None:
            raise RuntimeError("WebSocket not connected")

        request_id = str(uuid.uuid4())
        data = encode_rpc_frame(request_id, method, params)
        response_queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        self._pending_requests[request_id] = response_queue

        try:
            # UTF-8 bytes in a Text frame, which is what Derive accepts; it rejects Binary frames.
            await ws.send(data, text=True)

            try:
                envelope = await asyncio.wait_for(response_queue.get(), timeout=self._request_timeout)
                if isinstance(envelope, Exception):
                    raise envelope
                return envelope
            except asyncio.TimeoutError:
                self._logger.error(f"RPC timeout for {method} after {self._request_timeout}s")
                raise TimeoutError(f"RPC timeout after {self._request_timeout}s")

        finally:
            self._pending_requests.pop(request_id, None)

    async def _fail_pending_requests(self, reason: str) -> None:
        """Hand every in-flight RPC an exception rather than letting it time out."""
        pending, self._pending_requests = self._pending_requests, {}

        for request_id in pending:
            try:
                pending[request_id].put_nowait(RequestAbandoned(reason))
            except asyncio.QueueFull:
                self._logger.warning(f"Could not notify pending request {request_id}: {reason}")

    async def _receive_loop(self, ws: ClientConnection) -> None:
        """Background task: continuously receive and dispatch messages.

        Reads the connection it was started for, never whatever self._ws
        currently points at.
        """
        self._logger.info("Receiver task started")

        try:
            while not self._stop_event.is_set():
                try:
                    message = await ws.recv(decode=False)
                    try:
                        await self._dispatch_message(message)
                    except Exception:
                        self._logger.exception("Dispatch failed; message dropped")

                except TimeoutError:
                    continue

                except ConnectionClosed as e:
                    self._logger.warning(f"Connection closed: {e}")
                    await self._handle_disconnect()
                    break

                except Exception as e:
                    if not self._stop_event.is_set():
                        self._logger.error(f"Receive error: {e}", exc_info=True)
                        await self._handle_disconnect()
                    break

        finally:
            self._logger.info("Receiver task stopped")

    async def _dispatch_message(self, data: Data) -> None:
        """Decode one frame and route it to a waiter or a handler."""
        try:
            envelope = decode_envelope(data)
        except ValidationError as e:
            self._logger.warning(f"Unexpected envelope shape ({e}): {data[:200]!r}")
            return
        except Exception as e:
            self._logger.error(f"Failed to decode envelope: {e}")
            return

        # RPC response
        if envelope.id is not msgspec.UNSET:
            queue = self._pending_requests.get(envelope.id)

            if queue:
                try:
                    queue.put_nowait(envelope)
                except asyncio.QueueFull:
                    self._logger.warning(f"Failed to queue RPC response: {envelope.id}")
            else:
                self._logger.debug(f"No pending request for id: {envelope.id}")
            return

        # Subscription notification
        if envelope.method == "subscription":
            params = envelope.params

            if not isinstance(params, SubscriptionParams):
                self._logger.warning("Subscription message missing params")
                return

            subscription = self._subscriptions.get(params.channel)
            if subscription is None:
                self._logger.debug(f"No handler for channel: {params.channel}")
                return

            try:
                notification = subscription.decoder.decode(params.data)
            except ValidationError as e:
                self._logger.error(
                    f"Notification decode error for {params.channel}: {e} data: {bytes(params.data)!r}",
                    exc_info=True,
                )
                return

            await self._run_handler(params.channel, subscription.handler, notification)
            return

        # Other notification
        self._logger.debug(f"Unhandled notification: {envelope.method}")

    async def _run_handler(self, channel: str, handler: Handler, notification: Any) -> None:
        """Run handler (sync or async) in arrival order and catch exceptions.

        Handlers run on the receive loop, so a slow handler applies backpressure
        to the socket rather than racing the next message. That is the trade:
        per-channel ordering, which an orderbook feed requires, in exchange for
        a handler that must not block. Awaiting the returned value rather than
        testing iscoroutinefunction also handles partials and callable objects.

        A teardown cancels the receiver, so a handler in flight is cancelled
        with it. Handlers must not treat that as a failure to report.
        """
        try:
            result = handler(notification)
            if inspect.isawaitable(result):
                await result
        except Exception as e:
            self._logger.error(f"Handler error for {channel}: {e}", exc_info=True)

    @staticmethod
    def _finalize(logger: LoggerType) -> None:
        """Finalizer for cleanup."""
        logger.debug("WebSocketSession garbage collected without explicit close()")

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
