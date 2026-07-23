from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from derive_action_signing import ModuleData
from eth_abi.abi import encode
from web3 import Web3

from derive_client.data_types import ChecksumAddress


def _uint_word(value: int) -> bytes:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"expected a non-negative integer, got {value!r}")
    return value.to_bytes(32, "big")


def _to_e18(value: Decimal) -> int:
    return int(value * Decimal(10**18))


def encode_create_session_key_action_data(
    *,
    session_key: ChecksumAddress,
    expiry_sec: int,
    scopes: Sequence[int],
    subaccount_ids: Sequence[int],
) -> bytes:
    if not isinstance(expiry_sec, int) or isinstance(expiry_sec, bool) or expiry_sec < 0:
        raise ValueError(f"session key expiry_sec must be a non-negative integer, got {expiry_sec!r}")

    session_key_word = bytes(12) + bytes.fromhex(session_key[2:])  # 20-byte address, left-padded to 32

    words = [
        session_key_word,
        _uint_word(expiry_sec),
        _uint_word(len(scopes)),
        _uint_word(len(subaccount_ids)),
        *(_uint_word(code) for code in scopes),
        *(_uint_word(sid) for sid in subaccount_ids),
    ]
    return b"".join(words)


@dataclass
class SessionKeyModuleData(ModuleData):
    """ModuleData for session-key creation.

    Same outer Action/SignedAction envelope as TradeModuleData,
    but the payload itself is the hand-packed encoding from derive-ts's sessionKey.ts,
    not standard ABI encoding.
    """

    session_key: str
    expiry_sec: int
    scopes: list[int]
    subaccount_ids: list[int]

    def to_abi_encoded(self) -> bytes:
        return encode_create_session_key_action_data(
            session_key=ChecksumAddress(self.session_key),
            expiry_sec=self.expiry_sec,
            scopes=self.scopes,
            subaccount_ids=self.subaccount_ids,
        )

    def to_json(self) -> dict:
        return {}


@dataclass
class WithdrawModuleData(ModuleData):
    """WithdrawModuleData

    The exchange pays out to whichever address SIGNS this action,
    `recipient` is not independently authoritative; the exchange reconstructs it to equal the signer.
    Signing with a session key sends funds to the session key's own address.
    """

    protocol_asset: str
    max_fee_usd: Decimal
    recipient: str  # must equal the signer
    amount: Decimal
    decimals: int
    force_batch: bool = False

    def to_abi_encoded(self) -> bytes:
        native_amount = int(self.amount * Decimal(10**self.decimals))
        if native_amount <= 0:
            raise ValueError(f"withdrawal amount must be strictly positive, got {self.amount}")

        return encode(
            ["address", "uint256", "address", "uint256", "bool"],
            [
                Web3.to_checksum_address(self.protocol_asset),
                _to_e18(self.max_fee_usd),
                Web3.to_checksum_address(self.recipient),
                native_amount,
                self.force_batch,
            ],
        )

    def to_json(self) -> dict:
        return {
            "amount": str(self.amount),
            "max_fee": str(self.max_fee_usd),
        }
