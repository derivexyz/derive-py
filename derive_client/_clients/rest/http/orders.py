"""Order management operations."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from derive_client._web3.action_signing import TradeModuleData
from derive_client.config import INT64_MAX
from derive_client.data_types.generated_models import (
    CancelAllRequest,
    CancelByInstrumentRequest,
    CancelByInstrumentResponse,
    CancelByLabelRequest,
    CancelByLabelResponse,
    CancelByNonceRequest,
    CancelByNonceResponse,
    CancelOrderRequest,
    CreateOrderRequest,
    Direction,
    GetOpenOrdersRequest,
    GetOrderHistoryRequest,
    GetOrderRequest,
    Order,
    OrderCreatedResponse,
    OrderType,
    PaginatedOrdersResult,
    ReplaceOrderRequest,
    ReplaceOrderResponse,
    TimeInForce,
    TriggerPriceType,
    TriggerType,
)

if TYPE_CHECKING:
    from .subaccount import Subaccount


class OrderOperations:
    """High-level order management operations."""

    def __init__(self, subaccount: Subaccount):
        """
        Initialize order operations.

        Args:
            subaccount: Subaccount instance providing access to auth, config, and APIs
        """
        self._subaccount = subaccount

    def create(
        self,
        *,
        amount: Decimal,
        direction: Direction,
        instrument_name: str,
        limit_price: Decimal,
        max_fee: Decimal = Decimal("1000"),
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
        extra_fee: Decimal = Decimal("0.000001"),
        is_atomic_signing: Optional[bool] = False,
        label: str = "",
        mmp: bool = False,
        order_type: OrderType = OrderType.limit,
        reduce_only: bool = False,
        reject_timestamp: int = INT64_MAX,
        time_in_force: TimeInForce = TimeInForce.gtc,
        trigger_price: Optional[Decimal] = None,
        trigger_price_type: Optional[TriggerPriceType] = None,
        trigger_type: Optional[TriggerType] = None,
    ) -> OrderCreatedResponse:
        """
        Create a new order.

        Amount and limit_price are automatically quantized to match instrument specifications.
        """

        subaccount_id = self._subaccount.id

        instrument = self._subaccount.markets._get_cached_instrument(instrument_name=instrument_name)
        asset_address = instrument.base_asset_address
        sub_id = int(instrument.base_asset_sub_id)

        amount = Decimal(amount).quantize(Decimal(instrument.amount_step))
        limit_price = Decimal(limit_price).quantize(Decimal(instrument.tick_size))

        is_bid = direction == Direction.buy
        module_data = TradeModuleData(
            asset_address=asset_address,
            sub_id=sub_id,
            limit_price=limit_price,
            amount=amount,
            max_fee=max_fee,
            recipient_id=subaccount_id,
            is_bid=is_bid,
        )

        module_address = self._subaccount._config.contracts.TRADE_MODULE
        signed_action = self._subaccount.sign_action(
            nonce=nonce,
            module_address=module_address,
            module_data=module_data,
            signature_expiry_sec=signature_expiry_sec,
        )

        params = CreateOrderRequest(
            amount=amount,
            direction=direction,
            instrument_name=instrument_name,
            limit_price=limit_price,
            max_fee=max_fee,
            nonce=str(signed_action.nonce),
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
            subaccount_id=subaccount_id,
            extra_fee=extra_fee,
            is_atomic_signing=is_atomic_signing,
            label=label,
            mmp=mmp,
            order_type=order_type,
            reduce_only=reduce_only,
            reject_timestamp=reject_timestamp,
            time_in_force=time_in_force,
            trigger_price=trigger_price,
            trigger_price_type=trigger_price_type,
            trigger_type=trigger_type,
        )
        result = self._subaccount._private_api.rpc.order(params)
        return result

    def get(self, *, order_id: str) -> Order:
        """Get state of an order by order id."""

        subaccount_id = self._subaccount.id
        params = GetOrderRequest(
            order_id=order_id,
            subaccount_id=subaccount_id,
        )
        result = self._subaccount._private_api.rpc.get_order(params)
        return result

    def history(
        self,
        *,
        from_timestamp: Optional[int] = None,
        to_timestamp: Optional[int] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> PaginatedOrdersResult:
        """
        Get order history of the currently active subaccount.
        """

        params = GetOrderHistoryRequest(
            subaccount_id=self._subaccount.id,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            page=page,
            page_size=page_size,
        )
        result = self._subaccount._private_api.rpc.get_order_history(params)
        return result

    def list_open(self) -> List[Order]:
        """Get all open orders of a subacccount."""

        params = GetOpenOrdersRequest(subaccount_id=self._subaccount.id)
        result = self._subaccount._private_api.rpc.get_open_orders(params)
        return result.orders

    def cancel(
        self,
        *,
        instrument_name: str,
        order_id: str,
    ) -> Order:
        """
        Cancel a single order.
        """

        params = CancelOrderRequest(
            instrument_name=instrument_name,
            order_id=order_id,
            subaccount_id=self._subaccount.id,
        )
        result = self._subaccount._private_api.rpc.cancel(params)
        return result

    def cancel_by_label(
        self,
        *,
        label: str,
        instrument_name: Optional[str] = None,
    ) -> CancelByLabelResponse:
        """
        Cancel all open orders for a given subaccount and a given label.

        If instrument_name is provided, only orders for that instrument will be cancelled.

        v3 change: returns a cancelled-order count, not the cancelled orders.
        """

        params = CancelByLabelRequest(
            label=label,
            instrument_name=instrument_name,
            subaccount_id=self._subaccount.id,
        )
        result = self._subaccount._private_api.rpc.cancel_by_label(params)
        return result

    def cancel_by_nonce(
        self,
        *,
        instrument_name: str,
        nonce: int,
    ) -> CancelByNonceResponse:
        """
        Cancel a single order by nonce. Uses up that nonce if the order does not exist,
        so any future orders with that nonce will fail.

        v3 change: CancelByNonceRequest no longer accepts wallet, dropped.
        """

        params = CancelByNonceRequest(
            nonce=nonce,
            instrument_name=instrument_name,
            subaccount_id=self._subaccount.id,
        )
        result = self._subaccount._private_api.rpc.cancel_by_nonce(params)
        return result

    def cancel_by_instrument(self, *, instrument_name: str) -> CancelByInstrumentResponse:
        """
        Cancel all orders for this instrument.

        v3 change: returns a cancelled-order count, not the cancelled orders.
        """

        params = CancelByInstrumentRequest(
            instrument_name=instrument_name,
            subaccount_id=self._subaccount.id,
        )
        result = self._subaccount._private_api.rpc.cancel_by_instrument(params)
        return result

    def cancel_all(self) -> str:
        """
        Cancel all orders for this instrument.

        v3 change: response is now the literal string "ok", not a Result object.
        """

        params = CancelAllRequest(subaccount_id=self._subaccount.id)
        result = self._subaccount._private_api.rpc.cancel_all(params)
        return result

    def replace(
        self,
        *,
        amount: Decimal,
        direction: Direction,
        instrument_name: str,
        limit_price: Decimal,
        max_fee: Decimal = Decimal("1000"),
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
        expected_filled_amount: Optional[Decimal] = None,
        extra_fee: Decimal = Decimal("0.000001"),
        is_atomic_signing: Optional[bool] = False,
        label: str = "",
        mmp: bool = False,
        nonce_to_cancel: Optional[int] = None,
        order_id_to_cancel: Optional[str] = None,
        order_type: OrderType = OrderType.limit,
        reduce_only: bool = False,
        reject_timestamp: int = INT64_MAX,
        time_in_force: TimeInForce = TimeInForce.gtc,
        trigger_price: Optional[Decimal] = None,
        trigger_price_type: Optional[TriggerPriceType] = None,
        trigger_type: Optional[TriggerType] = None,
    ) -> ReplaceOrderResponse:
        """
        Cancel an existing order with nonce or order_id and create new order with
        different order_id in a single RPC call.

        If the cancel fails, the new order will not be created.

        If the cancel succeeds but the new order fails, the old order will still be
        cancelled.

        Amount and limit_price are automatically quantized to match instrument specifications.

        v3 change: return shape is now ReplaceOrderResponse (cancelled_order,
        order | None, create_order_error | None), not a flat order. Check
        .create_order_error before assuming .order succeeded.
        """

        if (nonce_to_cancel is None) == (order_id_to_cancel is None):
            raise ValueError("Replace requires exactly one of nonce_to_cancel or order_id_to_cancel (but not both).")

        subaccount_id = self._subaccount.id

        instrument = self._subaccount.markets._get_cached_instrument(instrument_name=instrument_name)
        asset_address = instrument.base_asset_address
        sub_id = int(instrument.base_asset_sub_id)

        amount = Decimal(amount).quantize(Decimal(instrument.amount_step))
        limit_price = Decimal(limit_price).quantize(Decimal(instrument.tick_size))

        is_bid = direction == Direction.buy
        module_data = TradeModuleData(
            asset_address=asset_address,
            sub_id=sub_id,
            limit_price=limit_price,
            amount=amount,
            max_fee=max_fee,
            recipient_id=subaccount_id,
            is_bid=is_bid,
        )

        module_address = self._subaccount._config.contracts.TRADE_MODULE
        signed_action = self._subaccount.sign_action(
            nonce=nonce,
            module_address=module_address,
            module_data=module_data,
            signature_expiry_sec=signature_expiry_sec,
        )

        params = ReplaceOrderRequest(
            amount=amount,
            direction=direction,
            instrument_name=instrument_name,
            limit_price=limit_price,
            max_fee=max_fee,
            nonce=str(signed_action.nonce),
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
            subaccount_id=subaccount_id,
            expected_filled_amount=expected_filled_amount,
            extra_fee=extra_fee,
            is_atomic_signing=is_atomic_signing,
            label=label,
            mmp=mmp,
            nonce_to_cancel=nonce_to_cancel,
            order_id_to_cancel=order_id_to_cancel,
            order_type=order_type,
            reduce_only=reduce_only,
            reject_timestamp=reject_timestamp,
            time_in_force=time_in_force,
            trigger_price=trigger_price,
            trigger_price_type=trigger_price_type,
            trigger_type=trigger_type,
        )
        result = self._subaccount._private_api.rpc.replace(params)
        return result
