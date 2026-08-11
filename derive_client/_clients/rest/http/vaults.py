"""Vault operations.

A vault is a subaccount with extra protocol state on top, traded by a *curator*
on behalf of *shareholders*. Curating is not a privileged role: any wallet can
create a vault, and a curator normally also holds shares in their own.

Every vault endpoint carries a `subaccount_id`, and in every case it means
**the subaccount you are acting as**, which is why this module hangs off
Subaccount rather than the client:

    shareholder     subaccount.vaults.request_deposit(vault_subaccount_id=...)
                    self.id is the source of the funds

    curator, seed   subaccount.vaults.create(...)
                    self.id is the funding subaccount the seed leaves

    curator, settle client.fetch_subaccount(vault_id).vaults.mint_shares(...)
                    self.id IS the vault

The settle approvals are the trap: mint_shares and burn_shares sign on the
VAULT subaccount, not the curator's own, so they must be called on a Subaccount
instantiated for the vault. Calling them through `client.vaults` while the
active subaccount is your funding account signs a valid action against the
wrong account and the exchange rejects it.

Vault-keyed reads default `vault_subaccount_id` to self.id, so they read
naturally from a vault's own Subaccount and still work for browsing anyone
else's. Wallet-keyed reads take the wallet from the auth context.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from derive_client._web3.action_signing import (
    SignedAction,
    VaultBurnSharesModuleData,
    VaultCancelModuleData,
    VaultCreateModuleData,
    VaultDepositModuleData,
    VaultMintSharesModuleData,
    VaultWithdrawModuleData,
)
from derive_client.data_types.generated_models import (
    BurnSharesRequest,
    CancelVaultRequestRequest,
    CreateVaultRequest,
    ForceBurnRequest,
    GetCuratedVaultsRequest,
    GetLiveBurnRequestsRequest,
    GetLiveMintRequestsRequest,
    GetLiveVaultRequestsRequest,
    GetShareholderVaultsRequest,
    GetVaultActionHistoryRequest,
    GetVaultPerformanceHistoryRequest,
    GetVaultRequest,
    GetVaultRequestHistoryRequest,
    GetVaultSharesRequest,
    GetVaultsRequest,
    MintSharesRequest,
    MultipleVaultRequestsResponse,
    OffchainAckResponse,
    PaginatedVaultActionHistory,
    PaginatedVaultRequestHistory,
    PerformanceResolution,
    RejectDepositRequestRequest,
    RequestVaultDepositRequest,
    RequestVaultWithdrawRequest,
    UpdateVaultInfoRequest,
    Vault,
    VaultCancelResponse,
    VaultCreateResponse,
    VaultForceBurnResponse,
    VaultIdsResponse,
    VaultPerformanceHistoryResult,
    VaultRequestAckResponse,
    VaultRequestId,
    VaultSettleResponse,
    VaultSharesResponse,
    VaultsResponse,
)

if TYPE_CHECKING:
    from .subaccount import Subaccount

#: Vault signatures are capped at 30 days out and have no minimum. Queued
#: intents are settled at the curator's discretion, within a 14-day SLA, so the
#: client-wide 1-hour default would routinely let a deposit reach `expired`
#: while it sits in the queue. Curator settle approvals execute immediately and
#: keep the client default.
INTENT_SIGNATURE_TTL_SEC = 7 * 24 * 60 * 60


class VaultOperations:
    """High-level vault operations."""

    def __init__(self, subaccount: Subaccount):
        """
        Initialize vault operations.

        Args:
            subaccount: Subaccount instance providing access to auth, config, and APIs
        """
        self._subaccount = subaccount

    # ------------------------------------------------------------------
    # Discovery: public, unauthenticated
    # ------------------------------------------------------------------

    def get(self, *, vault_subaccount_id: Optional[int] = None) -> Vault:
        """
        Get one vault's full record: on-chain state, immutable config, live pricing.

        Defaults to this subaccount, which is what you want when it is the vault.

        nav_usd and simulated_share_price_usd are unset when the vault cannot be
        priced right now, so never assume they are set; simulated_share_price_usd
        is the quote anchor for the settle loop and nav_usd is negative if the
        vault is insolvent.
        """

        params = GetVaultRequest(subaccount_id=_resolve_vault_id(self._subaccount, vault_subaccount_id))
        result = self._subaccount._public_api.rpc.get_vault(params)
        return result

    def list_all(
        self,
        *,
        page: int = 1,
        page_size: int = 100,
    ) -> VaultsResponse:
        """Get every vault on the exchange, paginated. This is how shareholders
        discover a vault."""

        params = GetVaultsRequest(page=page, page_size=page_size)
        result = self._subaccount._public_api.rpc.get_vaults(params)
        return result

    def action_history(
        self,
        *,
        vault_subaccount_id: Optional[int] = None,
        event_type: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> PaginatedVaultActionHistory:
        """
        Get a vault's settled deposit, withdrawal, fee-accrual and cancel events,
        with the fee-share split across management, performance, curator and
        protocol. Vault-level: per-holder detail is omitted.
        """

        params = GetVaultActionHistoryRequest(
            subaccount_id=_resolve_vault_id(self._subaccount, vault_subaccount_id),
            event_type=event_type,
            page=page,
            page_size=page_size,
        )
        result = self._subaccount._public_api.rpc.get_vault_action_history(params)
        return result

    def performance_history(
        self,
        *,
        resolution: PerformanceResolution,
        vault_subaccount_id: Optional[int] = None,
        from_timestamp: Optional[int] = None,
        to_timestamp: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> VaultPerformanceHistoryResult:
        """
        Get a vault's NAV, share price, share counts and high-water mark, sampled
        hourly and downsampled to the requested resolution. Bounds are unix
        seconds; results are newest first.
        """

        params = GetVaultPerformanceHistoryRequest(
            subaccount_id=_resolve_vault_id(self._subaccount, vault_subaccount_id),
            resolution=resolution,
            from_=from_timestamp,
            to=to_timestamp,
            limit=limit,
        )
        result = self._subaccount._public_api.rpc.get_vault_performance_history(params)
        return result

    # ------------------------------------------------------------------
    # Wallet-scoped reads
    # ------------------------------------------------------------------

    def list_curated(self) -> VaultIdsResponse:
        """Get the subaccount ids of the vaults this wallet curates.

        create() does not return the new vault's id, so this is also how you
        resolve one: snapshot before, then diff after the operation settles.
        """

        params = GetCuratedVaultsRequest(wallet=self._subaccount._auth.wallet)
        result = self._subaccount._private_api.rpc.get_curated_vaults(params)
        return result

    def list_shareholdings(self) -> VaultIdsResponse:
        """Get the subaccount ids of the vaults this wallet holds shares in."""

        params = GetShareholderVaultsRequest(wallet=self._subaccount._auth.wallet)
        result = self._subaccount._private_api.rpc.get_shareholder_vaults(params)
        return result

    def shares(self) -> VaultSharesResponse:
        """Get this wallet's share balance for every vault it holds shares in,
        each paired with the full vault row.

        Balances only change once the curator settles, so a just-queued deposit
        does not show up here.
        """

        params = GetVaultSharesRequest(wallet=self._subaccount._auth.wallet)
        result = self._subaccount._private_api.rpc.get_vault_shares(params)
        return result

    def list_live_requests(self) -> MultipleVaultRequestsResponse:
        """Get this wallet's queued deposit and withdraw intents across every
        vault, read live from the queues. Not paginated: the live queue is
        bounded. Terminal history is served by request_history()."""

        params = GetLiveVaultRequestsRequest(wallet=self._subaccount._auth.wallet)
        result = self._subaccount._private_api.rpc.get_live_vault_requests(params)
        return result

    def request_history(
        self,
        *,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> PaginatedVaultRequestHistory:
        """
        Get this wallet's full vault action history across every status, one row
        per action at its latest state.

        This is the only place a queued intent's outcome is observable: the
        request endpoints return an id, not an op_uuid, so there is nothing for
        wait_for_settlement to poll until a curator settles the request.
        """

        params = GetVaultRequestHistoryRequest(wallet=self._subaccount._auth.wallet, page=page, page_size=page_size)
        result = self._subaccount._private_api.rpc.get_vault_request_history(params)
        return result

    # ------------------------------------------------------------------
    # Shareholder: signed intents
    # ------------------------------------------------------------------

    def request_deposit(
        self,
        *,
        vault_subaccount_id: int,
        deposit_spot_asset: str,
        amount: Decimal,
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
    ) -> VaultRequestAckResponse:
        """
        Queue a deposit into a vault, signed on this subaccount as the source of
        the funds.

        Not a swap. The intent sits in the vault's FIFO queue until the curator
        mints shares at a quoted price bound to keccak of these exact signed
        bytes, and the funds are held on this subaccount until then, or until
        cancel_all_requests(). Share balances do not move until settlement.

        deposit_spot_asset must equal the vault's configured deposit asset; read
        it off get().protocol.config rather than hardcoding an address.

        Signature expiry defaults to 7 days rather than the client-wide 1 hour:
        an intent whose signature lapses before the curator settles it expires
        in the queue instead of filling.
        """

        module_data = VaultDepositModuleData(
            vault_subaccount_id=vault_subaccount_id,
            deposit_spot_asset=deposit_spot_asset,
            amount=amount,
        )
        signed_action = _sign_intent(
            self._subaccount,
            module_data=module_data,
            nonce=nonce,
            signature_expiry_sec=signature_expiry_sec,
        )

        # Both the wire decimal and the signed e18 word come from the module
        # data, so they cannot describe different amounts.
        payload = module_data.to_json()
        params = RequestVaultDepositRequest(
            subaccount_id=self._subaccount.id,
            vault_subaccount_id=vault_subaccount_id,
            deposit_spot_asset=payload["deposit_spot_asset"],
            amount=Decimal(payload["amount"]),
            nonce=signed_action.nonce,
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
        )
        result = self._subaccount._private_api.rpc.request_vault_deposit(params)
        return result

    def request_withdraw(
        self,
        *,
        vault_subaccount_id: int,
        shares_to_burn: Decimal,
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
    ) -> VaultRequestAckResponse:
        """
        Queue a share redemption, signed on this subaccount as the destination
        for the proceeds.

        Rejected until the vault's cooldown_sec has elapsed since this holder's
        last deposit (vault_cooldown_active, 18011). A curator redeeming their
        own stake is additionally floored by the curator stake minimum while
        other holders remain (vault_curator_stake_below_min, 18013), which is
        why the curator's full exit comes last in a winddown.

        Redemptions pay out in the vault's deposit asset, so a fully deployed
        vault cannot settle a large burn until its positions are unwound.
        """

        module_data = VaultWithdrawModuleData(
            vault_subaccount_id=vault_subaccount_id,
            shares_to_burn=shares_to_burn,
        )
        signed_action = _sign_intent(
            self._subaccount,
            module_data=module_data,
            nonce=nonce,
            signature_expiry_sec=signature_expiry_sec,
        )

        payload = module_data.to_json()
        params = RequestVaultWithdrawRequest(
            subaccount_id=self._subaccount.id,
            vault_subaccount_id=vault_subaccount_id,
            shares_to_burn=Decimal(payload["shares_to_burn"]),
            nonce=signed_action.nonce,
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
        )
        result = self._subaccount._private_api.rpc.request_vault_withdraw(params)
        return result

    def cancel_all_requests(
        self,
        *,
        vault_subaccount_id: int,
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
    ) -> VaultCancelResponse:
        """
        Cancel ALL of this wallet's pending intents for one vault, deposits and
        withdrawals alike. There is no cancel-one.

        The action bumps the per-(vault, holder) nonce to this action's nonce,
        so any intent already signed but not yet submitted, carrying a lower
        nonce, is invalidated along with the queued ones.

        May be signed on any subaccount the caller owns; this one is used.
        """

        module_data = VaultCancelModuleData(vault_subaccount_id=vault_subaccount_id)
        signed_action = _sign_intent(
            self._subaccount,
            module_data=module_data,
            nonce=nonce,
            signature_expiry_sec=signature_expiry_sec,
        )

        params = CancelVaultRequestRequest(
            subaccount_id=self._subaccount.id,
            vault_subaccount_id=vault_subaccount_id,
            nonce=signed_action.nonce,
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
        )
        result = self._subaccount._private_api.rpc.cancel_all_vault_requests(params)
        return result

    # ------------------------------------------------------------------
    # Curator: creation
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        manager_id: int,
        deposit_spot_asset: str,
        initial_deposit: Decimal,
        initial_share_price_usd: Decimal,
        management_fee_bps: int,
        performance_fee_bps: int,
        max_slippage_bps: int,
        cooldown_sec: int,
        max_fee_usd: Decimal,
        benchmark_asset: Optional[str] = None,
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
    ) -> VaultCreateResponse:
        """
        Create a vault seeded from this subaccount, which becomes its curator.

        There is no delete: a vault only ever winds down, and closes terminally
        when a burn takes total_shares to zero. Fee rates, max slippage, cooldown
        and the deposit asset are immutable afterwards, and the config is
        bounds-checked against a deployment-set global config (management fee
        <= 300bps, performance fee <= 5000bps, slippage <= 300bps, cooldown in
        [60, 604800], initial deposit >= $10,000, plus a one-time creation fee
        that max_fee_usd must cover).

        benchmark_asset denominates the high-water mark, so performance fees
        charge only on outperformance versus that asset. Omit it for the
        feed-less USD default: its PRESENCE, not its value, drives the signed
        has_benchmark flag, so passing the zero address is a different request.

        The new vault's subaccount id is not returned. Resolve it by diffing
        list_curated() once the operation settles.
        """

        module_data = VaultCreateModuleData(
            manager_id=manager_id,
            deposit_spot_asset=deposit_spot_asset,
            initial_deposit=initial_deposit,
            management_fee_bps=management_fee_bps,
            performance_fee_bps=performance_fee_bps,
            max_slippage_bps=max_slippage_bps,
            cooldown_sec=cooldown_sec,
            max_fee_usd=max_fee_usd,
            initial_share_price_usd=initial_share_price_usd,
            benchmark_asset=benchmark_asset,
        )
        signed_action = self._subaccount.sign_action(
            nonce=nonce,
            module_address=self._subaccount._config.contracts.VAULT_MODULE,
            module_data=module_data,
            signature_expiry_sec=signature_expiry_sec,
        )
        payload = module_data.to_json()

        params = CreateVaultRequest(
            subaccount_id=self._subaccount.id,
            manager_id=manager_id,
            deposit_spot_asset=payload["deposit_spot_asset"],
            initial_deposit=Decimal(payload["initial_deposit"]),
            initial_share_price_usd=Decimal(payload["initial_share_price_usd"]),
            management_fee_bps=management_fee_bps,
            performance_fee_bps=performance_fee_bps,
            max_slippage_bps=max_slippage_bps,
            cooldown_sec=cooldown_sec,
            max_fee_usd=Decimal(payload["max_fee_usd"]),
            benchmark_asset=payload["benchmark_asset"],
            nonce=signed_action.nonce,
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
        )
        result = self._subaccount._private_api.rpc.create_vault(params)
        return result

    # ------------------------------------------------------------------
    # Curator: the settle loop. Called on the VAULT's subaccount.
    # ------------------------------------------------------------------

    def list_live_mint_requests(
        self,
        *,
        limit: int = 100,
        vault_subaccount_id: Optional[int] = None,
    ) -> MultipleVaultRequestsResponse:
        """Get a FIFO page of the vault's pending deposit intents, plus the
        queue's total length. There is no WebSocket channel for these: poll,
        then settle. Each row carries the composite id and the user_action_hash
        that mint_shares() must be bound to."""

        params = GetLiveMintRequestsRequest(
            subaccount_id=_resolve_vault_id(self._subaccount, vault_subaccount_id), limit=limit
        )
        result = self._subaccount._private_api.rpc.get_live_mint_requests(params)
        return result

    def list_live_burn_requests(
        self,
        *,
        limit: int = 100,
        vault_subaccount_id: Optional[int] = None,
    ) -> MultipleVaultRequestsResponse:
        """Get a FIFO page of the vault's pending withdraw intents, plus the
        queue's total length."""

        params = GetLiveBurnRequestsRequest(
            subaccount_id=_resolve_vault_id(self._subaccount, vault_subaccount_id), limit=limit
        )
        result = self._subaccount._private_api.rpc.get_live_burn_requests(params)
        return result

    def mint_shares(
        self,
        *,
        request_id: VaultRequestId,
        share_price: Decimal,
        deposit_hash: str,
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
    ) -> VaultSettleResponse:
        """
        Settle one queued deposit, minting shares at the quoted price.

        Signed on THIS subaccount, which must be the vault. Call it on a
        Subaccount instantiated for the vault, not on your funding account.

        deposit_hash must be the user_action_hash from the queue row being
        settled, never a locally recomputed value: the hash is what binds the
        price to one exact request, and one that disagrees still produces a
        valid signature, one that settles nothing.

        Quote at or near get().simulated_share_price_usd, which is the live
        price a depositor faces with fees settled. The protocol rejects a quote
        outside the vault's immutable max_slippage_bps of its own mark-to-market
        price, in either direction.
        """

        module_data = VaultMintSharesModuleData(share_price=share_price, user_action_hash=deposit_hash)
        signed_action = _sign_settle(
            self._subaccount,
            module_data=module_data,
            nonce=nonce,
            signature_expiry_sec=signature_expiry_sec,
        )

        params = MintSharesRequest(
            subaccount_id=self._subaccount.id,
            request_id=request_id,
            share_price=Decimal(module_data.to_json()["share_price"]),
            deposit_hash=deposit_hash,
            nonce=signed_action.nonce,
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
        )
        result = self._subaccount._private_api.rpc.mint_vault_shares(params)
        return result

    def burn_shares(
        self,
        *,
        request_id: VaultRequestId,
        share_price: Decimal,
        withdraw_hash: str,
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
    ) -> VaultSettleResponse:
        """
        Settle one queued withdrawal, burning shares at the quoted price.

        Signed on THIS subaccount, which must be the vault. The mint and burn
        payloads are byte-identical apart from one discriminator word, so the
        two are only distinguishable by which method you call.

        Check the vault holds enough of the deposit asset to pay the redemption
        before settling; the funds move out at settle time. Accrued fees settle
        inside the burn. The burn that takes total_shares to zero closes the
        vault, terminally.
        """

        module_data = VaultBurnSharesModuleData(share_price=share_price, user_action_hash=withdraw_hash)
        signed_action = _sign_settle(
            self._subaccount,
            module_data=module_data,
            nonce=nonce,
            signature_expiry_sec=signature_expiry_sec,
        )

        params = BurnSharesRequest(
            subaccount_id=self._subaccount.id,
            request_id=request_id,
            share_price=Decimal(module_data.to_json()["share_price"]),
            withdraw_hash=withdraw_hash,
            nonce=signed_action.nonce,
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
        )
        result = self._subaccount._private_api.rpc.burn_vault_shares(params)
        return result

    # ------------------------------------------------------------------
    # Curator: unsigned, ownership-checked
    # ------------------------------------------------------------------

    def update_info(
        self,
        *,
        vault_subaccount_id: Optional[int] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        mtm_cap: Optional[Decimal] = None,
        whitelist_only: Optional[bool] = None,
    ) -> OffchainAckResponse:
        """
        Patch a vault's off-chain metadata. The economics stay immutable.

        Only the fields supplied are changed. Unsigned: an ownership check gates
        it to the vault's curator. mtm_cap is an advisory NAV soft-cap in USD, a
        signal to shareholders rather than an enforced limit.
        """

        params = UpdateVaultInfoRequest(
            subaccount_id=_resolve_vault_id(self._subaccount, vault_subaccount_id),
            name=name,
            description=description,
            mtm_cap=mtm_cap,
            whitelist_only=whitelist_only,
        )
        result = self._subaccount._private_api.rpc.update_vault_info(params)
        return result

    def reject_deposit_request(
        self,
        *,
        request_id: VaultRequestId,
        reason: Optional[str] = None,
    ) -> VaultRequestAckResponse:
        """
        Pop a queued deposit off the vault's queue and release the holder's funds
        with no on-chain settlement.

        Unsigned; the reason is optional and capped at 20 characters. Use it to
        stop taking deposits during a winddown, alongside whitelist_only.
        """

        params = RejectDepositRequestRequest(request_id=request_id, reason=reason)
        result = self._subaccount._private_api.rpc.reject_deposit_request(params)
        return result

    def force_burn(
        self,
        *,
        holder: str,
        vault_subaccount_id: Optional[int] = None,
    ) -> VaultForceBurnResponse:
        """
        Redeem a holder's ENTIRE share balance at the current mark-to-market
        price, with no request from them and no price quote from you.

        Unsigned; an ownership check gates it to the vault's curator. Its use is
        ejecting holders who never submit their own withdrawal during a
        winddown.
        """

        params = ForceBurnRequest(subaccount_id=_resolve_vault_id(self._subaccount, vault_subaccount_id), holder=holder)
        result = self._subaccount._private_api.rpc.force_burn(params)
        return result


