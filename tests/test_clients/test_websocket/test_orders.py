"""Tests for Orders module."""

from decimal import Decimal

import pytest

from derive_py.data_types.generated_models import (
    CancelByInstrumentResponse,
    CancelByLabelResponse,
    CancelByNonceResponse,
    Direction,
    Order,
    OrderType,
    PaginatedOrdersResult,
    ReplaceOrderResponse,
)
from tests.conftest import assert_api_calls


async def _create_order(
    client,
    amount=Decimal("0.10"),
    instrument_name: str = "ETH-PERP",
    direction=Direction.buy,
    limit_price=Decimal("200.00"),
) -> Order:
    max_fee = Decimal("1000")
    order_type = OrderType.limit
    label = "test_order"

    create_order_response = await client.orders.create(
        amount=amount,
        direction=direction,
        instrument_name=instrument_name,
        limit_price=limit_price,
        max_fee=max_fee,
        order_type=order_type,
        label=label,
    )
    return create_order_response.order


@pytest.mark.asyncio
async def test_orders_create(client_admin_wallet):
    with assert_api_calls(client_admin_wallet, expected=1):
        order = await _create_order(client_admin_wallet)
    assert isinstance(order, Order)


@pytest.mark.asyncio
async def test_orders_get(client_admin_wallet):
    order = await _create_order(client_admin_wallet)
    order_id = order.order_id
    order = await client_admin_wallet.orders.get(order_id=order_id)
    assert isinstance(order, Order)


@pytest.mark.asyncio
async def test_orders_history(client_admin_wallet):
    orders = await client_admin_wallet.orders.history()
    assert isinstance(orders, PaginatedOrdersResult)
    assert all(isinstance(o, Order) for o in orders.orders)


@pytest.mark.asyncio
async def test_orders_list_open(client_admin_wallet):
    open_orders = await client_admin_wallet.orders.list_open()
    assert isinstance(open_orders, list)
    assert all(isinstance(o, Order) for o in open_orders)


@pytest.mark.asyncio
async def test_orders_cancel(client_admin_wallet):
    order = await _create_order(client_admin_wallet)
    order_id = order.order_id
    cancelled = await client_admin_wallet.orders.cancel(
        instrument_name=order.instrument_name,
        order_id=order_id,
    )
    assert isinstance(cancelled, Order)


@pytest.mark.asyncio
async def test_orders_cancel_by_label(client_admin_wallet):
    order = await _create_order(client_admin_wallet)
    cancelled_by_label = await client_admin_wallet.orders.cancel_by_label(label=order.label)
    assert isinstance(cancelled_by_label, CancelByLabelResponse)


@pytest.mark.asyncio
async def test_orders_cancel_by_nonce(client_admin_wallet):
    order = await _create_order(client_admin_wallet)
    # order.nonce is str on the Order struct; cancel_by_nonce's request wants int.
    cancelled_by_label = await client_admin_wallet.orders.cancel_by_nonce(
        instrument_name=order.instrument_name,
        nonce=int(order.nonce),
    )
    assert isinstance(cancelled_by_label, CancelByNonceResponse)


@pytest.mark.asyncio
async def test_orders_cancel_by_instrument(client_admin_wallet):
    order = await _create_order(client_admin_wallet)
    cancelled_by_label = await client_admin_wallet.orders.cancel_by_instrument(instrument_name=order.instrument_name)
    assert isinstance(cancelled_by_label, CancelByInstrumentResponse)


@pytest.mark.asyncio
async def test_orders_cancel_all(client_admin_wallet):
    cancelled_all = await client_admin_wallet.orders.cancel_all()
    assert isinstance(cancelled_all, str)


@pytest.mark.asyncio
async def test_orders_replace(client_admin_wallet):
    order = await _create_order(client_admin_wallet)
    order_id = order.order_id
    with assert_api_calls(client_admin_wallet, expected=1):
        replace = await client_admin_wallet.orders.replace(
            amount=order.amount,
            direction=order.direction,
            instrument_name=order.instrument_name,
            limit_price=order.limit_price,
            max_fee=order.max_fee,
            order_id_to_cancel=order_id,
        )
    assert isinstance(replace, ReplaceOrderResponse)
