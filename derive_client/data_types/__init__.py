"""Enums and Models used in the derive_client module"""

from logging import Logger, LoggerAdapter

from .enums import (
    DeriveJSONRPCErrorCode,
    Environment,
    EthereumJSONRPCErrorCode,
    GasPriority,
    OffchainScope,
    ProtocolScope,
    RiskUniverseID,
)
from .generated_models import (
    AssetType,
    Direction,
    MarginType,
    OrderType,
)
from .models import (
    ChecksumAddress,
    ClientConfig,
    DeriveContractAddresses,
    EnvConfig,
    FeeEstimate,
    FeeEstimates,
    FeeHistory,
    PositionTransfer,
    RPCEndpoints,
    TxHash,
    TypedFilterParams,
    TypedLogReceipt,
    TypedSignedTransaction,
    TypedTransaction,
    TypedTxReceipt,
    Wei,
)
from .utils import D

LoggerType = Logger | LoggerAdapter


__all__ = [
    "AssetType",
    "ChecksumAddress",
    "ClientConfig",
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
    "GasPriority",
    "LoggerType",
    "MarginType",
    "OffchainScope",
    "OrderType",
    "PositionTransfer",
    "ProtocolScope",
    "RPCEndpoints",
    "TxHash",
    "TypedFilterParams",
    "TypedLogReceipt",
    "TypedSignedTransaction",
    "TypedTransaction",
    "TypedTxReceipt",
    "RiskUniverseID",
    "Wei",
]
