"""Enums and Models used in the derive_py module"""

from logging import Logger, LoggerAdapter

from .enums import (
    Chain,
    ConnectionState,
    DeriveJSONRPCErrorCode,
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
    ChainConfig,
    ChecksumAddress,
    ClientConfig,
    DeriveContractAddresses,
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
    "Chain",
    "ChecksumAddress",
    "ClientConfig",
    "ConnectionState",
    "D",
    "DeriveJSONRPCErrorCode",
    "DeriveContractAddresses",
    "Direction",
    "ChainConfig",
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
