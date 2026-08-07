"""
Vaults: browse, queue a deposit, cancel it.

A vault is a subaccount traded by a *curator* on behalf of *shareholders*.
Curating is not a privileged role: any wallet can create one. This example
stays on the shareholder side, because creating a vault is irreversible, costs
a five-figure seed deposit plus a creation fee, and can never be undone -- a
vault only ever winds down.

The mental model to take away:
  - Vault deposits and withdrawals are NOT swaps. You sign an intent, it
    queues, and the curator later settles it by minting or burning shares at a
    price they quote. Until then your funds sit on hold on your own subaccount.
  - The curator cannot fill you at an arbitrary price: the protocol bounds
    their quote to within the vault's immutable max_slippage_bps of its own
    mark-to-market share price.
  - Every vault call's subaccount_id is "the subaccount you are acting as".
    Here that is your funding subaccount. A curator settling the queue acts as
    the vault subaccount instead -- see the note at the bottom.
  - Intent signatures default to 7 days here, not the client's usual hour: an
    intent whose signature lapses before the curator gets to it expires in the
    queue instead of filling.

Prerequisites: a wallet with a funded subaccount -- see 01-deposit.py -- and a
session key holding vault:user_deposit and vault:user_cancel.

Run:
    python examples/10-vaults.py
"""

import asyncio
from decimal import Decimal
from pathlib import Path

from derive_client import WebSocketClient

DEPOSIT_AMOUNT = Decimal("10")  # in the vault's deposit asset, usually USDC


async def main():
    env_file = Path(__file__).parent.parent / ".env.template"
    client = WebSocketClient.from_env(env_file=env_file)
    await client.connect()

    try:
        # Browsing needs no auth: this is how shareholders find a vault.
        listed = await client.vaults.list_all(page=1, page_size=5)
        if not listed.vaults:
            print("no vaults on this environment yet -- nothing to demo")
            return

        print(f"found {len(listed.vaults)} vault(s):")
        for vault in listed.vaults:
            # nav_usd and simulated_share_price_usd are unset when the vault
            # cannot be priced right now. Never assume they are set.
            nav = vault.nav_usd or "?"
            price = vault.simulated_share_price_usd or "?"
            print(f"  #{vault.protocol.subaccount_id} {vault.name}: NAV ${nav}, share price ${price}")

        vault = next((v for v in listed.vaults if not v.whitelist_only and not v.protocol.closed), None)
        if vault is None:
            print("\nevery listed vault is whitelist-only or closed -- stopping before the deposit")
            return

        # A vault's economics are fixed at creation. Read them before depositing:
        # the fees and the cooldown are what you are agreeing to.
        vault_id = vault.protocol.subaccount_id
        config = vault.protocol.config
        print(f"\ninspecting '{vault.name}' (#{vault_id}):")
        print(f"  deposit asset:      {config.deposit_spot_asset}")
        print(f"  fees:               {config.management_fee_bps}bps mgmt / {config.performance_fee_bps}bps perf")
        print(f"  max settle slippage: {config.max_slippage_bps}bps")
        print(f"  withdraw cooldown:   {config.cooldown_sec}s after your last deposit")

        # The deposit asset must be the vault's own, so take it off the vault
        # row rather than hardcoding an address.
        ack = await client.active_subaccount.vaults.request_deposit(
            vault_subaccount_id=vault_id,
            deposit_spot_asset=config.deposit_spot_asset,
            amount=DEPOSIT_AMOUNT,
        )
        request_id = ack.request_id
        print(f"\nqueued a {DEPOSIT_AMOUNT} deposit; funds now held on subaccount {client.active_subaccount.id}")
        print(f"  request id: vault {request_id.vault_subaccount_id}, nonce {request_id.vault_nonce}")

        # The intent waits in a FIFO queue. There is no WebSocket channel for
        # it, and no op_uuid to poll: a queued request has no on-chain operation
        # until the curator settles it, so its outcome is only visible here.
        live = await client.vaults.list_live_requests()
        print(f"  {live.total} unsettled request(s) for this wallet")

        # Share balances only move on settlement, so the deposit above will not
        # show up here yet.
        holdings = await client.vaults.shares()
        for entry in holdings.vaults:
            print(f"  holding {entry.shares} shares of '{entry.vault.name}' (#{entry.vault.protocol.subaccount_id})")
        if not holdings.vaults:
            print("  no vault shares held yet")

        # Cancel so the demo does not leave funds on hold. This drains ALL of
        # this wallet's pending intents for the vault, deposits and withdrawals
        # alike; there is no cancel-one.
        cancelled = await client.active_subaccount.vaults.cancel_all_requests(vault_subaccount_id=vault_id)
        print(f"\ncancelled {len(cancelled.cancelled_request_ids)} intent(s); funds released")

        # The curator side, for reference. It is not privileged -- any wallet
        # can create a vault via active_subaccount.vaults.create(...) -- but the
        # settle approvals sign on the VAULT subaccount, not your funding one:
        #
        #   vault = await client.fetch_subaccount(vault_id)
        #   queue = await vault.vaults.list_live_mint_requests()
        #   for request in queue.requests:
        #       priced = await vault.vaults.get()
        #       if priced.simulated_share_price_usd is None:
        #           break  # unpriceable right now; retry later
        #       await vault.vaults.mint_shares(
        #           request_id=request.id,
        #           share_price=priced.simulated_share_price_usd,
        #           deposit_hash=request.user_action_hash,  # binds the price to this exact request
        #       )
        curated = await client.vaults.list_curated()
        ids = ", ".join(str(i) for i in curated.subaccount_ids) or "none"
        print(f"vaults curated by this wallet: {ids}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
