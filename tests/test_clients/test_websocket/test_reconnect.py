"""
Live reconnection tests.

The offline suite in test_reconnect_resubscribe.py covers the reconnect logic
against a venue we control, in seconds. These cover what a fake venue cannot:
the real subscribe ack shape, re-authentication actually restoring a *private*
channel, and whether cancel-on-disconnect survives a reconnect.
"""

import asyncio
import contextlib
import uuid
from decimal import Decimal

import pytest

from derive_py import WebSocketClient
from derive_py.data_types import ConnectionState
from derive_py.data_types.channel_models import TickerSlimPayload
from derive_py.data_types.generated_models import Direction

INTERVAL = 1000
PUBLIC_CHANNEL = f"ticker_slim.ETH-PERP.{INTERVAL}"

MESSAGE_TIMEOUT = 15
RECONNECT_TIMEOUT = 60

# A resting buy: far enough below market not to fill.
ORDER_INSTRUMENT = "ETH-PERP"
ORDER_AMOUNT = Decimal("0.1")
ORDER_PRICE_FACTOR = Decimal("0.5")

# The venue detects an aborted connection on its own schedule, which is slower
# than a close frame. This bounds how long that is allowed to take.
CANCEL_TIMEOUT = 60


async def _wait_until(predicate, timeout: float, message: str) -> None:
    """Poll until predicate holds, rather than sleeping a guessed span."""

    try:
        async with asyncio.timeout(timeout):
            while not await predicate():
                await asyncio.sleep(0.2)
    except TimeoutError:
        pytest.fail(f"{message} within {timeout}s")


@contextlib.contextmanager
def _recorded_states(client: WebSocketClient):
    """Record every state transition, then put the callback back.

    The client fixture is session-scoped, so a callback left installed would
    keep recording into a finished test's list.
    """

    seen: list[ConnectionState] = []
    previous = client.on_state_change
    client.on_state_change = seen.append
    try:
        yield seen
    finally:
        client.on_state_change = previous


async def _seen(states: list[ConnectionState], state: ConnectionState) -> bool:
    return state in states


async def _drop_and_recover(client: WebSocketClient, seen: list[ConnectionState]) -> None:
    """Abort the socket and wait until the session is usable again.

    A TCP abort, not a close frame: an orderly close is the easy path and not
    the one that breaks reconnection.
    """

    seen.clear()
    session = client._session
    assert session._ws is not None, "not connected, nothing to drop"
    session._ws.transport.abort()

    await _wait_until(
        lambda: _seen(seen, ConnectionState.RECONNECTING),
        RECONNECT_TIMEOUT,
        "the drop was never reported",
    )
    # CONNECTED is published only once re-auth and every channel have come
    # back, so this is the reconnect completing, not a socket opening.
    await _wait_until(
        lambda: _seen(seen, ConnectionState.CONNECTED),
        RECONNECT_TIMEOUT,
        "the session never became usable again",
    )
    assert client.connection_state is ConnectionState.CONNECTED


async def _resting_bid_price(client_admin_wallet: WebSocketClient) -> Decimal:
    """A price that will not fill: a fraction of the current best bid."""

    ticker = await client_admin_wallet.markets.get_ticker(instrument_name=ORDER_INSTRUMENT)
    reference = Decimal(str(ticker.best_bid_price or ticker.mark_price))
    assert reference > 0, f"no reference price for {ORDER_INSTRUMENT}"
    return reference * ORDER_PRICE_FACTOR


