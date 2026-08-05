from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from eth_abi.abi import encode
from web3 import Web3

from derive_client._web3.action_signing import ModuleData
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


@dataclass
class WhitelistedRecipientModuleData(ModuleData):
    """ModuleData for whitelisted-recipient management.

    Hand-packed layout (2 + A + R words), NOT standard ABI dynamic
    arrays -- verified against derive-ts's codecs/whitelistedRecipients.ts:
        word 0     : add count A
        word 1     : remove count R
        word 2+i   : add[i], address left-padded to 32 bytes
        word 2+A+j : remove[j], address left-padded to 32 bytes
    """

    add: list[str]
    remove: list[str]

    def to_abi_encoded(self) -> bytes:
        add_words = [bytes(12) + bytes.fromhex(addr[2:]) for addr in self.add]
        remove_words = [bytes(12) + bytes.fromhex(addr[2:]) for addr in self.remove]

        words = [
            _uint_word(len(self.add)),
            _uint_word(len(self.remove)),
            *add_words,
            *remove_words,
        ]
        return b"".join(words)

    def to_json(self) -> dict:
        return {
            "add": self.add,
            "remove": self.remove,
        }


def encode_transfer_action_data(
    *,
    to_subaccount_id: int,
    new_subaccount_manager: int,
    asset: str,
    sub_id: int,
    amount: Decimal,
    max_fee_usd: Decimal,
) -> bytes:
    """Standard ABI encoding, six static uint256/address words."""

    native_amount = _to_e18(amount)
    if native_amount <= 0:
        raise ValueError(f"transfer amount must be strictly positive, got {amount}")

    return encode(
        ["uint256", "uint256", "address", "uint256", "uint256", "uint256"],
        [
            to_subaccount_id,
            new_subaccount_manager,
            Web3.to_checksum_address(asset),
            sub_id,
            native_amount,
            _to_e18(max_fee_usd),
        ],
    )


@dataclass
class TransferSpotModuleData(ModuleData):
    """ModuleData for transferring a spot asset between the owner's own subaccounts."""

    to_subaccount_id: int
    new_subaccount_manager: int
    asset: str  # protocol spot-asset address, NOT the underlying ERC-20
    sub_id: int
    amount: Decimal
    max_fee_usd: Decimal

    def to_abi_encoded(self) -> bytes:
        return encode_transfer_action_data(
            to_subaccount_id=self.to_subaccount_id,
            new_subaccount_manager=self.new_subaccount_manager,
            asset=self.asset,
            sub_id=self.sub_id,
            amount=self.amount,
            max_fee_usd=self.max_fee_usd,
        )

    def to_json(self) -> dict:
        return {
            "amount": str(self.amount),
            "max_fee_usd": str(self.max_fee_usd),
        }


@dataclass
class TransferSpotExternalModuleData(ModuleData):
    """ModuleData for transferring a spot asset to a different owner's subaccount."""

    to_subaccount_id: int
    new_subaccount_manager: int
    asset: str
    sub_id: int
    amount: Decimal
    max_fee_usd: Decimal
    recipient: str

    def to_abi_encoded(self) -> bytes:
        native_amount = _to_e18(self.amount)
        if native_amount <= 0:
            raise ValueError(f"transfer amount must be strictly positive, got {self.amount}")

        return encode(
            ["uint256", "uint256", "address", "uint256", "uint256", "uint256", "address"],
            [
                self.to_subaccount_id,
                self.new_subaccount_manager,
                Web3.to_checksum_address(self.asset),
                self.sub_id,
                native_amount,
                _to_e18(self.max_fee_usd),
                Web3.to_checksum_address(self.recipient),
            ],
        )

    def to_json(self) -> dict:
        return {
            "amount": str(self.amount),
            "max_fee_usd": str(self.max_fee_usd),
            "recipient": self.recipient,
        }
