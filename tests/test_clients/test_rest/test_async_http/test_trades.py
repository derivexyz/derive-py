"""Tests for Trades module."""

import pytest

from derive_client.data_types.generated_models import (
    TradeHistoryResponse,
)


@pytest.mark.asyncio
async def test_trades_private_list(client_admin_wallet):
    trades = await client_admin_wallet.trades.list_private()
    assert isinstance(trades, list)
    assert all(isinstance(t, TradeHistoryResponse) for t in trades)
