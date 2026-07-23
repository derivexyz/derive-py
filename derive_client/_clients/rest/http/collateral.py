"""Collateral management operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from derive_client.data_types.generated_models import (
    GetCollateralsRequest,
    PrivateGetCollateralsResponse,
)

if TYPE_CHECKING:
    from .subaccount import Subaccount


class CollateralOperations:
    """Collateral management operations."""

    def __init__(self, *, subaccount: Subaccount):
        """
        Initialize collateral operations.

        Args:
            subaccount: Subaccount instance providing access to auth, config, and APIs
        """
        self._subaccount = subaccount

    def get(self) -> PrivateGetCollateralsResponse:
        """Get collaterals of a subaccount."""

        subaccount_id = self._subaccount.id
        params = GetCollateralsRequest(subaccount_id=subaccount_id)
        result = self._subaccount._private_api.rpc.get_collaterals(params)
        return result
