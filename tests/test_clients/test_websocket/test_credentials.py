"""Clients without a signer, and with a signer for a wallet that has no Derive account yet."""

from decimal import Decimal

import pytest

from derive_py.data_types.generated_models import GetPendingDepositsParams
from derive_py.exceptions import CredentialsRequired, NoActiveSubaccount


@pytest.mark.asyncio
async def test_public_client_reads_market_data(client_public) -> None:
    ticker = await client_public.markets.get_ticker(instrument_name="ETH-PERP")
    assert Decimal(ticker.mark_price) > 0


@pytest.mark.asyncio
async def test_public_client_refuses_account_access(client_public) -> None:
    with pytest.raises(CredentialsRequired):
        _ = client_public.private_api
    with pytest.raises(CredentialsRequired):
        _ = client_public.account


@pytest.mark.asyncio
async def test_public_client_has_no_active_subaccount(client_public) -> None:
    with pytest.raises(NoActiveSubaccount):
        _ = client_public.orders


@pytest.mark.asyncio
async def test_fresh_wallet_connects_without_account(client_fresh_wallet) -> None:
    assert client_fresh_wallet.cached_subaccounts == []
    with pytest.raises(NoActiveSubaccount):
        _ = client_fresh_wallet.orders


@pytest.mark.asyncio
async def test_fresh_wallet_has_no_pending_deposits(client_fresh_wallet) -> None:
    params = GetPendingDepositsParams(wallet=client_fresh_wallet._auth.wallet)
    result = await client_fresh_wallet.public_api.rpc.get_pending_deposits(params)
    assert result.pending_deposits == []
