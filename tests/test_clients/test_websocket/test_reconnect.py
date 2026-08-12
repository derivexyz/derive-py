"""
Live reconnection tests.

The offline suite in test_reconnect_resubscribe.py covers the reconnect logic
against a venue we control, in seconds. These cover what a fake venue cannot:
the real subscribe ack shape, re-authentication actually restoring a *private*
channel, and whether cancel-on-disconnect survives a reconnect.

Two tests, deliberately. Everything else about reconnection is cheaper and
more thorough offline.
"""

import asyncio
import contextlib
import uuid
from decimal import Decimal

import pytest

from derive_client import WebSocketClient
from derive_client.data_types.channel_models import TickerSlimPayload
from derive_client.data_types.generated_models import Direction

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


async def _is_set(event: asyncio.Event) -> bool:
    """Adapt an Event to the predicate _wait_until expects."""

    return event.is_set()


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


async def _drop_and_recover(session, events) -> None:
    """Abort the socket and wait until the session is usable again.

    A TCP abort, not a close frame: an orderly close is the easy path and not
    the one that breaks reconnection.
    """

    events["disconnected"].clear()
    assert session._ws is not None, "not connected, nothing to drop"
    session._ws.transport.abort()

    await _wait_until(
        lambda: _is_set(events["disconnected"]),
        RECONNECT_TIMEOUT,
        "the drop was never detected",
    )
    # The session is marked connected only once re-auth and every channel have
    # come back, so this is the reconnect completing, not a socket opening.
    await _wait_until(
        session._state.is_connected,
        RECONNECT_TIMEOUT,
        "the session never became usable again",
    )


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
                lambda: _is_set(received),
                MESSAGE_TIMEOUT,
                "the public channel never delivered before the drop",
            )
            assert isinstance(messages[0], TickerSlimPayload)

            received.clear()
            delivered_before_drop = len(messages)

            await _drop_and_recover(session, events)

            await _wait_until(
                lambda: _is_set(received),
                MESSAGE_TIMEOUT,
                "reconnected, but the public channel is silent",
            )
            assert len(messages) > delivered_before_drop
            assert isinstance(messages[-1], TickerSlimPayload)

            await _wait_until(
                lambda: _is_set(events["reauthenticated"]),
                RECONNECT_TIMEOUT,
                "re-authentication never ran",
            )

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

    session = client_admin_wallet._session
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

        with _lifecycle_events(session) as events:
            # First drop: does it work at all.
            await rest_an_order(f"{run}-1")
            await _drop_and_recover(session, events)
            await _wait_until(
                lambda: open_orders(f"{run}-1"),
                CANCEL_TIMEOUT,
                "cancel-on-disconnect did not cancel the order",
            )

            # Second drop: was it scoped to the connection it was set on.
            await rest_an_order(f"{run}-2")
            await _drop_and_recover(session, events)
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
