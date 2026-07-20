"""Transaction operations."""

from __future__ import annotations

from derive_client._clients.rest.http.api import PublicAPI
from derive_client.data_types import LoggerType
from derive_client.data_types.generated_models import (
    GetTransactionParams,
    GetTransactionResult,
)


class TransactionOperations:
    """High-level transaction operations."""

    def __init__(self, *, public_api: PublicAPI, logger: LoggerType):
        """
        Initialize transactions operations.

        Args:
            public_api: PublicAPI instance providing access to public APIs
        """

        self._public_api = public_api
        self._logger = logger

    def get(self, *, op_uuid: str) -> GetTransactionResult:
        """
        Get a transaction by its operation UUID.

        v3 change: the request field is now op_uuid (was transaction_id).
        """

        params = GetTransactionParams(op_uuid=op_uuid)
        result = self._public_api.rpc.get_transaction(params)
        return result
