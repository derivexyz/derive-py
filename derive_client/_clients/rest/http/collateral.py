"""Collateral management operations."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from derive_client.data_types import ChecksumAddress
from derive_client.data_types.generated_models import (
    AssetType,
    GetCollateralsRequest,
    GetErc20TransferHistoryRequest,
    PrivateGetCollateralsResponse,
    PrivateTransferSpotExternalRequest,
    PrivateTransferSpotExternalResponse,
    PrivateTransferSpotRequest,
    PrivateTransferSpotResponse,
    TransferEntry,
)
from derive_client.data_types.module_data import TransferSpotExternalModuleData, TransferSpotModuleData

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

    def get_transfer_history(
        self,
        *,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        wallet: bool = False,
    ) -> list[TransferEntry]:
        """Settled spot (ERC-20) transfer history; transfer_spot() and
        transfer_spot_external() calls that have settled, for this
        subaccount, or the whole wallet if wallet=True."""

        params = GetErc20TransferHistoryRequest(
            subaccount_id=None if wallet else self._subaccount.id,
            wallet=self._subaccount._auth.wallet if wallet else None,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
        )
        result = self._subaccount._private_api.rpc.get_erc20_transfer_history(params)
        return result.transfers

    def transfer_spot(
        self,
        *,
        amount: Decimal,
        asset_name: str,
        to_subaccount_id: int = 0,
        new_subaccount_manager: int = 0,
        max_fee_usd: Decimal = Decimal("0"),
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
    ) -> PrivateTransferSpotResponse:
        """Moves a spot balance between the owner's OWN subaccounts."""

        if to_subaccount_id == 0 and new_subaccount_manager == 0:
            raise ValueError("Specify to_subaccount_id, or new_subaccount_manager to create a new subaccount instead.")

        if new_subaccount_manager != 0 and max_fee_usd <= 0:
            raise ValueError(
                "Creating a subaccount charges a transfer fee -- "
                "set max_fee_usd (>= 1) when new_subaccount_manager is used."
            )

        subaccount_id = self._subaccount.id

        assets = self._subaccount.markets.get_assets(asset_type=AssetType.erc20, currency=asset_name)
        if not len(assets) == 1:
            raise RuntimeError(f"Expected exactly one asset for {asset_name}, got {assets}")
        asset = assets[0]

        module_data = TransferSpotModuleData(
            to_subaccount_id=to_subaccount_id,
            new_subaccount_manager=new_subaccount_manager,
            asset=asset.address,
            sub_id=int(asset.sub_id),
            amount=amount,
            max_fee_usd=max_fee_usd,
        )

        module_address = self._subaccount._config.contracts.TRANSFER_MODULE
        signed_action = self._subaccount.sign_action(
            module_address=module_address,
            module_data=module_data,
            nonce=nonce,
            signature_expiry_sec=signature_expiry_sec,
        )

        params = PrivateTransferSpotRequest(
            amount=amount,
            asset_name=asset_name,
            max_fee_usd=max_fee_usd,
            new_subaccount_manager=new_subaccount_manager,
            nonce=signed_action.nonce,
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
            sub_id=int(asset.sub_id),
            subaccount_id=subaccount_id,
            to_subaccount_id=to_subaccount_id,
        )

        result = self._subaccount._private_api.rpc.transfer_spot(params)
        return result

    def transfer_spot_external(
        self,
        *,
        amount: Decimal,
        asset_name: str,
        recipient_address: str,
        to_subaccount_id: int = 0,
        new_subaccount_manager: int = 0,
        max_fee_usd: Decimal,
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
    ) -> PrivateTransferSpotExternalResponse:
        """Moves a spot balance to a subaccount belonging to a DIFFERENT owner's wallet.

        recipient_address must already be on the sender's whitelist,
        call LightAccount.update_whitelisted_recipients() first.
        """

        if to_subaccount_id == 0 and new_subaccount_manager == 0:
            raise ValueError(
                "Specify the recipient's to_subaccount_id, or new_subaccount_manager to create one for them instead."
            )

        subaccount_id = self._subaccount.id
        recipient = ChecksumAddress(recipient_address)

        assets = self._subaccount.markets.get_assets(asset_type=AssetType.erc20, currency=asset_name)
        if not len(assets) == 1:
            raise RuntimeError(f"Expected exactly one asset for {asset_name}, got {assets}")
        asset = assets[0]

        module_data = TransferSpotExternalModuleData(
            to_subaccount_id=to_subaccount_id,
            new_subaccount_manager=new_subaccount_manager,
            asset=asset.address,
            sub_id=int(asset.sub_id),
            amount=amount,
            max_fee_usd=max_fee_usd,
            recipient=recipient,
        )

        module_address = self._subaccount._config.contracts.EXTERNAL_TRANSFER_MODULE
        signed_action = self._subaccount.sign_action(
            module_address=module_address,
            module_data=module_data,
            nonce=nonce,
            signature_expiry_sec=signature_expiry_sec,
        )

        params = PrivateTransferSpotExternalRequest(
            amount=amount,
            asset_name=asset_name,
            max_fee_usd=max_fee_usd,
            new_subaccount_manager=new_subaccount_manager,
            nonce=signed_action.nonce,
            recipient_address=recipient,
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
            sub_id=int(asset.sub_id),
            subaccount_id=subaccount_id,
            to_subaccount_id=to_subaccount_id,
        )

        result = self._subaccount._private_api.rpc.transfer_spot_external(params)
        return result
