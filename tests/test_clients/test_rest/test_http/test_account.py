"""Tests for (Light)Account module."""

from derive_client.data_types.generated_models import (
    PrivateGetAccountResponse,
    PrivateGetSubaccountsResponse,
    PrivateSessionKeysResponse,
    SessionKey,
    Subaccount,
)


def test_account_edit_session_key(client_admin_wallet):
    session_keys = client_admin_wallet.account.session_keys()
    public_session_key = session_keys.public_session_keys[0].public_session_key
    session_key = client_admin_wallet.account.edit_session_key(public_session_key=public_session_key)
    assert isinstance(session_key, SessionKey)


def test_account_session_keys(client_admin_wallet):
    session_keys = client_admin_wallet.account.session_keys()
    assert isinstance(session_keys, PrivateSessionKeysResponse)


def test_account_get_all_portfolios(client_admin_wallet):
    all_portfolios = client_admin_wallet.account.get_all_portfolios()
    assert isinstance(all_portfolios, list)
    assert all(isinstance(item, Subaccount) for item in all_portfolios)


def test_account_get_subaccounts(client_admin_wallet):
    subaccounts = client_admin_wallet.account.get_subaccounts()
    assert isinstance(subaccounts, PrivateGetSubaccountsResponse)


def test_account_get(client_admin_wallet):
    account = client_admin_wallet.account.get()
    assert isinstance(account, PrivateGetAccountResponse)
