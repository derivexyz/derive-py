from dataclasses import dataclass
from typing import Generic, TypeVar

from eth_abi.abi import encode
from eth_account.datastructures import SignedMessage
from hexbytes import HexBytes
from web3 import Account, Web3

from .module_data.module_data import ModuleData

TModuleData = TypeVar("TModuleData", bound=ModuleData)


@dataclass
class SignedAction(Generic[TModuleData]):
    """
    Used to sign and validate actions.

    :param subaccount_id: The subaccount id of the user.
    :param owner: The wallet that owns the subaccount (EOA or multisig).
    :param signer: The signer of the action - the owner or a session key.
    :param signature_expiry_sec: Signature expiry, in unix seconds. Minimums and
        maximums vary by action type; see docs.derive.xyz action-signing.
    :param nonce: UTC timestamp in nanoseconds (~19 digits). Must be strictly
        increasing per subaccount for withdraw, transfer, session key, whitelist
        and liquidation actions.
    :param module_address: The contract address of the module. Refer to Protocol
        Constants table in docs.derive.xyz.
    :param module_data: Data defined by the specific protocol module (e.g. for
        orders use module_data.trade.TradeModuleData).
    :param DOMAIN_SEPARATOR: The domain separator of the protocol, per chain.
        Refer to Protocol Constants table in docs.derive.xyz.
    :param ACTION_TYPEHASH: The typehash of the action. Refer to Protocol
        Constants table in docs.derive.xyz.
    :param signature: The signature of the action. Use sign() to generate it.
    """

    subaccount_id: int
    owner: str
    signer: str
    signature_expiry_sec: int
    nonce: int
    module_address: str
    module_data: TModuleData
    DOMAIN_SEPARATOR: str
    ACTION_TYPEHASH: str
    signature: str = ""

    def sign(self, signer_private_key: str) -> str:
        signer_wallet = Web3().eth.account.from_key(signer_private_key)
        signed: SignedMessage = signer_wallet.unsafe_sign_hash(self._to_typed_data_hash())
        self.signature = signed.signature.hex()
        return self.signature

    def to_json(self):
        envelope = {
            # String, not int: a nanosecond nonce exceeds 2^53 and is corrupted
            # by any JSON consumer using doubles.
            "nonce": str(self.nonce),
            "signer": self.signer,
            "signature_expiry_sec": self.signature_expiry_sec,
            "signature": self.signature,
        }
        if self.module_data.WALLET_SCOPED:
            envelope["wallet"] = self.owner
        else:
            envelope["subaccount_id"] = self.subaccount_id
        return {**envelope, **self.module_data.to_json()}

    def validate_signature(self):
        data_hash = self._to_typed_data_hash()
        recovered = Account._recover_hash(
            data_hash.hex(),
            signature=HexBytes(self.signature),
        )

        if recovered.lower() != self.signer.lower():
            raise ValueError("Invalid signature. Recovered signer does not match expected signer.")

    @staticmethod
    def _to_bytes32(value: str, name: str) -> bytes:
        raw = value[2:] if value.startswith("0x") else value
        try:
            result = bytes.fromhex(raw)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"{name} is not valid hex: {value!r}. "
                "Ensure the value is copied from Protocol Constants in docs.derive.xyz."
            ) from e
        if len(result) != 32:
            raise ValueError(f"{name} must be 32 bytes, got {len(result)}: {value!r}")
        return result

    @property
    def domain_separator(self) -> bytes:
        return self._to_bytes32(self.DOMAIN_SEPARATOR, "DOMAIN_SEPARATOR")

    @property
    def action_typehash(self) -> bytes:
        return self._to_bytes32(self.ACTION_TYPEHASH, "ACTION_TYPEHASH")

    def _to_typed_data_hash(self) -> HexBytes:
        return Web3.keccak(b"\x19\x01" + self.domain_separator + self._get_action_hash())

    def _get_action_hash(self) -> HexBytes:
        return Web3.keccak(
            encode(
                [
                    "bytes32",
                    "uint",
                    "uint",
                    "address",
                    "bytes32",
                    "uint",
                    "address",
                    "address",
                ],
                [
                    self.action_typehash,
                    self.subaccount_id,
                    self.nonce,
                    Web3.to_checksum_address(self.module_address),
                    Web3.keccak(self.module_data.to_abi_encoded()),
                    self.signature_expiry_sec,
                    Web3.to_checksum_address(self.owner),
                    Web3.to_checksum_address(self.signer),
                ],
            )
        )
