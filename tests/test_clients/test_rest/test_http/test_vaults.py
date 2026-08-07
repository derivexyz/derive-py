"""Tests for the Vaults module.

Runs against live testnet, like the rest of test_http. A vault must exist for
most of this to mean anything, and one cannot be created here: creating is
irreversible, one-shot, and costs the seed deposit plus the creation fee. The
fixtures skip rather than fail when the exchange has no usable vault, so a
clean testnet does not look like a broken client.

The write path is a queue-and-cancel round trip. A deposit holds funds on the
source subaccount until it is settled or cancelled, so every test that queues
one cancels it, and cancel_all_requests is all-or-nothing per vault anyway.
"""

import time
from decimal import Decimal

import msgspec
import pytest

from derive_client.data_types.generated_models import (
    MultipleVaultRequestsResponse,
    PaginatedVaultActionHistory,
    PaginatedVaultRequestHistory,
    PerformanceResolution,
    Vault,
    VaultCancelResponse,
    VaultIdsResponse,
    VaultRequestAckResponse,
    VaultSharesResponse,
    VaultsResponse,
)
from tests.conftest import assert_api_calls

DEPOSIT_AMOUNT = Decimal("10")


# ---------------------------------------------------------------------------
# Public reads
# ---------------------------------------------------------------------------


def test_vaults_list_all(client_admin_wallet):
    with assert_api_calls(client_admin_wallet, expected=1):
        listed = client_admin_wallet.vaults.list_all(page=1, page_size=10)
    assert isinstance(listed, VaultsResponse)
    assert all(isinstance(vault, Vault) for vault in listed.vaults)


def test_vaults_get(client_admin_wallet, any_vault):
    with assert_api_calls(client_admin_wallet, expected=1):
        vault = client_admin_wallet.vaults.get(vault_subaccount_id=any_vault.protocol.subaccount_id)
    assert isinstance(vault, Vault)
    assert vault.protocol.subaccount_id == any_vault.protocol.subaccount_id


def test_vaults_get_defaults_to_this_subaccount(client_admin_wallet, curated_vault):
    vault_subaccount = client_admin_wallet.fetch_subaccount(curated_vault)
    vault = vault_subaccount.vaults.get()
    assert vault.protocol.subaccount_id == curated_vault


def test_vaults_action_history(client_admin_wallet, any_vault):
    with assert_api_calls(client_admin_wallet, expected=1):
        history = client_admin_wallet.vaults.action_history(
            vault_subaccount_id=any_vault.protocol.subaccount_id, page=1, page_size=10
        )
    assert isinstance(history, PaginatedVaultActionHistory)


def test_vaults_performance_history(client_admin_wallet, any_vault):
    with assert_api_calls(client_admin_wallet, expected=1):
        performance = client_admin_wallet.vaults.performance_history(
            vault_subaccount_id=any_vault.protocol.subaccount_id,
            resolution=PerformanceResolution.field_24h,
            limit=10,
        )
    assert performance.resolution == PerformanceResolution.field_24h


def test_vault_pricing_may_be_unset(any_vault):
    """nav_usd and simulated_share_price_usd are unset when the vault cannot be
    priced right now. The settle loop quotes from the latter, so treating unset
    as zero would quote a free vault."""

    for value in (any_vault.nav_usd, any_vault.simulated_share_price_usd):
        assert value is None or isinstance(value, Decimal) or value is msgspec.UNSET


# ---------------------------------------------------------------------------
# Wallet-scoped reads
# ---------------------------------------------------------------------------


def test_vaults_list_curated(client_admin_wallet):
    with assert_api_calls(client_admin_wallet, expected=1):
        curated = client_admin_wallet.vaults.list_curated()
    assert isinstance(curated, VaultIdsResponse)


def test_vaults_list_shareholdings(client_admin_wallet):
    with assert_api_calls(client_admin_wallet, expected=1):
        held = client_admin_wallet.vaults.list_shareholdings()
    assert isinstance(held, VaultIdsResponse)


def test_vaults_shares(client_admin_wallet):
    with assert_api_calls(client_admin_wallet, expected=1):
        shares = client_admin_wallet.vaults.shares()
    assert isinstance(shares, VaultSharesResponse)


def test_vaults_list_live_requests(client_admin_wallet):
    with assert_api_calls(client_admin_wallet, expected=1):
        live = client_admin_wallet.vaults.list_live_requests()
    assert isinstance(live, MultipleVaultRequestsResponse)


def test_vaults_request_history(client_admin_wallet):
    with assert_api_calls(client_admin_wallet, expected=1):
        history = client_admin_wallet.vaults.request_history(page=1, page_size=10)
    assert isinstance(history, PaginatedVaultRequestHistory)


# ---------------------------------------------------------------------------
# Curator reads, keyed on the vault subaccount
# ---------------------------------------------------------------------------


def test_vaults_list_live_mint_requests(client_admin_wallet, curated_vault):
    with assert_api_calls(client_admin_wallet, expected=1):
        queue = client_admin_wallet.vaults.list_live_mint_requests(vault_subaccount_id=curated_vault)
    assert isinstance(queue, MultipleVaultRequestsResponse)


