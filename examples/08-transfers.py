"""
08 - Spot transfers: between your own subaccounts, and out to another owner.

Two flows, both EIP-712 signed actions, both acknowledged immediately and
settled asynchronously:

    transfer_spot           between two subaccounts of the same owner. Free.
    transfer_spot_external  to a subaccount belonging to a DIFFERENT owner.
                            The recipient must be whitelisted first, and a
                            fee is always charged.

The external transfer here pays out to your session key's own EOA. That
address is distinct from the owner wallet but you already hold the key for
it, which makes it a usable stand-in for someone else's wallet without
needing a second party. If your session key IS the owner wallet, there is no
second address to send to and this example stops after the internal transfer.

The FALLBACK risk universe holds collateral that could not be applied to its
intended target. It trades nothing, so it is a valid transfer SOURCE and
never a valid target:
https://v3.docs.derive.xyz/trading/managers-and-risk-universes

max_fee_usd on the external transfer is a cap signed into the action, not a
target. The exchange charges its own fee and the request fails rather than
exceed the cap.

Prerequisites: two non-fallback subaccounts, one holding enough USDC, and a
subaccount belonging to the session key EOA (see RECIPIENT_SUBACCOUNT_ID).
See 01-deposit.py. Copy .env.template to .env first.

Run:
    python examples/08-transfers.py
"""

import os
from decimal import Decimal

from derive_py import HTTPClient, wait_for_settlement
from derive_py.data_types import RiskUniverseID
from derive_py.exceptions import SettlementFailed, SettlementTimeout

ASSET = "USDC"

INTERNAL_AMOUNT = Decimal("1")
EXTERNAL_AMOUNT = Decimal("5")  # must clear the risk universe's min_deposit_usd
EXTERNAL_MAX_FEE_USD = Decimal("5")

# Pre-created on Sepolia for this .env.template's session key wallet. An
# owner-authenticated client cannot enumerate another wallet's subaccounts, so
# this cannot be discovered. Running against a different wallet needs its own
# id here, created via the new_subaccount_manager path shown below.
RECIPIENT_SUBACCOUNT_ID = 75736

# Realistic. Off-chain balances often move before L1 confirms, so a timeout
# here is not a failure. The example test suite shortens this.
SETTLEMENT_TIMEOUT_SEC = int(os.getenv("DERIVE_EXAMPLE_TIMEOUT_SEC", "30"))

client = HTTPClient.from_env()
log = client.logger


def balance(subaccount) -> Decimal:
    collateral = next((c for c in subaccount.state.collaterals if c.asset_name == ASSET), None)
    return Decimal(collateral.amount) if collateral else Decimal("0")


def settle(op_uuid: str, what: str) -> bool:
    """Wait for an acknowledged action to settle. False means still in flight."""

    log.info(f"{what} acked (op {op_uuid}), waiting for settlement")
    try:
        log.info(f"  settled: {wait_for_settlement(client, op_uuid=op_uuid, timeout=SETTLEMENT_TIMEOUT_SEC).status}")
        return True
    except SettlementFailed as e:
        raise SystemExit(f"{what} failed: {e}") from e
    except SettlementTimeout as e:
        # Not a failure. Off-chain balances may already reflect the move
        # before L1 confirms; poll again later with the same op_uuid.
        log.warning(f"  still pending: {e}")
        return False


# -- 1. Internal transfer: subaccount to subaccount, one owner --------------

subaccounts = sorted(client.fetch_subaccounts(), key=balance, reverse=True)
tradable = [s for s in subaccounts if s.risk_universe_id is not RiskUniverseID.FALLBACK]
stranded = [s for s in subaccounts if s.risk_universe_id is RiskUniverseID.FALLBACK]

if not tradable:
    raise SystemExit("Need at least one non-fallback subaccount to receive a transfer.")

# Prefer a fallback subaccount as the source: that recovers collateral
# stranded there. Otherwise the richest tradable one.
if stranded and balance(stranded[0]) >= INTERNAL_AMOUNT:
    source = stranded[0]
    log.info(f"recovering stranded collateral from fallback subaccount #{source.id}")
elif balance(subaccounts[0]) >= INTERNAL_AMOUNT:
    source = subaccounts[0]
else:
    raise SystemExit(f"No subaccount holds {INTERNAL_AMOUNT} {ASSET}. Run 01-deposit.py first.")

# Poorest tradable subaccount as the target, which a fallback never may be.
target = min((s for s in tradable if s.id != source.id), key=balance, default=None)
if target is None:
    raise SystemExit("Need a second non-fallback subaccount to receive the transfer.")

log.info(
    f"before:\n"
    f"  source #{source.id}: {balance(source):.4f} {ASSET}\n"
    f"  target #{target.id}: {balance(target):.4f} {ASSET}"
)

internal = source.collateral.transfer_spot(
    amount=INTERNAL_AMOUNT,
    asset_name=ASSET,
    to_subaccount_id=target.id,
)
settle(internal.op_uuid, "transfer_spot")

# .state is cached from construction, so refresh before reading balances.
log.info(
    f"after:\n"
    f"  source #{source.id}: {balance(source.refresh()):.4f} {ASSET}\n"
    f"  target #{target.id}: {balance(target.refresh()):.4f} {ASSET}"
)


# -- 2. External transfer: to a wallet you do not own -----------------------

recipient = client._auth.signer  # session key EOA
if recipient == client._auth.wallet:
    # Environment fact, not a failure: everything above ran.
    log.info("the session key is the owner wallet, so there is no second address to transfer to")
    raise SystemExit(0)

source = subaccounts[0].refresh()
if balance(source) < EXTERNAL_AMOUNT + EXTERNAL_MAX_FEE_USD:
    raise SystemExit(f"Subaccount #{source.id} cannot cover {EXTERNAL_AMOUNT} {ASSET} plus the fee cap.")

# External transfers only pay out to pre-approved wallets. Whitelisting is
# itself a signed action, so skip it when the recipient is already listed.
if recipient in client.account.get().whitelisted_recipients:
    log.info(f"{recipient} is already whitelisted")
else:
    whitelist = client.account.update_whitelisted_recipients(add=[recipient], remove=[])
    if not settle(whitelist.op_uuid, "update_whitelisted_recipients"):
        # The exchange accepts the transfer against off-chain state, which
        # already reflects the whitelist, so this very likely goes through.
        # Acceptable on testnet. Do not copy into anything moving real funds.
        log.warning("whitelisting has not settled on L1; proceeding against off-chain state")

# Targets an existing subaccount rather than minting one per run. To create one
# for the recipient instead, leave to_subaccount_id at its default and pass the
# target risk manager id, which charges a subaccount-creation fee:
#
#   source.collateral.transfer_spot_external(
#       amount=EXTERNAL_AMOUNT,
#       asset_name=ASSET,
#       recipient_address=recipient,
#       max_fee_usd=EXTERNAL_MAX_FEE_USD,
#       new_subaccount_manager=1,  # PRIME's standard margin manager
#   )
external = source.collateral.transfer_spot_external(
    amount=EXTERNAL_AMOUNT,
    asset_name=ASSET,
    recipient_address=recipient,
    to_subaccount_id=RECIPIENT_SUBACCOUNT_ID,
    max_fee_usd=EXTERNAL_MAX_FEE_USD,
)
settle(external.op_uuid, "transfer_spot_external")

# The recipient's balance is not readable from here: this client is
# authenticated as the owner wallet, not as the session key. A second
# HTTPClient authenticated as the session key could confirm it.
log.info(f"source #{source.id} now holds {balance(source.refresh()):.4f} {ASSET}")
