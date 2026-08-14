"""Custom Exception classes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from derive_client.data_types import FeeEstimate
    from derive_client.data_types.generated_models import GetTransactionResult, RPCError, VaultActionResponse


class NotConnectedError(RuntimeError):
    """Raised when the client hasn't connected (call connect())."""


class DeriveJSONRPCError(Exception):
    """Raised when a Derive JSON-RPC error payload is returned."""

    def __init__(self, message_id: str | int, rpc_error: RPCError):
        super().__init__(f"{rpc_error.code}: {rpc_error.message} (message_id={message_id})")
        self.message_id = message_id
        self.rpc_error = rpc_error

    def __str__(self):
        base = f"Derive RPC {self.rpc_error.code}: {self.rpc_error.message}"
        return f"{base}  [data={self.rpc_error.data!r}]" if self.rpc_error.data is not None else base


class EthereumJSONRPCException(Exception):
    """Raised when an Ethereum JSON-RPC error payload is returned."""

    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.data = data

    def __str__(self):
        base = f"Ethereum RPC {self.code}: {self.args[0]}"
        return f"{base}  [data={self.data!r}]" if self.data is not None else base


class DeriveJSONRPCException(Exception):
    """Raised when a Derive JSON-RPC error payload is returned."""

    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.data = data

    def __str__(self):
        base = f"Derive RPC {self.code}: {self.args[0]}"
        return f"{base}  [data={self.data!r}]" if self.data is not None else base


class RequestAbandoned(RuntimeError):
    """An in-flight RPC was given up on because the connection went away."""


class InsufficientNativeBalance(Exception):
    """Raised when the native currency balance is insufficient for gas and/or value transfer."""

    def __init__(
        self,
        message: str,
        *,
        chain_id: int,
        balance: int,
        assumed_gas_limit: int,
        fee_estimate: FeeEstimate,
    ):
        super().__init__(message)
        self.chain_id = chain_id
        self.balance = balance
        self.assumed_gas_limit = assumed_gas_limit
        self.fee_estimate = fee_estimate


class InsufficientTokenBalance(Exception):
    """Raised when the token balance is insufficient for the requested operation."""


class TxReceiptMissing(Exception):
    """Raised when a transaction receipt is required but not available."""


class FinalityTimeout(Exception):
    """Raised when the transaction was mined but did not reach the required finality within the timeout."""


class TxPendingTimeout(Exception):
    """Raised when the transaction receipt does not materialize and the transaction remains in the mempool."""


class TransactionDropped(Exception):
    """Raised when the transaction the transaction is no longer in the mempool, likely dropped."""


class SettlementError(Exception):
    """Base for settlement outcomes that carry the last polled result."""

    def __init__(self, message: str, tx_result: GetTransactionResult | None = None):
        super().__init__(message)
        self.tx_result = tx_result


class SettlementFailed(SettlementError):
    """Terminal *Error status reported by the exchange. The operation will not settle."""


class SettlementTimeout(SettlementError):
    """Still in flight when the timeout elapsed. Not a failure: poll again with
    the same op_uuid, nothing is resubmitted."""


class VaultRequestError(Exception):
    """Base for vault request outcomes that carry the last polled history row."""

    def __init__(self, message: str, action: VaultActionResponse | None = None):
        super().__init__(message)
        self.action = action


class VaultRequestFailed(VaultRequestError):
    """The request reached a terminal status that is not a settlement: rejected
    by the curator, rejected by a protocol check (slippage, margin, cooldown),
    or expired because its signature lapsed before anyone settled it.

    Not raised for a cancellation, which is an outcome the caller asked for.
    """


class VaultRequestTimeout(VaultRequestError):
    """Still queued when the timeout elapsed. Not a failure: settlement is at
    the curator's discretion within a 14-day SLA, so a request that outlives a
    client-side timeout is waiting, not lost. Poll again with the same request
    id, or cancel it.

    `action` is None when the request had not yet appeared in the history at
    all, which is normal in the first seconds after queueing.
    """


class ChainIdMismatch(Exception):
    """An RPC endpoint reports a chain id other than the configured one."""

    def __init__(self, message: str, *, endpoint: str, expected: int, actual: int):
        super().__init__(message)
        self.endpoint = endpoint
        self.expected = expected
        self.actual = actual


class AllEndpointsFailed(Exception):
    """Every RPC endpoint failed or was disabled for a single request."""

    def __init__(self, message: str, *, method: str, failures: dict[str, str]):
        super().__init__(message)
        self.method = method
        self.failures = failures