def test_vaults_list_live_burn_requests(client_admin_wallet, curated_vault):
    with assert_api_calls(client_admin_wallet, expected=1):
        queue = client_admin_wallet.vaults.list_live_burn_requests(vault_subaccount_id=curated_vault)
    assert isinstance(queue, MultipleVaultRequestsResponse)


def test_vaults_update_info(client_admin_wallet, curated_vault):
    """Off-chain patch, unsigned, gated to the curator by an ownership check.

    Settle approvals sign on the vault subaccount rather than the curator's
    funding account, so the curator surface is reached through a Subaccount
    instantiated for the vault. Fetched outside the assertion block, which
    counts calls.

    Writes back the vault's current description rather than a fixed string: the
    field is real metadata on a real vault, and a test should not rename it.
    """

    vault_subaccount = client_admin_wallet.fetch_subaccount(curated_vault)
    vault = vault_subaccount.vaults.get()
    with assert_api_calls(client_admin_wallet, expected=1):
        ack = vault_subaccount.vaults.update_info(description=vault.description)
    assert ack.status


# ---------------------------------------------------------------------------
# Shareholder writes
# ---------------------------------------------------------------------------


def test_vaults_request_deposit_and_cancel(client_admin_wallet, any_vault):
    """The deposit holds funds on this subaccount until settled or cancelled, so
    the cancel is cleanup, not a separate scenario."""

    vault_id = any_vault.protocol.subaccount_id
    try:
        with assert_api_calls(client_admin_wallet, expected=1):
            ack = client_admin_wallet.vaults.request_deposit(
                vault_subaccount_id=vault_id,
                deposit_spot_asset=any_vault.protocol.config.deposit_spot_asset,
                amount=DEPOSIT_AMOUNT,
            )
        assert isinstance(ack, VaultRequestAckResponse)
        assert ack.request_id.vault_subaccount_id == vault_id
    finally:
        cancelled = client_admin_wallet.vaults.cancel_all_requests(vault_subaccount_id=vault_id)
        assert isinstance(cancelled, VaultCancelResponse)


def test_queued_deposit_appears_in_the_live_queue(client_admin_wallet, any_vault):
    """The queued intent is the only thing that proves the signature verified:
    the server rebuilt the payload from the typed params to check it, and what
    comes back on signed_action.action.data is that reconstruction."""

    vault_id = any_vault.protocol.subaccount_id
    try:
        ack = client_admin_wallet.vaults.request_deposit(
            vault_subaccount_id=vault_id,
            deposit_spot_asset=any_vault.protocol.config.deposit_spot_asset,
            amount=DEPOSIT_AMOUNT,
        )
        live = client_admin_wallet.vaults.list_live_requests()
        queued = [row for row in live.requests if row.id == ack.request_id]
        assert queued, f"queued request {ack.request_id} missing from {live.total} live entries"
        assert bytes(queued[0].signed_action.action.data)
    finally:
        client_admin_wallet.vaults.cancel_all_requests(vault_subaccount_id=vault_id)


def test_cancel_all_requests_is_idempotent(client_admin_wallet, any_vault):
    """There is no cancel-one, and cancelling an empty queue is how a winddown
    keeps rejecting new intents without special-casing the first pass."""

    vault_id = any_vault.protocol.subaccount_id
    client_admin_wallet.vaults.cancel_all_requests(vault_subaccount_id=vault_id)
    again = client_admin_wallet.vaults.cancel_all_requests(vault_subaccount_id=vault_id)
    assert again.cancelled_request_ids == []


def test_vaults_request_withdraw_needs_shares(client_admin_wallet, any_vault):
    """Redemption is bounded by the holder's balance and by the vault's cooldown
    since their last deposit (18011). Skipped rather than asserted on the error,
    since which of the two fires depends on this wallet's history."""

    vault_id = any_vault.protocol.subaccount_id
    holdings = client_admin_wallet.vaults.shares()
    held = {entry.vault.protocol.subaccount_id: entry.shares for entry in holdings.vaults}
    if not held.get(vault_id):
        pytest.skip(f"this wallet holds no shares in vault {vault_id}")

    try:
        ack = client_admin_wallet.vaults.request_withdraw(
            vault_subaccount_id=vault_id,
            shares_to_burn=min(held[vault_id], Decimal("0.001")),
        )
        assert isinstance(ack, VaultRequestAckResponse)
    finally:
        client_admin_wallet.vaults.cancel_all_requests(vault_subaccount_id=vault_id)


def test_intent_signature_expiry_defaults_well_beyond_an_hour(client_admin_wallet, any_vault):
    """Curators settle at their own pace within a 14-day SLA. The client-wide
    1-hour default would let a deposit reach `expired` in the queue rather than
    fill, which is why the intents override it."""

    vault_id = any_vault.protocol.subaccount_id
    try:
        ack = client_admin_wallet.vaults.request_deposit(
            vault_subaccount_id=vault_id,
            deposit_spot_asset=any_vault.protocol.config.deposit_spot_asset,
            amount=DEPOSIT_AMOUNT,
        )
        live = client_admin_wallet.vaults.list_live_requests()
        queued = next(row for row in live.requests if row.id == ack.request_id)
        assert queued.signed_action.action.expiry - int(time.time()) > 24 * 60 * 60
    finally:
        client_admin_wallet.vaults.cancel_all_requests(vault_subaccount_id=vault_id)
