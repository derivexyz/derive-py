"""Trade management operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from derive_client.config import INT64_MAX
from derive_client.data_types.generated_models import (
    GetTradeHistoryRequest,
    TradeHistoryResponse,
)

if TYPE_CHECKING:
    from .subaccount import Subaccount


class TradeOperations:
    """High-level order management operations."""

    def __init__(self, subaccount: Subaccount):
        """
        Initialize order operations.

        Args:
            subaccount: Subaccount instance providing access to auth, config, and APIs
        """
        self._subaccount = subaccount

    def list_private(
        self,
        from_timestamp: int = 0,
        instrument_name: str | None = None,
        order_id: str | None = None,
        page: int = 1,
        page_size: int = 100,
        quote_id: str | None = None,
        to_timestamp: int = INT64_MAX,
    ) -> list[TradeHistoryResponse]:
        """Get trade history for a subaccount, with filter parameters."""

        params = GetTradeHistoryRequest(
            from_timestamp=from_timestamp,
            instrument_name=instrument_name,
            order_id=order_id,
            page=page,
            page_size=page_size,
            quote_id=quote_id,
            subaccount_id=self._subaccount.id,
            to_timestamp=to_timestamp,
            wallet=self._subaccount._auth.wallet,
        )
        result = self._subaccount._private_api.rpc.get_trade_history(params)
        return result.trades
