"""Enums and Models used in the derive_client module"""

from logging import Logger, LoggerAdapter

from .enums import (
    ConnectionState,
    DeriveJSONRPCErrorCode,
    Environment,
    EthereumJSONRPCErrorCode,
    GasPriority,
    OffchainScope,
    ProtocolScope,
    RiskUniverseID,
    VaultAction,
)
from .generated_models import (
    AssetType,
    Direction,
    MarginType,
    OrderType,
)
from .models import (
    AsyncHTTPSessionConfig,
    ChecksumAddress,
    ClientConfig,
    DeriveContractAddresses,
    EnvConfig,
    FeeEstimate,
    FeeEstimates,
    FeeHistory,
    HTTPSessionConfig,
    PositionTransfer,
    TxHash,
    TypedFilterParams,
    TypedLogReceipt,
    TypedSignedTransaction,
    TypedTransaction,
    TypedTxReceipt,
    WebSocketSessionConfig,
    Wei,
)
from .utils import D

LoggerType = Logger | LoggerAdapter


__all__ = [
    "AssetType",
    "AsyncHTTPSessionConfig",
    "ChecksumAddress",
    "ClientConfig",
    "ConnectionState",
    "D",
    "DeriveJSONRPCErrorCode",
    "DeriveContractAddresses",
    "Direction",
    "Environment",
    "EnvConfig",
    "EthereumJSONRPCErrorCode",
    "FeeHistory",
    "FeeEstimate",
    "FeeEstimates",
    "HTTPSessionConfig",
    "GasPriority",
    "LoggerType",
    "MarginType",
    "OffchainScope",
    "OrderType",
    "PositionTransfer",
    "ProtocolScope",
    "TxHash",
    "TypedFilterParams",
    "TypedLogReceipt",
    "TypedSignedTransaction",
    "TypedTransaction",
    "TypedTxReceipt",
    "RiskUniverseID",
    "VaultAction",
    "WebSocketSessionConfig",
    "Wei",
]
