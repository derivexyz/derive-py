"""Tests for Subaccount module."""


def test_subaccount_setup_config(client_owner_wallet):
    assert client_owner_wallet.active_subaccount.margin_type == "SM"
    assert client_owner_wallet.active_subaccount.state.manager_id == 1
    assert client_owner_wallet.active_subaccount.state.risk_universe_id == 1
    currency = client_owner_wallet.active_subaccount.currency
    assert isinstance(currency, list)
