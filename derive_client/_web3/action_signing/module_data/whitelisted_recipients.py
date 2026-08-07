from dataclasses import dataclass
from typing import ClassVar

from eth_abi.abi import encode
from web3 import Web3

from .module_data import ModuleData


@dataclass
class WhitelistedRecipientModuleData(ModuleData):
    """Recipient allow-list management.

    Merges the current list with add, excluding any addresses in remove.
    """

    WALLET_SCOPED: ClassVar[bool] = True

    add: list[str]
    remove: list[str]

    def to_abi_encoded(self) -> bytes:
        return encode(
            ["address[]", "address[]"],
            [
                [Web3.to_checksum_address(a) for a in self.add],
                [Web3.to_checksum_address(a) for a in self.remove],
            ],
        )

    def to_json(self) -> dict:
        return {"add": self.add, "remove": self.remove}
