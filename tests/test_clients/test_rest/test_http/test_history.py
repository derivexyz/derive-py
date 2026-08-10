"""Tests for History module."""

import pytest

from derive_client._clients.rest.http.history import HistoryOperations
from derive_client.data_types.generated_models import (
    DepositHistoryResult,
    InterestHistoryResult,
    OptionSettlementHistoryResponse,
    PaginatedOrdersResult,
    PaginatedTradesResult,
    PerpSettlementHistoryResponse,
    TransferHistoryResult,
    WithdrawalHistoryResult,
)


def test_history_deposits(history_scope):
    result = history_scope.history.deposits()
    assert isinstance(result, DepositHistoryResult)


def test_history_withdrawals(history_scope):
    result = history_scope.history.withdrawals()
    assert isinstance(result, WithdrawalHistoryResult)


def test_history_erc20_transfers(history_scope):
    result = history_scope.history.erc20_transfers()
    assert isinstance(result, TransferHistoryResult)


def test_history_interest(history_scope):
    result = history_scope.history.interest()
    assert isinstance(result, InterestHistoryResult)


def test_history_option_settlements(history_scope):
    result = history_scope.history.option_settlements()
    assert isinstance(result, OptionSettlementHistoryResponse)


def test_history_funding(history_scope):
    result = history_scope.history.funding()
    assert isinstance(result, PerpSettlementHistoryResponse)


def test_history_orders(history_scope):
    result = history_scope.history.orders()
    assert isinstance(result, PaginatedOrdersResult)


def test_history_trades(history_scope):
    result = history_scope.history.trades()
    assert isinstance(result, PaginatedTradesResult)


def test_history_subaccount_scope(client_admin_wallet):
    history = client_admin_wallet.history
    assert history.subaccount_id == client_admin_wallet.active_subaccount.id
    assert history.wallet is None


def test_history_wallet_scope(client_admin_wallet):
    history = client_admin_wallet.account.history
    assert history.wallet == client_admin_wallet.account.address
    assert history.subaccount_id is None


def test_history_rejects_both_scopes(client_admin_wallet):
    with pytest.raises(ValueError):
        HistoryOperations(
            private_api=client_admin_wallet._private_api,
            wallet=client_admin_wallet.account.address,
            subaccount_id=client_admin_wallet.active_subaccount.id,
        )


def test_history_rejects_no_scope(client_admin_wallet):
    with pytest.raises(ValueError):
        HistoryOperations(private_api=client_admin_wallet._private_api)
