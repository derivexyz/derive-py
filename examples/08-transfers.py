"""
08 -- Spot transfers: moving USDC between subaccounts and to other wallets.

Shows the two spot-transfer flows:
  1. transfer_spot          -- between two of YOUR OWN subaccounts. Free.
  2. transfer_spot_external -- to ANOTHER owner's wallet. The recipient
                                must be whitelisted first
                                (update_whitelisted_recipients), and a fee
                                is charged.

Both are EIP-712 signed actions: transfer_spot()/transfer_spot_external()
encode the transfer, sign it locally with your key, and the exchange
verifies that signature -- it never holds your key and cannot move funds
you didn't sign for.

Prerequisites: a funded account with at least two subaccounts for step 1
(see 01-deposit.py). For step 2, set RECIPIENT to another owner's wallet,
and optionally RECIPIENT_SUBACCOUNT_ID to one of their existing
subaccounts (omitted -> the exchange creates them a new one, which costs
an extra fee).

Run:
    RECIPIENT=0x... python examples/08-transfers.py
"""

from decimal import Decimal
from pathlib import Path

from more_itertools import last, partition

from derive_client import HTTPClient
from derive_client._clients.utils import wait_for_settlement
from derive_client.data_types import RiskUniverseID
from derive_client.exceptions import WithdrawalFailed, WithdrawalTimeout


def usdc_balance(subaccount) -> Decimal:
    collateral = next((c for c in subaccount.state.collaterals if c.asset_name == "USDC"), None)
    return Decimal(collateral.amount) if collateral else Decimal("0")


def is_fallback(subaccount) -> bool:
    return subaccount.risk_universe_id is RiskUniverseID.FALLBACK


# Timeout for transaction settlement
# Funds may already be moved between subaccounts prior to this,
# but the L1 settlement may not yet be confirmed.
TIMEOUT_SEC = 300
AMOUNT_USDC = Decimal("1")

env_file = Path(__file__).parent.parent / ".env.template"
client = HTTPClient.from_env(env_file=env_file)


# -- 1. Internal transfer: subaccount -> subaccount, same owner ------------
subaccounts = client.fetch_subaccounts()

# The FALLBACK risk universe holds orphaned collateral for recovery.
# It is a source-only construct: it must never be a transfer target.
# https://v3.docs.derive.xyz/trading/managers-and-risk-universes
regular_subaccounts, fallback_subaccounts = partition(is_fallback, subaccounts)
regular_subaccounts = sorted(regular_subaccounts, key=usdc_balance, reverse=True)
fallback_subaccounts = sorted(fallback_subaccounts, key=usdc_balance, reverse=True)

if not regular_subaccounts:
    raise SystemExit("Need at least one non-fallback subaccount to act as transfer target.")

# Robinhood move: pull from richest move to poorest
# Prefer recovering stranded funds from the richest fallback subaccount.
richest_fallback = fallback_subaccounts[0] if fallback_subaccounts else None
if richest_fallback and usdc_balance(richest_fallback) >= AMOUNT_USDC:
    print(f"Recovering funds from fallback subaccount #{richest_fallback.id} as source")
    source_sub = richest_fallback
elif regular_subaccounts and usdc_balance(regular_subaccounts[0]) >= AMOUNT_USDC:
    source_sub = regular_subaccounts[0]
    print(f"Using regular subaccount #{source_sub.id} as source")
else:
    raise SystemExit(
        f"GAME OVER: No subaccount has at least {AMOUNT_USDC} USDC to transfer. "
        "Go back to level 1 (01-deposit.py) and try again."
    )

# Target: poorest remaining non-fallback subaccount.
target_sub = last((sa for sa in regular_subaccounts if sa.id != source_sub.id), None)
if not target_sub:
    raise SystemExit("Need a second non-fallback subaccount, distinct from the source, as target.")

print("USDC Balance before:")
print(f"  source subaccount #{source_sub.id}: {usdc_balance(source_sub):.4f}")
print(f"  target subaccount #{target_sub.id}: {usdc_balance(target_sub):.4f}")

# Moves between existing subaccounts are free
internal = source_sub.collateral.transfer_spot(
    amount=AMOUNT_USDC,
    asset_name="USDC",
    to_subaccount_id=target_sub.id,
)

# ACKed immediately, settled asynchronously by the exchange
print(f"transfer_spot acked (op {internal.op_uuid}); waiting for settlement...")
try:
    tx_result = wait_for_settlement(client, op_uuid=internal.op_uuid, timeout=TIMEOUT_SEC)