# ---------------------------------------------------------------------------
# Helpers
#
# Module-level functions, not methods. scripts/generate-rest-async-http.py
# awaits every `self.<method>(...)` call in a converted module and makes the
# method async to match; a plain function call is left alone, which is what
# these want, since none of them touches the API. The same reasoning rules out
# a `_wallet` property here.
# ---------------------------------------------------------------------------


def _resolve_vault_id(subaccount: Subaccount, vault_subaccount_id: Optional[int]) -> int:
    """Vault-keyed reads default to this subaccount, which is correct when it is
    the vault and overridable when browsing someone else's."""

    return subaccount.id if vault_subaccount_id is None else vault_subaccount_id


def _sign_vault_action(
    subaccount: Subaccount,
    *,
    module_data,
    nonce: Optional[int],
    signature_expiry_sec: Optional[int],
) -> SignedAction:
    """Sign against VAULT_MODULE on this subaccount.

    Vault nonces must strictly increase per subaccount, unlike order nonces, and
    are accepted only from 60 days before to 1 hour after the server clock. A
    caller-supplied nonce that does not increase is rejected server-side.
    """

    return subaccount.sign_action(
        nonce=nonce,
        module_address=subaccount._config.contracts.VAULT_MODULE,
        module_data=module_data,
        signature_expiry_sec=signature_expiry_sec,
    )


def _sign_intent(
    subaccount: Subaccount,
    *,
    module_data,
    nonce: Optional[int],
    signature_expiry_sec: Optional[int],
) -> SignedAction:
    """Sign a shareholder intent, defaulting the expiry to INTENT_SIGNATURE_TTL_SEC."""

    if signature_expiry_sec is None:
        signature_expiry_sec = int(time.time()) + INTENT_SIGNATURE_TTL_SEC
    return _sign_vault_action(
        subaccount,
        module_data=module_data,
        nonce=nonce,
        signature_expiry_sec=signature_expiry_sec,
    )


def _sign_settle(
    subaccount: Subaccount,
    *,
    module_data,
    nonce: Optional[int],
    signature_expiry_sec: Optional[int],
) -> SignedAction:
    """Sign a curator settle approval. Executes immediately, so it keeps the
    client-wide expiry default rather than the intent TTL."""

    return _sign_vault_action(
        subaccount,
        module_data=module_data,
        nonce=nonce,
        signature_expiry_sec=signature_expiry_sec,
    )
