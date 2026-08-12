"""
Live reconnection test.

The offline suite in test_reconnect_resubscribe.py covers the reconnect logic
against a venue we control, in seconds. This covers the three things a fake
venue cannot: the real subscribe ack shape, re-authentication actually
restoring a *private* channel, and the batched resubscribe against the live
exchange.
"""

import asyncio
import contextlib

import pytest

from derive_client import WebSocketClient
from derive_client.data_types.channel_models import TickerSlimPayload

INTERVAL = 1000
PUBLIC_CHANNEL = f"ticker_slim.ETH-PERP.{INTERVAL}"

MESSAGE_TIMEOUT = 15
RECONNECT_TIMEOUT = 60


async def _wait_until(predicate, timeout: float, message: str) -> None:
    """Poll until predicate holds, rather than sleeping a guessed span."""

    try:
        async with asyncio.timeout(timeout):
            while not await predicate():
                await asyncio.sleep(0.2)
    except TimeoutError:
        pytest.fail(f"{message} within {timeout}s")


@contextlib.contextmanager
def _lifecycle_events(session):
    """Signal the session's disconnect and re-auth hooks, then put them back.

    The client fixture is session-scoped, so hooks left wrapped would fire for
    every later test.
    """

    events = {"disconnected": asyncio.Event(), "reauthenticated": asyncio.Event()}
    original_disconnect = session._on_disconnect
    original_reauth = session._on_before_resubscribe

    def on_disconnect():
        events["disconnected"].set()
        return original_disconnect() if original_disconnect else None

    async def on_before_resubscribe():
        if original_reauth:
            await original_reauth()
        # Set after, not before: a re-auth that raises must not look like one
        # that worked, since a failed attempt is retried.
        events["reauthenticated"].set()

    session._on_disconnect = on_disconnect
    session._on_before_resubscribe = on_before_resubscribe
    try:
        yield events
    finally:
        session._on_disconnect = original_disconnect
        session._on_before_resubscribe = original_reauth


@pytest.mark.asyncio
async def test_an_abrupt_drop_restores_both_channels(client_admin_wallet: WebSocketClient):
    """
    Test that an abrupt drop restores a public and a private channel.

    The private one is the point: it can only be subscribed on an
    authenticated connection, so its return is the proof that the re-auth hook
    ran on the new socket and that the venue accepted it.
    """

    session = client_admin_wallet._session
    subaccount_id = client_admin_wallet.active_subaccount.id
    private_channel = f"{subaccount_id}.orders"

    messages: list = []
    received = asyncio.Event()

    def on_ticker(payload):
        messages.append(payload)
        received.set()

    def on_order(_payload):
        return None

    try:
        with _lifecycle_events(session) as events:
            await client_admin_wallet.public_channels.ticker_slim_interval_by_instrument_name(
                instrument_name="ETH-PERP",
                interval=INTERVAL,
                callback=on_ticker,
            )
            await client_admin_wallet.private_channels.orders_by_subaccount_id(
                subaccount_id=str(subaccount_id),
                callback=on_order,
            )

            await _wait_until(
                lambda: asyncio.sleep(0, result=received.is_set()),
                MESSAGE_TIMEOUT,
                "the public channel never delivered before the drop",
            )
            assert isinstance(messages[0], TickerSlimPayload)

            # A TCP abort, not a close frame: an orderly close is the easy path
            # and not the one that breaks reconnection.
            assert session._ws is not None, "not connected, nothing to drop"
            session._ws.transport.abort()

            received.clear()
            delivered_before_drop = len(messages)

            await _wait_until(
                lambda: asyncio.sleep(0, result=events["disconnected"].is_set()),
                RECONNECT_TIMEOUT,
                "the drop was never detected",
            )
            await _wait_until(
                lambda: asyncio.sleep(0, result=events["reauthenticated"].is_set()),
                RECONNECT_TIMEOUT,
                "re-authentication never ran",
            )

            # The session is marked connected only once re-auth and every
            # channel have come back, so this is the reconnect completing, not
            # merely a socket opening.
            await _wait_until(
                session._state.is_connected,
                RECONNECT_TIMEOUT,
                "the session never became usable again",
            )

        await _wait_until(
            lambda: asyncio.sleep(0, result=received.is_set()),
            MESSAGE_TIMEOUT,
            "reconnected, but the public channel is silent",
        )
        assert len(messages) > delivered_before_drop
        assert isinstance(messages[-1], TickerSlimPayload)

        # Ask the venue what this connection holds. Our own registry keeps a
        # refused channel registered on purpose, so it cannot answer this.
        remaining = await client_admin_wallet.unsubscribe(PUBLIC_CHANNEL)
        assert remaining is not None
        assert private_channel in remaining.remaining_subscriptions, "the private channel did not survive the reconnect"

    finally:
        with contextlib.suppress(Exception):
            await client_admin_wallet.unsubscribe(PUBLIC_CHANNEL, private_channel)