except WithdrawalTimeout as e:
    print(f"Timeout while waiting for L1 settlement: {e}")
    print("Balance on subaccounts may already have updated, but L1 settlement is not confirmed yet.")
except WithdrawalFailed as e:
    print(f"Transfer failed (no L1 settlement expected): {e}")
    raise SystemExit(1)


# Use this to refresh state, .state is cached from construction otherwise
source_sub.refresh()
target_sub.refresh()

print("USDC Balance after (may have changed before/without L1 settlement confirmation):")
print(f"  source subaccount #{source_sub.id}: {usdc_balance(source_sub):.4f}")
print(f"  target subaccount #{target_sub.id}: {usdc_balance(target_sub):.4f}")


# -- 2. External transfer: to a wallet you do NOT own -----------------------
#
# Sends to a subaccount belonging to your SESSION KEY's own EOA -- a
# convenient stand-in for "someone else's wallet" for this example,
# since the session key is a distinct address from the owner wallet but
# still available to sign with.
#
# Targets an EXISTING subaccount (RECIPIENT_SUBACCOUNT_ID below) rather
# than creating a new one on every run. To create a subaccount for a
# recipient instead, set new_subaccount_manager to the target risk
# manager id and leave to_subaccount_id=0 (default).
# This charges an additional subaccount-creation fee.
#
#   source_sub.collateral.transfer_spot_external(
#       amount=AMOUNT_USDC,
#       asset_name="USDC",
#       recipient_address=recipient_address,
#       max_fee_usd=MAX_FEE_USD,
#       new_subaccount_manager=1,  # e.g. PRIME's standard margin manager
#   )
#
# Not run here, so repeated runs of this example don't mint a fresh
# subaccount each time.

AMOUNT_USDC = Decimal("5")  # Must clear the risk universe's min_deposit_usd.
MAX_FEE_USD = Decimal("5")  # fee cap, not a target

# Pre-created once on Sepolia for this .env.template's session key wallet.
# If you're running against a different wallet, this id won't exist for
# you -- create one first via the new_subaccount_manager path above, note
# the resulting subaccount id, then hardcode it here.
RECIPIENT_SUBACCOUNT_ID = 75736

recipient_address = client._auth.signer  # session key EOA
owner_address = client._auth.wallet
if recipient_address == owner_address:
    print(
        "Session key address equals owner wallet address, can't use it as "
        "an external recipient (external transfers require a distinct wallet)."
    )
    raise SystemExit(1)

subaccounts = sorted(client.fetch_subaccounts(), key=usdc_balance, reverse=True)
source_sub = subaccounts[0]

if usdc_balance(source_sub) < AMOUNT_USDC + MAX_FEE_USD:
    print(f"Source subaccount #{source_sub.id} has less than {AMOUNT_USDC} USDC plus max fee {MAX_FEE_USD}.")
    raise SystemExit(1)

# External transfers only pay out to pre-approved wallets.
print(f"Whitelisting {recipient_address}")
whitelist = client.account.update_whitelisted_recipients(add=[recipient_address], remove=[])
print(f"Whitelist update acked (op {whitelist.op_uuid}); waiting for settlement...")
# One could wait for settlement here as well, which we omit for expediency.

# Unlike internal moves, external transfers ALWAYS charge a fee (1 USD
# standard, plus a subaccount-creation fee when one is created), so
# max_fee_usd is mandatory; a signed CAP on what the exchange may
# deduct, not a target: the request fails rather than overpay.
external = source_sub.collateral.transfer_spot_external(
    amount=AMOUNT_USDC,
    asset_name="USDC",
    recipient_address=recipient_address,
    max_fee_usd=MAX_FEE_USD,
    to_subaccount_id=RECIPIENT_SUBACCOUNT_ID,
)

print(f"transfer_spot_external acked (op {external.op_uuid}); waiting for settlement...")
try:
    tx_result = wait_for_settlement(client, op_uuid=external.op_uuid, timeout=TIMEOUT_SEC)
except WithdrawalTimeout as e:
    print(f"Timeout while waiting for L1 settlement: {e}")
    print("Balance on subaccounts may already have updated, but L1 settlement is not confirmed yet.")
except WithdrawalFailed as e:
    print(f"Transfer failed (no L1 settlement expected): {e}")
    raise SystemExit(1)

# Owner's client can't check the recipient subaccount's balance directly
# (it operates on the owner wallet, not the session key wallet). A
# second HTTPClient authenticated as the session key could confirm it,
# omitted here to keep the example focused.
