"""
09 - Withdraw collateral to L1.

Two things make withdrawals unlike every other signed action:

    The amount is signed in the ERC-20's NATIVE decimals (USDC has 6), not
    the protocol's usual e18 fixed point. It is resolved from the
    subaccount's own risk universe, so you never pass it.
    The payout goes to the recipient signed into the action, which defaults
    to the subaccount's owner wallet.

Who may send it, and to whom: the signer needs the withdraw protocol scope.
Scopes form a tree and admin sits above all of them, so an admin session key
holds withdraw implicitly. Owner and admin signers may pay out to any
address; any other signer is limited to the owner's whitelisted_recipients,
printed below. That list is changed with update_whitelisted_recipients(),
itself an owner-or-admin action that settles asynchronously, which is why it
is not part of this example. Set RECIPIENT to an address only if your key
clears one of those two bars.

public/withdraw_debug returns the typed data and hashes the exchange would
compute for these same parameters, which is how to check your signing
without spending anything.

Withdrawal is asynchronous. Submitting returns an op_uuid immediately and
settlement (Batching, Executing, Proving, Settling, Settled) follows later,
which is what this polls for. max_fee_usd is a cap signed into the action:
the exchange charges its own fee and the request fails rather than exceed it.
FORCE_BATCH requests immediate batching and proving, at the expense of a
higher MAX_FEE_USD.

Prerequisites: a subaccount holding USDC. Run 01-deposit.py first.
Copy .env.template to .env first.

Run:
    python examples/09-withdraw.py
"""

import os

from derive_py import HTTPClient, wait_for_settlement
from derive_py.data_types import D
from derive_py.exceptions import SettlementFailed, SettlementTimeout

ASSET = "USDC"
AMOUNT = D("5")  # Must clear the collateral's min_deposit_usd, and the MAX_FEE_USD
MAX_FEE_USD = D("1")  # 10 is required when FORCE_BATCH is True
FORCE_BATCH = False  # If True immediate batching/proving: faster, higher fee
RECIPIENT = None  # None pays out to the owner wallet
# L1 settlement may take several minutes and total tx time depends on FORCE_BATCH
SETTLEMENT_TIMEOUT_SEC = int(os.getenv("DERIVE_EXAMPLE_TIMEOUT_SEC", "300"))

client = HTTPClient.from_env()
log = client.logger

subaccount = client.active_subaccount
account = client.account

# Portfolio figures come back as human-readable decimal strings.
collateral = next((c for c in subaccount.state.collaterals if c.asset_name == ASSET), None)
balance = D(collateral.amount) if collateral else D("0")

if balance < AMOUNT:
    raise SystemExit(f"Subaccount {subaccount.id} holds {balance} {ASSET}. Run 01-deposit.py, or lower AMOUNT.")

log.info(
    f"Subaccount {subaccount.id} holds {balance} {ASSET}, withdrawing {AMOUNT}.\n"
    f"  signed payout recipient: {RECIPIENT or account.address}\n"
    f"  owner wallet: {account.address}\n"
    f"  whitelisted recipients: {account.state.whitelisted_recipients}"
)

response = subaccount.withdraw(
    asset_name=ASSET,
    amount=AMOUNT,
    recipient=RECIPIENT,
    max_fee_usd=MAX_FEE_USD,
    force_batch=FORCE_BATCH,
)
log.info(f"withdrawal accepted (op {response.op_uuid}), waiting for settlement")

try:
    log.info(f"settled: {wait_for_settlement(client, op_uuid=response.op_uuid, timeout=SETTLEMENT_TIMEOUT_SEC).status}")
except SettlementFailed as e:
    raise SystemExit(f"Withdrawal failed: {e}") from e
except SettlementTimeout as e:
    # Not a failure: still in flight. Poll again later with the same op_uuid.
    log.warning(f"still pending: {e}")
