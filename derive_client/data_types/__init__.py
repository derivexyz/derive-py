"""Enums and Models used in the derive_client module"""

from logging import Logger, LoggerAdapter

from .enums import (
    DeriveJSONRPCErrorCode,
    Environment,
    EthereumJSONRPCErrorCode,
    GasPriority,
    UniverseType,
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
    "D",
    "LoggerType",
    "ChecksumAddress",
    "Direction",
    "EnvConfig",
    "AssetType",
    "EthereumJSONRPCErrorCode",
    "DeriveJSONRPCErrorCode",
    "DeriveContractAddresses",
    "OrderType",
    "Environment",
    "ClientConfig",
    "GasPriority",
    "FeeHistory",
    "FeeEstimate",
    "FeeEstimates",
    "MarginType",
    "RPCEndpoints",
    "PositionTransfer",
    "TxHash",
    "TypedFilterParams",
    "TypedLogReceipt",
    "TypedSignedTransaction",
    "TypedTransaction",
    "TypedTxReceipt",
    "UniverseType",
    "Wei",
]