@pytest.mark.asyncio
async def test_an_abrupt_drop_restores_both_channels(client_admin_wallet: WebSocketClient):
    """
    Test that an abrupt drop restores a public and a private channel.

    The private one is the point: it can only be subscribed on an
    authenticated connection, so its return is the proof that the re-auth hook
    ran on the new socket and that the venue accepted it.
    """

    subaccount_id = client_admin_wallet.active_subaccount.id
    private_channel = f"{subaccount_id}.orders"

    messages: list = []
    received = asyncio.Event()

    def on_ticker(payload):
        messages.append(payload)
        received.set()

    def on_order(_payload):
        return None

    async def delivered() -> bool:
        return received.is_set()

    try:
        with _recorded_states(client_admin_wallet) as seen:
            await client_admin_wallet.public_channels.ticker_slim_interval_by_instrument_name(
                instrument_name="ETH-PERP",
                interval=INTERVAL,
                callback=on_ticker,
            )
            await client_admin_wallet.private_channels.orders_by_subaccount_id(
                subaccount_id=str(subaccount_id),
                callback=on_order,
            )

            await _wait_until(delivered, MESSAGE_TIMEOUT, "the public channel never delivered before the drop")
            assert isinstance(messages[0], TickerSlimPayload)

            received.clear()
            delivered_before_drop = len(messages)

            await _drop_and_recover(client_admin_wallet, seen)

            await _wait_until(delivered, MESSAGE_TIMEOUT, "reconnected, but the public channel is silent")
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


@pytest.mark.asyncio
async def test_cancel_on_disconnect_survives_a_reconnect(client_admin_wallet: WebSocketClient):
    """
    Test that cancel-on-disconnect still fires after the session has reconnected.

    Two drops, deliberately. The first shows the setting works at all; the
    second shows it was not scoped to the connection it was set on. If it is,
    every drop after the first leaves the book exposed while the client looks
    perfectly healthy.
    """

    orders = client_admin_wallet.orders
    run = uuid.uuid4().hex[:8]

    async def open_orders(label: str) -> list:
        return [order for order in await orders.list_open() if order.label == label]

    async def rest_an_order(label: str) -> None:
        await orders.create(
            amount=ORDER_AMOUNT,
            direction=Direction.buy,
            instrument_name=ORDER_INSTRUMENT,
            limit_price=await _resting_bid_price(client_admin_wallet),
            label=label,
        )
        resting = await open_orders(label)
        assert len(resting) == 1, f"expected one resting order for {label}, found {len(resting)}"

    try:
        await orders.cancel_all()
        await client_admin_wallet.set_cancel_on_disconnect(enabled=True)

        account = await client_admin_wallet.account.get()
        assert account.cancel_on_disconnect is True, "the venue did not record cancel-on-disconnect as enabled"

        with _recorded_states(client_admin_wallet) as seen:
            # First drop: does it work at all.
            await rest_an_order(f"{run}-1")
            await _drop_and_recover(client_admin_wallet, seen)
            await _wait_until(
                lambda: open_orders(f"{run}-1"),
                CANCEL_TIMEOUT,
                "cancel-on-disconnect did not cancel the order",
            )

            # Second drop: was it scoped to the connection it was set on.
            await rest_an_order(f"{run}-2")
            await _drop_and_recover(client_admin_wallet, seen)
            await _wait_until(
                lambda: open_orders(f"{run}-2"),
                CANCEL_TIMEOUT,
                "cancel-on-disconnect did not survive the reconnect: it is scoped to "
                "the connection it was set on and has to be re-applied",
            )

    finally:
        with contextlib.suppress(Exception):
            await client_admin_wallet.set_cancel_on_disconnect(enabled=False)
        with contextlib.suppress(Exception):
            await orders.cancel_all()


@pytest.mark.asyncio
async def test_state_transitions_are_reported_in_order(client_admin_wallet: WebSocketClient):
    """
    Test that a drop is reported, in order, and never claims to be usable early.

    Out-of-order delivery would be worse than no signal: a caller told
    CONNECTED while the socket is gone believes it is safe to trade.
    """

    with _recorded_states(client_admin_wallet) as seen:
        assert client_admin_wallet.connection_state is ConnectionState.CONNECTED
        await _drop_and_recover(client_admin_wallet, seen)

    assert seen[-1] is ConnectionState.CONNECTED, f"did not end connected: {seen}"
    assert ConnectionState.CONNECTED not in seen[:-1], f"claimed connected mid-outage: {seen}"
    assert ConnectionState.RECONNECTING in seen, f"never reported reconnecting: {seen}"
    assert all(a is not b for a, b in zip(seen, seen[1:])), f"repeated a state: {seen}"
