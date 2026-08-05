"""Position management operations."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from derive_client._clients.utils import sort_by_instrument_name
from derive_client._web3.action_signing import (
    MakerTransferPositionsModuleData,
    TakerTransferPositionsModuleData,
    TransferPositionsDetails,
)
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

    async def list(self) -> list[Position]:
        """Get all positions"""

        params = GetPositionsRequest(subaccount_id=self._subaccount.id)
        result = await self._subaccount._private_api.rpc.get_positions(params)
        return result.positions

    async def transfer(
        self,
        *,
        positions: list[PositionTransfer],
        direction: Direction,
        to_subaccount: int,
        signature_expiry_sec: Optional[int] = None,
        maker_nonce: Optional[int] = None,
        taker_nonce: Optional[int] = None,
    ) -> TransferPositionsResponse:
        """Transfers multiple positions from one subaccount to another, owned by the same wallet."""

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
