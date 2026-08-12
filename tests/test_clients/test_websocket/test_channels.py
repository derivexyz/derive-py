import asyncio

import msgspec
import pytest

from derive_client.data_types.channel_models import (
    OrderbookSnapshot,
    SpotFeedPayload,
    TickerSlimPayload,
)
from derive_client.data_types.generated_models import (
    AssetType,
    BatchStatus,
)
from derive_client.exceptions import DeriveJSONRPCError

TIMEOUT = 5
SUBSCRIPTION_OK = "ok"


def noop(result: msgspec.Struct) -> None:
    """No-op passed as callback when a notification within TIMEOUT seconds is not guaranteed."""

    return None


async def _wait_for_one(client, subscribe_coro_factory):
    """
    Subscribe, wait up to TIMEOUT for one notification, return (subscription_result, data).

    subscribe_coro_factory takes a callback and returns the awaitable
    subscribe call, so it can capture whatever channel-specific args the
    caller already bound (instrument_name, group, depth, etc.).
    """
    got = {}
    msg_event = asyncio.Event()

    def callback(result):
        got["data"] = result
        msg_event.set()

    subscription_result = await subscribe_coro_factory(callback)

    try:
        await asyncio.wait_for(msg_event.wait(), timeout=TIMEOUT)
    except asyncio.TimeoutError:
        pytest.fail(f"No notification received within {TIMEOUT}s")

    return subscription_result, got["data"]


## Public channels
@pytest.mark.asyncio
async def test_public_auctions_watch(client_admin_wallet):
    subscription_result = await client_admin_wallet.public_channels.auctions_watch(
        callback=noop,
    )

    assert subscription_result.status["auctions.watch"] == SUBSCRIPTION_OK


@pytest.mark.asyncio
async def test_public_margin_watch(client_admin_wallet):
    subscription_result = await client_admin_wallet.public_channels.margin_watch(
        callback=noop,
    )

    assert subscription_result.status["margin.watch"] == SUBSCRIPTION_OK


@pytest.mark.skip(reason="Spec/deployment skew: OrderSnapshot bids and asks are array instead of object.")
@pytest.mark.asyncio
async def test_public_orderbook_group_depth_by_instrument_name(client_admin_wallet):
    subscription_result, data = await _wait_for_one(
        client_admin_wallet,
        lambda callback: client_admin_wallet.public_channels.orderbook_group_depth_by_instrument_name(
            instrument_name="ETH-PERP",
            group=1,
            depth=1,
            callback=callback,
        ),
    )
    assert subscription_result.status["orderbook.ETH-PERP.1.1"] == SUBSCRIPTION_OK
    assert isinstance(data, OrderbookSnapshot)


@pytest.mark.asyncio
async def test_public_spot_feed_by_currency(client_admin_wallet):
    subscription_result, data = await _wait_for_one(
        client_admin_wallet,
        lambda callback: client_admin_wallet.public_channels.spot_feed_by_currency(
            currency="ETH",
            callback=callback,
        ),
    )

    assert subscription_result.status["spot_feed.ETH"] == SUBSCRIPTION_OK
    assert isinstance(data, SpotFeedPayload)


@pytest.mark.asyncio
async def test_public_ticker_slim_interval_by_instrument_name(client_admin_wallet):
    subscription_result, data = await _wait_for_one(
        client_admin_wallet,
        lambda callback: client_admin_wallet.public_channels.ticker_slim_interval_by_instrument_name(
            instrument_name="ETH-PERP",
            interval=1000,
            callback=callback,
        ),
    )

    assert subscription_result.status["ticker_slim.ETH-PERP.1000"] == SUBSCRIPTION_OK
    assert isinstance(data, TickerSlimPayload)


@pytest.mark.asyncio
async def test_public_trades_by_instrument_name(client_admin_wallet):
    subscription_result = await client_admin_wallet.public_channels.trades_by_instrument_name(
        instrument_name="ETH-PERP",
        callback=noop,
    )

    assert subscription_result.status["trades.ETH-PERP"] == SUBSCRIPTION_OK


@pytest.mark.asyncio
async def test_public_trades_by_instrument_type(client_admin_wallet):
    subscription_result = await client_admin_wallet.public_channels.trades_by_instrument_type(
        instrument_type=AssetType.erc20,
        currency="ETH",
        callback=noop,
    )

    assert subscription_result.status["trades.erc20.ETH"] == SUBSCRIPTION_OK


