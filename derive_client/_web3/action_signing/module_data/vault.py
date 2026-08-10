from abc import abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar, Optional

from eth_abi.abi import encode
from web3 import Web3

from derive_client.config.constants import ZERO_ADDRESS
from derive_client.data_types import VaultAction

from ..utils import format_units, scale_vault_amount, to_bytes32, to_uint
from .module_data import ModuleData


@dataclass
class VaultModuleData(ModuleData):
    """Base for the six vault actions.

    Transcribed from derive-ts codecs/vault.ts and checked against the byte
    vectors in its test/unit/vault-codec.test.ts. There is no vault *_debug
    endpoint, so unlike every other module these encodings have no server
    reference at capture time.

    Deposit and withdraw can still be checked after the fact: their request
    bodies carry no data bytes, so the server must rebuild the payload from the
    typed params to verify the signature, and returns its reconstruction as
    signed_action.action.data on the live queue reads. Create, cancel, mint and
    burn have no read-back; acceptance is the only signal.
    """

    KIND: ClassVar[VaultAction]


@dataclass
class VaultCreateModuleData(VaultModuleData):
    """Vault creation, signed on the curator's funding subaccount.

    Fee rates, max slippage and cooldown are immutable once set, and are
    bounds-checked server-side against a deployment-set global config. The bps
    fields and cooldown_sec are plain integers, not e18.

    benchmark_asset denominates the high-water mark. Its PRESENCE, not its
    value, drives the encoded has_benchmark flag, which is how the exchange
    derives it from the wire param: passing the zero address explicitly is not
    the same as omitting it.
    """

    manager_id: int
    deposit_spot_asset: str
    initial_deposit: Decimal
    management_fee_bps: int
    performance_fee_bps: int
    max_slippage_bps: int
    cooldown_sec: int
    max_fee_usd: Decimal
    initial_share_price_usd: Decimal
    benchmark_asset: Optional[str] = None

    KIND: ClassVar[VaultAction] = VaultAction.CREATE

    def to_abi_encoded(self) -> bytes:
        benchmark_asset = self.benchmark_asset
        return encode(
            [
                "uint256",
                "uint256",
                "address",
                "uint256",
                "uint256",
                "uint256",
                "uint256",
                "uint256",
                "uint256",
                "uint256",
                "address",
                "bool",
            ],
            [
                self.KIND,
                to_uint(self.manager_id, "manager_id"),
                Web3.to_checksum_address(self.deposit_spot_asset),
                scale_vault_amount(self.initial_deposit, "initial_deposit"),
                to_uint(self.management_fee_bps, "management_fee_bps"),
                to_uint(self.performance_fee_bps, "performance_fee_bps"),
                to_uint(self.max_slippage_bps, "max_slippage_bps"),
                to_uint(self.cooldown_sec, "cooldown_sec"),
                scale_vault_amount(self.max_fee_usd, "max_fee_usd"),
                scale_vault_amount(self.initial_share_price_usd, "initial_share_price_usd"),
                Web3.to_checksum_address(benchmark_asset or ZERO_ADDRESS),
                benchmark_asset is not None,
            ],
        )

    def to_json(self) -> dict:
        return {
            "manager_id": self.manager_id,
            "deposit_spot_asset": Web3.to_checksum_address(self.deposit_spot_asset),
            "initial_deposit": format_units(scale_vault_amount(self.initial_deposit, "initial_deposit")),
            "management_fee_bps": self.management_fee_bps,
            "performance_fee_bps": self.performance_fee_bps,
            "max_slippage_bps": self.max_slippage_bps,
            "cooldown_sec": self.cooldown_sec,
            "max_fee_usd": format_units(scale_vault_amount(self.max_fee_usd, "max_fee_usd")),
            "initial_share_price_usd": format_units(
                scale_vault_amount(self.initial_share_price_usd, "initial_share_price_usd")
            ),
            # Explicit null rather than an omitted key: presence is what the
            # exchange reads to derive the signed has_benchmark flag.
            "benchmark_asset": (
                Web3.to_checksum_address(self.benchmark_asset) if self.benchmark_asset is not None else None
            ),
        }


