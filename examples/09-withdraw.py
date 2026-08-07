"""
Withdraw collateral to L1.

Two things make withdrawals different from every other signed action on
Derive v3, and this example calls out both:

  1. The amount is signed in the ERC-20's NATIVE decimals (USDC = 6),
     not the protocol's usual e18 fixed-point -- resolved automatically
     from the subaccount's own risk universe, not something you pass.
  2. The exchange pays out to whichever address SIGNED the withdrawal --
     not an independently chosen recipient. This example signs with the
     client's own key, so funds land at THAT address. Never grant
     withdraw scope to a session key you don't want holding payouts.

Withdrawal is asynchronous: submitting returns an op_uuid immediately;
settlement (Batching -> Executing -> Proving -> Settling -> Settled)
happens later. This example polls for it.

Prerequisites: a subaccount already holding USDC -- run 01-deposit.py first.

Run:
    python examples/09-withdraw.py
"""

from pathlib import Path

from derive_client import HTTPClient
from derive_client._clients.utils import wait_for_settlement
from derive_client.data_types import D
from derive_client.exceptions import SettlementFailed, SettlementTimeout

TIMEOUT_SEC = 300

env_file = Path(__file__).parent.parent / ".env.template"
client = HTTPClient.from_env(env_file=env_file)

subaccount = client.active_subaccount

# All portfolio figures come back as human-readable decimal strings.
usdc = next((c for c in subaccount.state.collaterals if c.asset_name == "USDC"), None)
balance = D(usdc.amount) if usdc else D("0")

amount = D("5")  # Must clear the risk universe's collateral min_deposit_usd.

print(f"Subaccount {subaccount.id} holds {balance} USDC; withdrawing {amount}.")

if balance < amount:
    print("Insufficient USDC -- run 01-deposit.py first, or lower `amount` above.")
    raise SystemExit(0)

# WHERE THE MONEY GOES: this is the signer, always.
print(f"Payout recipient (the signer): {client._auth.wallet}")

response = subaccount.withdraw(
    asset_name="USDC",
    amount=amount,
    force_batch=False,  # False is the default, if True: go straight to L1 settlement (more expensive)
    max_fee_usd=D("1"),  # Increase this if you want to force a faster settlement
)
print(f"Withdrawal accepted: op_uuid={response.op_uuid}")

try:
    tx_result = wait_for_settlement(client, op_uuid=response.op_uuid, timeout=TIMEOUT_SEC)
    print(f"Settled: {tx_result}")
except SettlementFailed as e:
    print(f"Withdrawal failed: {e}")
    print(f"  last status: {e.tx_result.status if e.tx_result else 'unknown'}")
except SettlementTimeout as e:
    # Not a failure: the withdrawal is still in flight. Poll again later with the same op_uuid
    print(f"Still pending: {e}")
    print(f"  last status: {e.tx_result.status if e.tx_result else 'unknown'}")