@pytest.mark.asyncio
async def test_public_trades_batch_status_by_instrument_type(client_admin_wallet):
    instrument_type = AssetType.option
    currency = "ETH"
    batch_status = BatchStatus.Settled
    subscription_result = await client_admin_wallet.public_channels.trades_batch_status_by_instrument_type(
        instrument_type=instrument_type,
        currency=currency,
        batch_status=batch_status,
        callback=noop,
    )

    assert subscription_result.status[f"trades.{instrument_type}.{currency}.{batch_status}"] == SUBSCRIPTION_OK


## Private channels
@pytest.mark.asyncio
async def test_private_balances_by_subaccount_id(client_admin_wallet):
    subaccount_id = client_admin_wallet.active_subaccount.id
    subscription_result = await client_admin_wallet.private_channels.balances_by_subaccount_id(
        subaccount_id=subaccount_id,
        callback=noop,
    )

    assert subscription_result.status[f"{subaccount_id}.balances"] == SUBSCRIPTION_OK


@pytest.mark.asyncio
async def test_private_best_quotes_by_subaccount_id(client_admin_wallet):
    subaccount_id = client_admin_wallet.active_subaccount.id
    subscription_result = await client_admin_wallet.private_channels.best_quotes_by_subaccount_id(
        subaccount_id=subaccount_id,
        callback=noop,
    )

    assert subscription_result.status[f"{subaccount_id}.best.quotes"] == SUBSCRIPTION_OK


@pytest.mark.asyncio
async def test_private_orders_by_subaccount_id(client_admin_wallet):
    subaccount_id = client_admin_wallet.active_subaccount.id
    subscription_result = await client_admin_wallet.private_channels.orders_by_subaccount_id(
        subaccount_id=subaccount_id,
        callback=noop,
    )

    assert subscription_result.status[f"{subaccount_id}.orders"] == SUBSCRIPTION_OK


@pytest.mark.asyncio
async def test_private_quotes_by_subaccount_id(client_admin_wallet):
    subaccount_id = client_admin_wallet.active_subaccount.id
    subscription_result = await client_admin_wallet.private_channels.quotes_by_subaccount_id(
        subaccount_id=subaccount_id,
        callback=noop,
    )

    assert subscription_result.status[f"{subaccount_id}.quotes"] == SUBSCRIPTION_OK


@pytest.mark.asyncio
async def test_private_trades_by_subaccount_id(client_admin_wallet):
    subaccount_id = client_admin_wallet.active_subaccount.id
    subscription_result = await client_admin_wallet.private_channels.trades_by_subaccount_id(
        subaccount_id=subaccount_id,
        callback=noop,
    )

    assert subscription_result.status[f"{subaccount_id}.trades"] == SUBSCRIPTION_OK


@pytest.mark.asyncio
async def test_private_trades_batch_status_by_subaccount_id(client_admin_wallet):
    subaccount_id = client_admin_wallet.active_subaccount.id
    batch_status = BatchStatus.Settled
    subscription_result = await client_admin_wallet.private_channels.trades_batch_status_by_subaccount_id(
        subaccount_id=subaccount_id,
        batch_status=batch_status,
        callback=noop,
    )

    assert subscription_result.status[f"{subaccount_id}.trades.{batch_status}"] == SUBSCRIPTION_OK


@pytest.mark.asyncio
async def test_private_rfqs_by_wallet(client_admin_wallet):
    wallet = client_admin_wallet.account.address
    subscription_result = await client_admin_wallet.private_channels.rfqs_by_wallet(
        wallet=wallet,
        callback=noop,
    )

    assert subscription_result.status[f"{wallet}.rfqs"] == SUBSCRIPTION_OK


@pytest.mark.asyncio
async def test_rejected_subscription_is_not_registered(client_admin_wallet):
    with pytest.raises(DeriveJSONRPCError):
        await client_admin_wallet.public_channels.orderbook_group_depth_by_instrument_name(
            instrument_name="ETH-PERP",
            group=1,
            depth=2,
            callback=noop,
        )
    assert "orderbook.ETH-PERP.1.2" not in client_admin_wallet.subscriptions