@dataclass
class VaultDepositModuleData(VaultModuleData):
    """Queued deposit intent, signed on the subaccount the funds leave.

    Not a swap: the curator settles it later by minting shares at a quoted
    price bound to keccak of these exact bytes. Until then (or until cancelled)
    the funds are held on the source subaccount.

    deposit_spot_asset must equal the vault's configured deposit asset; take it
    from the vault row rather than hardcoding an address.
    """

    vault_subaccount_id: int
    deposit_spot_asset: str
    amount: Decimal

    KIND: ClassVar[VaultAction] = VaultAction.DEPOSIT

    def to_abi_encoded(self) -> bytes:
        return encode(
            ["uint256", "uint256", "address", "uint256"],
            [
                self.KIND,
                to_uint(self.vault_subaccount_id, "vault_subaccount_id"),
                Web3.to_checksum_address(self.deposit_spot_asset),
                scale_vault_amount(self.amount, "amount", strictly_positive=True),
            ],
        )

    def to_json(self) -> dict:
        return {
            "vault_subaccount_id": self.vault_subaccount_id,
            "deposit_spot_asset": Web3.to_checksum_address(self.deposit_spot_asset),
            "amount": format_units(scale_vault_amount(self.amount, "amount", strictly_positive=True)),
        }


@dataclass
class VaultWithdrawModuleData(VaultModuleData):
    """Queued redemption intent, signed on the subaccount the proceeds land in.

    Rejected until the vault's cooldown_sec has elapsed since the holder's last
    deposit (vault_cooldown_active, 18011). A curator redeeming their own stake
    is additionally floored by the curator stake minimum while other holders
    remain (vault_curator_stake_below_min, 18013).
    """

    vault_subaccount_id: int
    shares_to_burn: Decimal

    KIND: ClassVar[VaultAction] = VaultAction.WITHDRAW

    def to_abi_encoded(self) -> bytes:
        return encode(
            ["uint256", "uint256", "uint256"],
            [
                self.KIND,
                to_uint(self.vault_subaccount_id, "vault_subaccount_id"),
                scale_vault_amount(self.shares_to_burn, "shares_to_burn", strictly_positive=True),
            ],
        )

    def to_json(self) -> dict:
        return {
            "vault_subaccount_id": self.vault_subaccount_id,
            "shares_to_burn": format_units(
                scale_vault_amount(self.shares_to_burn, "shares_to_burn", strictly_positive=True)
            ),
        }


@dataclass
class VaultCancelModuleData(VaultModuleData):
    """Cancel ALL of the signer's pending intents for one vault.

    There is no cancel-one. The action bumps the per-(vault, holder) nonce to
    the envelope's nonce, so any intent already signed but not yet submitted,
    carrying a lower nonce, is invalidated along with the queued ones. May be
    signed on any subaccount the caller owns.
    """

    vault_subaccount_id: int

    KIND: ClassVar[VaultAction] = VaultAction.CANCEL

    def to_abi_encoded(self) -> bytes:
        return encode(
            ["uint256", "uint256"],
            [self.KIND, to_uint(self.vault_subaccount_id, "vault_subaccount_id")],
        )

    def to_json(self) -> dict:
        return {"vault_subaccount_id": self.vault_subaccount_id}


@dataclass
class VaultSettleModuleData(VaultModuleData):
    """Shared mint/burn layout: [kind, share_price_e18, user_action_hash].

    The hash commits the quoted price to one exact queued request, so the
    exchange cannot pair it with a different deposit or withdrawal. It must be
    the user_action_hash the queue read returned, never a locally recomputed
    value: a hash that disagrees still yields a perfectly valid signature, one
    that settles nothing.

    Both actions are signed on the VAULT subaccount, not the curator's own.
    Zero is a permitted share price here, matching derive-ts unsignedE18; the
    protocol bounds the quote against its own mark-to-market price within the
    vault's immutable max_slippage_bps.
    """

    share_price: Decimal
    user_action_hash: str

    @property
    @abstractmethod
    def _hash_field(self) -> str:
        """Wire name for user_action_hash. The two settle actions differ only
        in their kind word and in this key."""

    def to_abi_encoded(self) -> bytes:
        return encode(
            ["uint256", "uint256", "bytes32"],
            [
                self.KIND,
                scale_vault_amount(self.share_price, "share_price"),
                to_bytes32(self.user_action_hash, self._hash_field),
            ],
        )

    def to_json(self) -> dict:
        return {
            "share_price": format_units(scale_vault_amount(self.share_price, "share_price")),
            self._hash_field: self.user_action_hash,
        }


@dataclass
class VaultMintSharesModuleData(VaultSettleModuleData):
    """Curator approval settling one queued deposit."""

    KIND: ClassVar[VaultAction] = VaultAction.MINT_SHARES

    @property
    def _hash_field(self) -> str:
        return "deposit_hash"


@dataclass
class VaultBurnSharesModuleData(VaultSettleModuleData):
    """Curator approval settling one queued withdrawal.

    The vault subaccount must hold enough of the deposit asset to pay the
    redemption at settle time; unwind positions first if it does not. The burn
    that takes total_shares to zero closes the vault, terminally.
    """

    KIND: ClassVar[VaultAction] = VaultAction.BURN_SHARES

    @property
    def _hash_field(self) -> str:
        return "withdraw_hash"
