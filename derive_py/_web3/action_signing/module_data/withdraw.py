from dataclasses import dataclass
from decimal import Decimal

from eth_abi.abi import encode
from web3 import Web3

from ..utils import scale_amount
from .module_data import ModuleData


@dataclass
class WithdrawModuleData(ModuleData):
    """Withdrawal to L1.

    `recipient` is the L1 address paid out, and defaults to the subaccount's
    owner wallet. It is independent of the signer: a session key signing this
    action does NOT redirect funds to itself. A non-owner signer may only pay
    out to an address on the owner's whitelisted_recipients, unless the key
    holds Admin. `amount` is in the asset's native ERC-20 decimals, with no
    additional scaling.
    """

    protocol_asset: str  # address, for to_abi_encoded
    asset_name: str  # e.g. "USDC", for to_json
    max_fee_usd: Decimal
    recipient: str
    amount: Decimal
    decimals: int
    force_batch: bool = False

    def to_abi_encoded(self) -> bytes:
        amount = scale_amount(self.amount, self.decimals)
        if amount <= 0:
            raise ValueError("withdrawal amount must be strictly positive")
        return encode(
            ["address", "uint256", "address", "uint256", "bool"],
            [
                Web3.to_checksum_address(self.protocol_asset),
                scale_amount(self.max_fee_usd),
                Web3.to_checksum_address(self.recipient),
                amount,
                self.force_batch,
            ],
        )

    def to_json(self) -> dict:
        return {
            "asset_name": self.asset_name,
            "amount_in_underlying": str(self.amount),
            "max_fee_usd": str(self.max_fee_usd),
            "force_batch": self.force_batch,
        }
