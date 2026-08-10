"""System operations."""

from __future__ import annotations

from derive_client._clients.rest.async_http.api import AsyncPublicAPI
from derive_client.data_types import LoggerType
from derive_client.data_types.generated_models import (
    GetTransactionParams,
    GetTransactionResult,
)


class SystemOperations:
    """High-level system operations."""

    def __init__(self, *, public_api: AsyncPublicAPI, logger: LoggerType):
        """
        Initialize system operations.

        Args:
            public_api: PublicAPI instance providing access to public APIs
            logger: Logger instance for logging
        """

        self._public_api = public_api
        self._logger = logger

    async def get_transaction(self, *, op_uuid: str) -> GetTransactionResult:
        """Get a transaction by its operation UUID."""

        params = GetTransactionParams(op_uuid=op_uuid)
        result = await self._public_api.rpc.get_transaction(params)
        return result
