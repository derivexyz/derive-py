"""Tests for History module."""

import pytest

from derive_py._clients.rest.async_http.history import HistoryOperations
from derive_py.data_types.generated_models import (
    DepositHistoryResult,
    InterestHistoryResult,
    OptionSettlementHistoryResponse,
    PaginatedOrdersResult,
    PaginatedTradesResult,
    PerpSettlementHistoryResponse,
    TransferHistoryResult,
    WithdrawalHistoryResult,
)


@pytest.mark.asyncio
async def test_history_deposits(history_scope):
    result = await history_scope.history.deposits()
    assert isinstance(result, DepositHistoryResult)


@pytest.mark.asyncio
async def test_history_withdrawals(history_scope):
    result = await history_scope.history.withdrawals()
    assert isinstance(result, WithdrawalHistoryResult)


@pytest.mark.asyncio
async def test_history_erc20_transfers(history_scope):
    result = await history_scope.history.erc20_transfers()
    assert isinstance(result, TransferHistoryResult)


@pytest.mark.asyncio
async def test_history_interest(history_scope):
    result = await history_scope.history.interest()
    assert isinstance(result, InterestHistoryResult)


@pytest.mark.asyncio
async def test_history_option_settlements(history_scope):
    result = await history_scope.history.option_settlements()
    assert isinstance(result, OptionSettlementHistoryResponse)


@pytest.mark.asyncio
async def test_history_funding(history_scope):
    result = await history_scope.history.funding()
    assert isinstance(result, PerpSettlementHistoryResponse)


@pytest.mark.asyncio
async def test_history_orders(history_scope):
    result = await history_scope.history.orders()
    assert isinstance(result, PaginatedOrdersResult)


@pytest.mark.asyncio
async def test_history_trades(history_scope):
    result = await history_scope.history.trades()
    assert isinstance(result, PaginatedTradesResult)


@pytest.mark.asyncio
async def test_history_subaccount_scope(client_admin_wallet):
    history = client_admin_wallet.history
    assert history.subaccount_id == client_admin_wallet.active_subaccount.id
    assert history.wallet is None


@pytest.mark.asyncio
async def test_history_wallet_scope(client_admin_wallet):
    history = client_admin_wallet.account.history
    assert history.wallet == client_admin_wallet.account.address
    assert history.subaccount_id is None


@pytest.mark.asyncio
async def test_history_rejects_both_scopes(client_admin_wallet):
    with pytest.raises(ValueError):
        HistoryOperations(
            private_api=client_admin_wallet._private_api,
            wallet=client_admin_wallet.account.address,
            subaccount_id=client_admin_wallet.active_subaccount.id,
        )


@pytest.mark.asyncio
async def test_history_rejects_no_scope(client_admin_wallet):
    with pytest.raises(ValueError):
        HistoryOperations(private_api=client_admin_wallet._private_api)
