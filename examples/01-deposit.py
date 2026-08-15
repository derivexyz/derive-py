"""
01 - Deposit: the only way an account or subaccount comes into existence.

Derive v3 has no create_subaccount call. Depositing on-chain creates the
subaccount, so this is the first step for a new wallet and the top-up path
for an existing one. Set CREATE_NEW_SUBACCOUNT below to pick between:

    plan_deposit()                    fund an existing subaccount, which
                                      already carries its own manager_id
    plan_deposit_to_new_subaccount()  create one under a risk universe and
                                      margin type, then fund it

Either way you get one step per transaction: the ERC-20 approve, skipped
when the allowance already covers it, then the deposit. Each step arrives
prepared, fee-estimated and simulated but unsigned, so you can see what it
costs before it costs anything. Steps are built one at a time: the deposit
cannot be prepared until the approve is mined, because its simulation would
revert on the missing allowance.

Mining is not crediting. The exchange applies the deposit asynchronously,
around two minutes, and the new subaccount id is not in the receipt, so
this waits for the credit afterwards.

Direct deposits only. The Standard and Instant deposit-address routes are a
different mechanism: https://v3.docs.derive.xyz/getting-started/depositing

Prerequisites: a Sepolia wallet holding ETH for gas and USDC to deposit.
Copy .env.template to .env first.

Run:
    python examples/01-deposit.py

Nothing is submitted without confirmation at the prompt, so running this
anywhere non-interactive prepares the transactions and stops.
"""

import sys
from decimal import Decimal
from time import monotonic, sleep

import rich_click as click

from derive_py import HTTPClient
from derive_py.data_types import D, MarginType, RiskUniverseID
from derive_py.exceptions import FinalityTimeout, TxPendingTimeout

ASSET = "USDC"
AMOUNT = D("5")  # below the collateral's min_deposit_usd it is donated, not credited

CREATE_NEW_SUBACCOUNT = False
RISK_UNIVERSE = RiskUniverseID.PRIME  # creating one only: see client.markets.get_risk_universes()
MARGIN_TYPE = MarginType.SM  # creating one only

CREDIT_TIMEOUT_SEC = 300
POLL_INTERVAL_SEC = 5

client = HTTPClient.from_env()
log = client.logger  # one stream: the client logs here too


def usdc_balance(subaccount) -> Decimal:
    collateral = next((c for c in subaccount.state.collaterals if c.asset_name == ASSET), None)
    return Decimal(collateral.amount) if collateral else Decimal("0")


def submit(step) -> bool:
    """Show what the transaction costs, then submit it only if confirmed."""

    tx = step.tx_params
    worst_case_eth = Decimal(tx["gas"] * tx["maxFeePerGas"]) / Decimal(10**18)
    log.info(
        f"[{step.kind}] {step.description}\n"
        f"  gas {tx['gas']} at up to {tx['maxFeePerGas'] / 1e9:.2f} gwei, {worst_case_eth:.6f} ETH worst case"
    )

    if not sys.stdin.isatty():
        log.warning("  not a terminal, so nothing was submitted. Run this interactively to confirm.")
        return False

    if not click.confirm("  submit?", default=False):
        log.warning("  not submitted.")
        return False

    log.info(f"  submitted {step.submit()}")
    try:
        log.info(f"  final in block {step.wait_for_finality().blockNumber}")
    except (FinalityTimeout, TxPendingTimeout) as e:
        # Mined or still in the mempool, either way not lost: wait_for_finality()
        # reuses the same tx hash and never resubmits. TransactionDropped is a
        # real failure and is deliberately not caught here.
        log.warning(f"  {e} Rerun to keep waiting on the same transaction.")
        return False
    return True


if CREATE_NEW_SUBACCOUNT:
    # A wallet's first deposit creates two subaccounts: the one you asked for,
    # plus a fallback under manager 0 that catches deposits which cannot be
    # applied. Two new ids on a first run is normal.
    known_ids = set(client.account.get_subaccounts().subaccount_ids)
    log.info(f"Creating a {MARGIN_TYPE} subaccount in {RISK_UNIVERSE.name} with {AMOUNT} {ASSET}.")
    steps = client.plan_deposit_to_new_subaccount(
        risk_universe_id=RISK_UNIVERSE,
        margin_type=MARGIN_TYPE,
        asset_name=ASSET,
        amount=AMOUNT,
    )

    def credited() -> str | None:
        """The receipt does not carry the new id, so diff the list instead."""

        new_ids = set(client.account.get_subaccounts().subaccount_ids) - known_ids
        return f"new subaccount(s) {sorted(new_ids)}" if new_ids else None

else:
    # Never deposit into the FALLBACK universe: it holds orphaned collateral
    # for recovery and trades nothing.
    tradable = [s for s in client.fetch_subaccounts() if s.risk_universe_id is not RiskUniverseID.FALLBACK]
    if not tradable:
        raise SystemExit("No tradable subaccount on this wallet. Set CREATE_NEW_SUBACCOUNT = True to make one.")

    target = tradable[0]

    opening_balance = usdc_balance(target)
    log.info(f"Depositing {AMOUNT} {ASSET} into subaccount {target.id}, holding {opening_balance} {ASSET}.")
    steps = target.plan_deposit(asset_name=ASSET, amount=AMOUNT)

    def credited() -> str | None:
        balance = usdc_balance(target.refresh())
        return f"subaccount {target.id} now holds {balance} {ASSET}" if balance > opening_balance else None


for step in steps:
    if not submit(step):
        # Prepared but not submitted is the documented outcome of declining or
        # of running non-interactively, not a failure.
        log.info("Stopped before the deposit completed. Nothing further was submitted.")
        raise SystemExit(0)

log.info(f"Waiting up to {CREDIT_TIMEOUT_SEC}s for the exchange to credit the deposit.")
deadline = monotonic() + CREDIT_TIMEOUT_SEC
while monotonic() < deadline:
    if (result := credited()) is not None:
        log.info(f"Credited: {result}")
        break
    sleep(POLL_INTERVAL_SEC)
else:
    log.warning("Not credited yet. The deposit is in flight, not lost; check again later.")
