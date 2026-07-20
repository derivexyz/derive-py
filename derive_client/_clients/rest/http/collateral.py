"""Collateral management operations."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from derive_action_signing import WithdrawModuleData

from derive_client.config import CURRENCY_DECIMALS
from derive_client.data_types import Currency
from derive_client.data_types.generated_models import (
    GetCollateralsRequest,
    PrivateGetCollateralsResponse,
    PrivateWithdrawRequest,
    PrivateWithdrawResponse,
)

if TYPE_CHECKING:
    from .subaccount import Subaccount


class CollateralOperations:
    """Collateral management operations."""

    def __init__(self, *, subaccount: Subaccount):
        """
        Initialize collateral operations.

        Args:
            subaccount: Subaccount instance providing access to auth, config, and APIs
        """
        self._subaccount = subaccount

    def get(self) -> PrivateGetCollateralsResponse:
        """Get collaterals of a subaccount."""

        subaccount_id = self._subaccount.id
        params = GetCollateralsRequest(subaccount_id=subaccount_id)
        result = self._subaccount._private_api.rpc.get_collaterals(params)
        return result

    def withdraw_from_subaccount(
        self,
        *,
        amount: Decimal,
        asset_name: str,
        max_fee_usd: Decimal,
        subaccount_id: Optional[int] = None,
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
        force_batch: bool = False,
    ) -> PrivateWithdrawResponse:
        """
        Withdraw an asset from a subaccount to the LightAccount wallet.

        v3 changes, not fully resolved here:
        - max_fee_usd is now required (max fee in USD the caller accepts).
        - force_batch replaces is_atomic_signing; semantics not confirmed identical.
        - asset address resolution below is unresolved, see raise.
        """

        subaccount_id = self._subaccount.id if subaccount_id is None else subaccount_id
        module_address = self._subaccount._config.contracts.WITHDRAW_MODULE

        currency = self._subaccount.markets.get_currency(currency=asset_name)

        # v3: Currency.spot is now list[SpotAssetEntry], not a single nullable
        # address (currency.protocol_asset_addresses.spot no longer exists).
        # Not guessing which entry is correct for a withdrawal address —
        # verify against Derive's docs before picking a selection rule.
        raise NotImplementedError(
            f"Asset address resolution for withdrawals needs updating for v3's Currency.spot "
            f"list shape (found {len(currency.spot)} entries for '{asset_name}'). "
            "Confirm the correct entry before implementing."
        )

        decimals = CURRENCY_DECIMALS[Currency[asset_name]]
        asset = ""  # Placeholder for the resolved asset address, to be implemented after confirming the correct entry.
        module_data = WithdrawModuleData(
            amount=amount,
            asset=asset,
            decimals=decimals,
            asset_name=asset_name,
        )

        signed_action = self._subaccount.sign_action(
            nonce=nonce,
            module_address=module_address,
            module_data=module_data,
            signature_expiry_sec=signature_expiry_sec,
        )

        params = PrivateWithdrawRequest(
            amount_in_underlying=str(amount),
            asset_name=asset_name,
            force_batch=force_batch,
            max_fee_usd=max_fee_usd,
            nonce=signed_action.nonce,
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
            subaccount_id=subaccount_id,
        )
        result = self._subaccount._private_api.rpc.withdraw(params)
        return result
