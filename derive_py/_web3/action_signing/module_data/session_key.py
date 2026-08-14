from dataclasses import dataclass, field
from decimal import Decimal  # noqa: F401 - remove if unused
from typing import ClassVar

from eth_abi.abi import encode
from web3 import Web3

from derive_py.data_types import ProtocolScope

from .module_data import ModuleData


@dataclass
class SessionKeyModuleData(ModuleData):
    """Session-key registration.

    Signed against subaccount_id = 0; the request is wallet-scoped and carries
    no subaccount_id. Canonical abi.encode, verified against derive-ts
    codecs/sessionKey.ts.

    An empty subaccount_ids grants the key ALL current and future subaccounts.
    Over private/set_session_key, expiry_sec must be at least 5 minutes out
    (error 14039); 0 is rejected rather than deactivating the key.
    """

    WALLET_SCOPED: ClassVar[bool] = True

    session_key: str
    expiry_sec: int
    protocol_scopes: list[ProtocolScope]
    subaccount_ids: list[int] = field(default_factory=list)
    offchain_scopes: list[str] = field(default_factory=list)

    def to_abi_encoded(self) -> bytes:
        if not isinstance(self.expiry_sec, int) or self.expiry_sec < 0:
            raise ValueError(f"expiry_sec must be a non-negative integer, got {self.expiry_sec!r}")
        return encode(
            ["address", "uint256", "uint256[]", "uint256[]"],
            [
                Web3.to_checksum_address(self.session_key),
                self.expiry_sec,
                [scope.code for scope in self.protocol_scopes],
                list(self.subaccount_ids),
            ],
        )

    def to_json(self) -> dict:
        return {
            "public_session_key": self.session_key,
            "expiry_sec": self.expiry_sec,
            "protocol_scopes": [str(scope) for scope in self.protocol_scopes],
            "offchain_scopes": self.offchain_scopes,
            "subaccount_ids": self.subaccount_ids,
        }
