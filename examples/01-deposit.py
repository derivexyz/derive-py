"""
Deposit: fund a Derive v3 subaccount on-chain.

There is no separate "create account" call on Derive v3 -- a deposit
either creates your first subaccount or tops up one you already have.
This example shows both on-chain deposit paths this client supports:

  New subaccount      -- client.plan_deposit_to_new_subaccount(): nothing
                          exists yet, so you choose a risk universe and
                          margin type; the deposit itself creates the
                          subaccount.
  Existing subaccount -- subaccount.plan_deposit(): the subaccount
                          already knows its own manager, so you only
                          give it an asset and an amount.

Not covered here: the Standard/Instant deposit-address flows (the
CEX-style "send from any wallet, credited asynchronously" methods) --
those go through private/register_deposit_address on the HTTP client,
a different mechanism entirely from the Direct on-chain path below.

Both flows yield the same kind of step (1 if already approved, 2 if
not): inspect the unsigned tx, submit it, wait for finality, then move
to the next step. wait_for_finality() is safe to call again if it times
out -- it doesn't resubmit, it just keeps polling the same tx hash.

Prerequisites: a Sepolia wallet with ETH (gas) and USDC (the deposit),
configured in .env.template.

Run:
    python examples/01-deposit.py
"""

from decimal import Decimal as D
from pathlib import Path

from derive_client import HTTPClient
from derive_client.data_types import MarginType, UniverseType

env_file = Path(__file__).parent.parent / ".env.template"
client = HTTPClient.from_env(env_file=env_file)


def run_steps(steps):
    """Shared driver for both flows below: inspect, submit, wait -- per step."""

    for step in steps:
        print(f"[{step.kind}] {step.description}")
        tx_hash = step.submit()
        print(f"  submitted: {tx_hash}")
        receipt = step.wait_for_finality()
        print(f"  confirmed: block {receipt.blockNumber}")


existing = client.fetch_subaccounts()

if not existing:
    print("No subaccounts yet -- depositing into a NEW one.")
    steps = client.plan_deposit_to_new_subaccount(
        universe_type=UniverseType.PRIME,
        margin_type=MarginType.SM,
        asset_name="USDC",
        amount=D("5"),
    )
else:
    subaccount = existing[0]
    print(f"Depositing into existing subaccount {subaccount.id}.")
    steps = subaccount.plan_deposit(
        asset_name="USDC",
        amount=D("5"),
    )

run_steps(steps)
