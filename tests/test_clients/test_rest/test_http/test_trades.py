"""Tests for Trades module."""

from derive_client.data_types.generated_models import (
    TradeHistoryResponse,
)


def test_trades_private_list(client_admin_wallet):
    trades = client_admin_wallet.trades.list_private()
    assert isinstance(trades, list)
    assert all(isinstance(t, TradeHistoryResponse) for t in trades)
