"""Typed models for on-chain data and client configuration."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, cast

from eth_account.datastructures import SignedTransaction
from eth_typing import BlockNumber, HexStr
from eth_typing import ChecksumAddress as ETHChecksumAddress
from eth_utils.address import is_address, to_checksum_address
from eth_utils.hexadecimal import is_0x_prefixed, is_hex
from hexbytes import HexBytes
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    RootModel,
    SecretStr,
    model_validator,
)
from pydantic_core import core_schema
from web3.types import FilterParams, LogReceipt, TxReceipt
from web3.types import Wei as ETHWei

from .enums import (
    Chain,
    GasPriority,
)


class DeriveContractAddresses(BaseModel, frozen=True):
    TRADE_MODULE: ChecksumAddress
    TRANSFER_MODULE: ChecksumAddress
    WITHDRAW_MODULE: ChecksumAddress
    RFQ_MODULE: ChecksumAddress
    EXTERNAL_TRANSFER_MODULE: ChecksumAddress
    WHITELISTED_RECIPIENT_MODULE: ChecksumAddress
    VAULT_MODULE: ChecksumAddress
    LIQUIDATION_MODULE: ChecksumAddress
    CREATE_SESSION_KEY_MODULE: ChecksumAddress

    # addresses matching ABIs downloaded and stored in data/abis/<network>/contracts.json
    ACTION_MANAGER: ChecksumAddress
    VAPP: ChecksumAddress
    WITHDRAWAL_OUTBOX: ChecksumAddress
    SPOT_VAULT: ChecksumAddress

    def __getitem__(self, key):
        return getattr(self, key)


class ChainConfig(BaseModel, frozen=True):
    base_url: str
    ws_address: str
    ACTION_TYPEHASH: str
    DOMAIN_SEPARATOR: str
    contracts: DeriveContractAddresses


class ClientConfig(BaseModel):
    session_key: SecretStr
    wallet: ChecksumAddress
    subaccount_id: int
    chain: Chain
    rpc_endpoints: tuple[str, ...] | None = None


class _HTTPSessionConfigBase(BaseModel, frozen=True):
    """Retry settings shared by the synchronous and asynchronous HTTP sessions."""

    # Per attempt, not total: a retried request can take up to
    # max_attempts * request_timeout, plus backoff.
    request_timeout: float = Field(default=10.0, gt=0)

    max_attempts: int = Field(default=4, ge=1)
    backoff_factor: float = Field(default=0.2, ge=0)
    backoff_max: float = Field(default=10.0, gt=0)
    retry_statuses: frozenset[int] = frozenset({429, 500, 502, 503, 504})


class HTTPSessionConfig(_HTTPSessionConfigBase, frozen=True):
    """Transport and retry settings for a synchronous HTTP session.

    `request_timeout` bounds connect and between-bytes time, not total elapsed:
    requests passes one scalar to both.
    """

    pool_connections: int = Field(default=10, ge=1)
    # Size of the idle-connection cache, not a concurrency cap: over this many
    # in-flight requests, urllib3 opens extra connections and discards them.
    pool_maxsize: int = Field(default=20, ge=1)


class AsyncHTTPSessionConfig(_HTTPSessionConfigBase, frozen=True):
    """Transport and retry settings for an asynchronous HTTP session.

    `request_timeout` is a wall-clock bound on the whole request, unlike the
    synchronous session's scalar.
    """

    limit: int = Field(default=100, ge=1)
    limit_per_host: int = Field(default=10, ge=1)
    keepalive_timeout: float = Field(default=30.0, gt=0)


class WebSocketSessionConfig(BaseModel, frozen=True):
    """Transport and reconnection settings for a WebSocket session."""

    request_timeout: float = 10.0
    reconnect: bool = True
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 60.0

    open_timeout: float = 10.0
    close_timeout: float = 5.0
    max_size: int = 16 * 1024 * 1024

    # The venue pings on its own ~180s heartbeat and `websockets` answers automatically.
    # These are our pings, and they are what detects a half-open connection:
    # worst case ping_interval + ping_timeout.
    ping_interval: float = 20.0
    ping_timeout: float = 20.0

    @model_validator(mode="after")
    def _delays_are_ordered(self) -> WebSocketSessionConfig:
        if self.reconnect_delay > self.max_reconnect_delay:
            raise ValueError("reconnect_delay cannot exceed max_reconnect_delay")
        return self


class PHexBytes(HexBytes):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source: Any, _handler: Any) -> core_schema.CoreSchema:
        # Allow either HexBytes or bytes/hex strings to be parsed into HexBytes
        return core_schema.no_info_before_validator_function(
            cls._validate,
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(HexBytes),
                    core_schema.bytes_schema(),
                    core_schema.str_schema(),
                ]
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, _schema: core_schema.CoreSchema, _handler: Any) -> dict:
        return {"type": "string", "format": "hex"}

    @classmethod
    def _validate(cls, v: Any) -> HexBytes:
        if isinstance(v, HexBytes):
            return v
        if isinstance(v, (bytes, bytearray)):
            return HexBytes(v)
        if isinstance(v, str):
            return HexBytes(v)
        raise TypeError(f"Expected HexBytes-compatible type, got {type(v).__name__}")


class ChecksumAddress(str):
    """ChecksumAddress with validation."""

    def __new__(cls, v: str) -> ChecksumAddress:
        if not is_address(v):
            raise ValueError(f"Invalid Ethereum address: {v}")
        return cast(ChecksumAddress, to_checksum_address(v))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source, _handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.no_info_before_validator_function(cls._validate, core_schema.any_schema())

    @classmethod
    def __get_pydantic_json_schema__(cls, _schema, _handler: GetJsonSchemaHandler) -> dict:
        return {"type": "string", "format": "ethereum-address"}

    @classmethod
    def _validate(cls, v) -> ChecksumAddress:
        if isinstance(v, cls):
            return v
        if not isinstance(v, str):
            raise TypeError(f"Expected str, got {type(v)}")
        return cls(v)


class TxHash(str):
    """Transaction hash with validation."""

    def __new__(cls, value: str | HexBytes) -> TxHash:
        if isinstance(value, HexBytes):
            value = value.to_0x_hex()
        if not isinstance(value, str):
            raise TypeError(f"Expected string or HexBytes, got {type(value)}")
        if not is_0x_prefixed(value) or not is_hex(value) or len(value) != 66:
            raise ValueError(f"Invalid transaction hash: {value}")
        return cast(TxHash, value)

    @classmethod
    def __get_pydantic_core_schema__(cls, _source, _handler: GetCoreSchemaHandler):
        return core_schema.no_info_before_validator_function(cls._validate, core_schema.str_schema())

    @classmethod
    def __get_pydantic_json_schema__(cls, _schema, _handler: GetJsonSchemaHandler):
        return {"type": "string", "format": "ethereum-tx-hash"}

    @classmethod
    def _validate(cls, v: str | HexBytes) -> str:
        if isinstance(v, HexBytes):
            v = v.to_0x_hex()
        if not isinstance(v, str):
            raise TypeError("Expected a string or HexBytes for TxHash")
        if not is_0x_prefixed(v) or not is_hex(v) or len(v) != 66:
            raise ValueError(f"Invalid Ethereum transaction hash: {v}")
        return v


class Wei(int):
    """Wei with validation."""

    def __new__(cls, value: str | int) -> Wei:
        if isinstance(value, str) and is_hex(value):
            value = int(value, 16)
        return cast(Wei, value)

    @classmethod
    def __get_pydantic_core_schema__(cls, _source, _handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.no_info_before_validator_function(cls._validate, core_schema.int_schema())

    @classmethod
    def __get_pydantic_json_schema__(cls, _schema, _handler: GetJsonSchemaHandler) -> dict:
        return {"type": ["string", "integer"], "title": "Wei"}

    @classmethod
    def _validate(cls, v: str | int) -> int:
        if isinstance(v, int):
            return v
        if isinstance(v, str) and is_hex(v):
            return int(v, 16)
        raise TypeError(f"Invalid type for Wei: {type(v)}")


class TypedFilterParams(BaseModel):
    """Typed filter params for eth_getLogs that we actually use.

    Unlike web3.types.FilterParams which has overly-broad unions,
    this reflects our actual runtime behavior:
    - We work with int block numbers internally
    - We convert to hex strings right before RPC calls
    - We use 'latest' as a special case for open-ended queries
    """

    model_config = ConfigDict(frozen=True)

    address: ChecksumAddress | list[ChecksumAddress]
    topics: tuple[PHexBytes | None, ...] | None = None

    # Block range - we use int internally, convert to hex for RPC
    # 'latest' is used as sentinel for open-ended queries
    fromBlock: int | Literal["latest"]
    toBlock: int | Literal["latest"]
    blockHash: PHexBytes | None = None

    def to_rpc_params(self) -> FilterParams:
        """Convert to RPC-compatible filter params with hex block numbers."""

        address: ETHChecksumAddress | list[ETHChecksumAddress]
        if isinstance(self.address, list):
            address = [cast(ETHChecksumAddress, addr) for addr in self.address]
        else:
            address = cast(ETHChecksumAddress, self.address)

        from_block = cast(HexStr, hex(self.fromBlock)) if self.fromBlock != "latest" else self.fromBlock
        to_block = cast(HexStr, hex(self.toBlock)) if self.toBlock != "latest" else self.toBlock

        params: FilterParams = {
            "address": address,
            "fromBlock": from_block,
            "toBlock": to_block,
        }

        if self.topics is not None:
            params["topics"] = [cast(HexStr, topic.to_0x_hex()) if topic is not None else None for topic in self.topics]
        if self.blockHash is not None:
            params["blockHash"] = self.blockHash

        return params


class TypedLogReceipt(BaseModel):
    """Typed log entry from transaction receipt."""

    address: ChecksumAddress
    blockHash: PHexBytes
    blockNumber: int
    data: PHexBytes
    logIndex: int
    removed: bool
    topics: list[PHexBytes]
    transactionHash: PHexBytes
    transactionIndex: int

    def to_w3(self) -> LogReceipt:
        """Convert to web3.py LogReceipt dict."""

        return LogReceipt(
            address=cast(ETHChecksumAddress, self.address),
            blockHash=self.blockHash,
            blockNumber=cast(BlockNumber, self.blockNumber),
            data=self.data,
            logIndex=self.logIndex,
            removed=self.removed,
            topics=self.topics,
            transactionHash=self.transactionHash,
            transactionIndex=self.transactionIndex,
        )


class TypedTxReceipt(BaseModel):
    """Fully typed transaction receipt with attribute access.

    Based on web3.types.TxReceipt but actually usable with type checkers.
    All fields from EIP-658 and common extensions included.
    """

    model_config = ConfigDict(populate_by_name=True)

    blockHash: PHexBytes
    blockNumber: int
    contractAddress: ChecksumAddress | None
    cumulativeGasUsed: int
    effectiveGasPrice: int
    from_: ChecksumAddress = Field(alias='from')
    gasUsed: int
    logs: list[TypedLogReceipt]
    logsBloom: PHexBytes
    status: int  # 0 or 1 per EIP-658
    to: ChecksumAddress
    transactionHash: PHexBytes
    transactionIndex: int
    type: int = Field(alias='type')  # Transaction type (0=legacy, 1=EIP-2930, 2=EIP-1559)

    # Optional fields (depending on chain/tx type)
    root: HexStr | None = None  # Pre-EIP-658 state root
    # blobGasPrice: int | None = None  # EIP-4844
    # blobGasUsed: int | None = None  # EIP-4844

    def to_w3(self) -> TxReceipt:
        """Convert to web3.py TxReceipt dict."""

        tx_receipt = {
            'blockHash': self.blockHash,
            'blockNumber': cast(BlockNumber, self.blockNumber),
            'contractAddress': cast(ETHChecksumAddress, self.contractAddress) if self.contractAddress else None,
            'cumulativeGasUsed': self.cumulativeGasUsed,
            'effectiveGasPrice': cast(ETHWei, self.effectiveGasPrice),
            'from': cast(ETHChecksumAddress, self.from_),
            'gasUsed': self.gasUsed,
            'logs': [log.to_w3() for log in self.logs],
            'logsBloom': self.logsBloom,
            'status': self.status,
            'to': cast(ETHChecksumAddress, self.to),
            'transactionHash': self.transactionHash,
            'transactionIndex': self.transactionIndex,
            'type': self.type,
        }
        if self.root is not None:
            tx_receipt["root"] = self.root

        # web3.py's definition is WRONG.
        # EIP-658 (Byzantium fork, 2017) replaced root with status
        # Pre-EIP-658 receipts: Have root, don't have status
        # Post-EIP-658 receipts: Have status, don't have root
        return cast(TxReceipt, tx_receipt)


class TypedSignedTransaction(BaseModel):
    """Properly typed signed transaction.

    Immutable replacement for eth_account.datastructures.SignedTransaction.
    """

    model_config = ConfigDict(frozen=True)

    raw_transaction: PHexBytes
    hash: PHexBytes
    r: int
    s: int
    v: int

    def to_w3(self) -> SignedTransaction:
        """Convert to eth_account SignedTransaction."""

        return SignedTransaction(
            raw_transaction=self.raw_transaction,
            hash=self.hash,
            r=self.r,
            s=self.s,
            v=self.v,
        )


class TypedTransaction(BaseModel):
    """Fully typed transaction data retrieved from the blockchain.

    Based on web3.types.TxData but with proper attribute access.
    This represents a transaction that has been retrieved from a node,
    which may or may not be mined yet.
    """

    model_config = ConfigDict(populate_by_name=True)

    blockHash: PHexBytes | None
    blockNumber: int | None  # None if pending
    from_: ChecksumAddress = Field(alias='from')
    gas: int
    gasPrice: int | None = None  # Legacy transactions
    maxFeePerGas: int | None = None  # EIP-1559
    maxPriorityFeePerGas: int | None = None  # EIP-1559
    hash: PHexBytes
    input: PHexBytes
    nonce: int
    to: ChecksumAddress | None  # None for contract creation
    transactionIndex: int | None  # None if pending
    value: int
    type: int  # 0=legacy, 1=EIP-2930, 2=EIP-1559
    chainId: int | None = None
    v: int
    r: PHexBytes
    s: PHexBytes

    # EIP-2930 (optional)
    accessList: list[dict[str, Any]] | None = None

    # EIP-4844 (optional)
    maxFeePerBlobGas: int | None = None
    blobVersionedHashes: list[PHexBytes] | None = None


class FeeHistory(BaseModel):
    base_fee_per_gas: list[Wei] = Field(alias="baseFeePerGas")
    gas_used_ratio: list[float] = Field(alias="gasUsedRatio")
    base_fee_per_blob_gas: list[Wei] | None = Field(default=None, alias="baseFeePerBlobGas")
    blob_gas_used_ratio: list[float] | None = Field(default=None, alias="blobGasUsedRatio")
    oldest_block: int = Field(alias="oldestBlock")
    reward: list[list[Wei]]


@dataclass
class FeeEstimate:
    max_fee_per_gas: int
    max_priority_fee_per_gas: int


class FeeEstimates(RootModel):
    root: dict[GasPriority, FeeEstimate]

    def __getitem__(self, key: GasPriority):
        return self.root[key]

    def items(self):
        return self.root.items()


@dataclass
class PositionTransfer:
    """Position to transfer between subaccounts."""

    instrument_name: str
    amount: Decimal  # Can be negative (sign indicates long/short)
