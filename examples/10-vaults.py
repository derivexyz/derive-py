"""
10 - Vaults: browse, queue a deposit, cancel it.

A vault is a subaccount traded by a curator on behalf of shareholders. This
stays on the shareholder side. Creating one is irreversible, costs a
five-figure seed deposit plus a fee, and a vault only ever winds down.

    Deposits and withdrawals are NOT swaps. You sign an intent, it queues,
    and the curator later settles it by minting or burning shares at a price
    they quote. Your funds sit on hold on your own subaccount until then.
    The curator cannot fill at an arbitrary price: the protocol bounds the
    quote to within the vault's immutable max_slippage_bps of its own
    mark-to-market share price.
    Intent signatures default to 7 days, not the client's usual hour. An
    intent whose signature lapses before the curator reaches it expires in
    the queue instead of filling.
    Every vault call's subaccount_id is the subaccount you are acting AS.
    Here that is your funding subaccount. A curator settling the queue acts
    as the vault subaccount instead, calling list_live_mint_requests() and
    then mint_shares(), which binds the quoted price to the exact signed
    bytes of one request through deposit_hash.

Browsing is public and always runs. The deposit is opt-in: set VAULT_ID to
one of the ids the browse step prints. It puts real funds on hold, so it
should not happen because a vault happened to be first in a list.

Prerequisites for the deposit: a funded subaccount, and a session key
holding vault:user_deposit and vault:user_cancel. See 01-deposit.py.
Copy .env.template to .env first.

Run:
    python examples/10-vaults.py
"""

import asyncio
from decimal import Decimal

from derive_py import WebSocketClient

VAULT_ID = 0  # a vault subaccount id from the browse step; 0 browses only
DEPOSIT_AMOUNT = Decimal("10")  # in the vault's own deposit asset, usually USDC
VAULTS_TO_SHOW = 5


async def main() -> None:
    client = WebSocketClient.from_env()
    log = client.logger
    await client.connect()

    queued = False
    try:
        # Browsing needs no auth: this is how shareholders find a vault.
        listed = await client.vaults.list_all(page=1, page_size=VAULTS_TO_SHOW)
        if not listed.vaults:
            log.warning("No vaults on this environment yet.")
            return

        rows = []
        for vault in listed.vaults:
            # nav_usd and simulated_share_price_usd are unset when the vault
            # cannot be priced right now. Never assume they are set.
            closed = " [closed]" if vault.protocol.closed else ""
            restricted = " [whitelist only]" if vault.whitelist_only else ""
            rows.append(
                f"  #{vault.protocol.subaccount_id} {vault.name}{closed}{restricted}:"
                f" NAV ${vault.nav_usd or '?'}, share price ${vault.simulated_share_price_usd or '?'}"
            )
        log.info(f"{len(listed.vaults)} vault(s):\n" + "\n".join(rows))

        if not VAULT_ID:
            log.info("Set VAULT_ID to one of the ids above to queue a deposit into it.")
            return

        # A vault's economics are fixed at creation. The fees and the cooldown
        # are what you are agreeing to by depositing.
        vault = await client.vaults.get(vault_subaccount_id=VAULT_ID)
        config = vault.protocol.config
        if vault.whitelist_only or vault.protocol.closed:
            raise SystemExit(f"Vault #{VAULT_ID} is whitelist-only or closed, so it will not accept this deposit.")

        log.info(
            f"'{vault.name}' (#{VAULT_ID}):\n"
            f"  deposit asset:    {config.deposit_spot_asset}\n"
            f"  fees:             {config.management_fee_bps}bps mgmt / {config.performance_fee_bps}bps perf\n"
            f"  settle slippage:  up to {config.max_slippage_bps}bps from the mark share price\n"
            f"  withdraw cooldown: {config.cooldown_sec}s after your last deposit"
        )

        # The deposit asset must be the vault's own, so read it off the record
        # rather than hardcoding an address.
        ack = await client.active_subaccount.vaults.request_deposit(
            vault_subaccount_id=VAULT_ID,
            deposit_spot_asset=config.deposit_spot_asset,
            amount=DEPOSIT_AMOUNT,
        )
        queued = True
        log.info(
            f"queued {DEPOSIT_AMOUNT}, now held on subaccount {client.active_subaccount.id}\n"
            f"  request: vault {ack.request_id.vault_subaccount_id}, nonce {ack.request_id.vault_nonce}"
        )

        # The intent waits in a FIFO queue. There is no channel for it and no
        # op_uuid to poll: a queued request has no on-chain operation until the
        # curator settles it, so this listing is the only handle on it.
        live = await client.vaults.list_live_requests()
        holdings = await client.vaults.shares()
        held = "\n".join(
            f"  {e.shares} shares of '{e.vault.name}' (#{e.vault.protocol.subaccount_id})" for e in holdings.vaults
        )
        # Share balances only move on settlement, so the deposit above is absent.
        log.info(f"{live.total} unsettled request(s) for this wallet\n{held or '  no vault shares held yet'}")
    finally:
        if queued:
            # Drains ALL of this wallet's pending intents for the vault,
            # deposits and withdrawals alike. There is no cancel-one.
            cancelled = await client.active_subaccount.vaults.cancel_all_requests(vault_subaccount_id=VAULT_ID)
            log.info(f"cancelled {len(cancelled.cancelled_request_ids)} intent(s), funds released")
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
