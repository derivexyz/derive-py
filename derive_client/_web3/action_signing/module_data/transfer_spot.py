from dataclasses import dataclass
from decimal import Decimal

from eth_abi.abi import encode
from web3 import Web3

from ..utils import scale_amount
from .module_data import ModuleData


@dataclass
class TransferSpotModuleData(ModuleData):
    """Spot transfer between subaccounts of the same owner."""

    to_subaccount_id: int
    new_subaccount_manager: int
    asset: str  # protocol spot-asset address, not the underlying ERC-20
    asset_name: str  # e.g. "USDC", for to_json
    sub_id: int
    amount: Decimal
    max_fee_usd: Decimal

    def to_abi_encoded(self) -> bytes:
        return encode(
            ["uint256", "uint256", "address", "uint256", "uint256", "uint256"],
            [
                self.to_subaccount_id,
                self.new_subaccount_manager,
                Web3.to_checksum_address(self.asset),
                self.sub_id,
                scale_amount(self.amount),
                scale_amount(self.max_fee_usd),
            ],
        )

    def to_json(self) -> dict:
        return {
            "to_subaccount_id": self.to_subaccount_id,
            "new_subaccount_manager": self.new_subaccount_manager,
            "asset_name": self.asset_name,
            "sub_id": self.sub_id,
            "amount": str(self.amount),
            "max_fee_usd": str(self.max_fee_usd),
        }
