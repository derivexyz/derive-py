"""Position management operations."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from derive_action_signing import (
    MakerTransferPositionsModuleData,
    TakerTransferPositionsModuleData,
    TransferPositionsDetails,
)

from derive_client._clients.utils import sort_by_instrument_name
from derive_client.data_types import PositionTransfer
from derive_client.data_types.generated_models import (
    Direction,
    GetPositionsRequest,
    Position,
    PricedLegParamsAndResponse,
    SignedTransferQuoteRequest,
    TransferPositionsRequest,
    TransferPositionsResponse,
)

if TYPE_CHECKING:
    from .subaccount import Subaccount


class PositionOperations:
    """High-level position management operations."""

    def __init__(self, subaccount: Subaccount):
        """
        Initialize order operations.

        Args:
            subaccount: Subaccount instance providing access to auth, config, and APIs
        """
        self._subaccount = subaccount

    async def list(self, is_open: Optional[bool] = None, currency: str | None = None) -> list[Position]:
        """Get all positions"""

        params = GetPositionsRequest(subaccount_id=self._subaccount.id)
        result = await self._subaccount._private_api.rpc.get_positions(params)
        intermediate = (
            result.positions if is_open is None else [p for p in result.positions if (p.amount != 0) == is_open]
        )
        if currency:
            intermediate = [p for p in intermediate if p.instrument_name.startswith(currency)]
        return intermediate

    async def transfer(
        self,
        *,
        positions: List[PositionTransfer],
        direction: Direction,
        to_subaccount: int,
        signature_expiry_sec: Optional[int] = None,
        maker_nonce: Optional[int] = None,
        taker_nonce: Optional[int] = None,
    ) -> TransferPositionsResponse:
        """Transfers multiple positions from one subaccount to another, owned by the same
        wallet.

        The transfer is executed as a an RFQ. A mock RFQ is first created from the taker
        parameters, followed by a maker quote and a taker execute.

        The leg amounts, prices and instrument name must be the same in both param
        payloads.

        Fee is not charged and a zero `max_fee` must be signed.

        Every leg in the transfer must be a position reduction for either maker or taker
        (or both).

        History: for position transfer history, use the `private/get_trade_history` RPC
        (not `private/get_erc20_transfer_history`).

        v3 change: returns TransferPositionsResponse (maker_quote: Quote,
        taker_quote: Quote), not the previous flat result shape.
        """

        from_subaccount = self._subaccount.id
        positions = sort_by_instrument_name(positions)
        max_fee = Decimal("0")

        legs = []
        transfer_details = []
        for position in positions:
            amount = abs(position.amount)
            leg_direction = Direction.buy if position.amount < 0 else Direction.sell

            instrument_name = position.instrument_name
            instrument = self._subaccount.markets._get_cached_instrument(instrument_name=instrument_name)
            price = Decimal(instrument.tick_size)
            asset_address = instrument.base_asset_address
            sub_id = int(instrument.base_asset_sub_id)

            priced_leg = PricedLegParamsAndResponse(
                amount=amount,
                direction=leg_direction,
                instrument_name=instrument_name,
                price=price,
            )
            legs.append(priced_leg)

            details = TransferPositionsDetails(
                instrument_name=instrument_name,
                direction=leg_direction.value,
                asset_address=asset_address,
                sub_id=sub_id,
                price=price,
                amount=amount,
            )
            transfer_details.append(details)

        maker_direction = direction
        taker_direction = Direction.buy if maker_direction == Direction.sell else Direction.sell

        module_address = self._subaccount._config.contracts.RFQ_MODULE

        maker_module_data = MakerTransferPositionsModuleData(
            global_direction=maker_direction.value,
            positions=transfer_details,
        )
        taker_module_data = TakerTransferPositionsModuleData(
            global_direction=taker_direction.value,
            positions=transfer_details,
        )

        maker_action = self._subaccount.sign_action(
            nonce=maker_nonce,
            module_address=module_address,
            module_data=maker_module_data,
            signature_expiry_sec=signature_expiry_sec,
        )
        taker_action = self._subaccount._auth.sign_action(
            nonce=taker_nonce,
            module_address=module_address,
            module_data=taker_module_data,
            signature_expiry_sec=signature_expiry_sec,
            subaccount_id=to_subaccount,
        )

        maker_params = SignedTransferQuoteRequest(
            direction=maker_direction,
            legs=legs,
            max_fee=max_fee,
            nonce=str(maker_action.nonce),
            signature=maker_action.signature,
            signature_expiry_sec=maker_action.signature_expiry_sec,
            signer=maker_action.signer,
            subaccount_id=from_subaccount,
        )
        taker_params = SignedTransferQuoteRequest(
            direction=taker_direction,
            legs=legs,
            max_fee=max_fee,
            nonce=str(taker_action.nonce),
            signature=taker_action.signature,
            signature_expiry_sec=taker_action.signature_expiry_sec,
            signer=taker_action.signer,
            subaccount_id=to_subaccount,
        )

        params = TransferPositionsRequest(
            maker_params=maker_params,
            taker_params=taker_params,
            wallet=self._subaccount._auth.wallet,
        )
        result = await self._subaccount._private_api.rpc.transfer_positions(params)
        return result
