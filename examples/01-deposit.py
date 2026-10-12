"""
01 - Deposit: the only way an account or subaccount comes into existence.

Derive v3 has no create-account or create-subaccount call. The first deposit
into a new subaccount creates the account, that subaccount, and a fallback
subaccount under manager 0. This example works out what exists and acts on it:

    no key            offers to create one, encrypted in ~/.derive-py/keystores
    no subaccount     deposits into a new one; on a terminal you pick the risk
                      universe and margin type
    subaccounts       tops up the first tradable one, or opens another when
                      CREATE_NEW_SUBACCOUNT is set or you choose to at the prompt

Either way you get one step per transaction: the ERC-20 approve, skipped
when the allowance already covers it, then the deposit. Each step arrives
prepared, fee-estimated and simulated but unsigned, so you can see what it
costs before it costs anything. Steps are built one at a time: the deposit
cannot be prepared until the approve is mined, because its simulation would
revert on the missing allowance.

Mining is not crediting. The exchange applies the deposit asynchronously,
around two minutes, and the new subaccount id is not in the receipt, so
this waits for the credit afterwards.

Direct deposits only. The Standard deposit-address route is a different
mechanism: https://docs.derive.xyz/getting-started/depositing

Prerequisites: a wallet holding ETH for gas and USDC to deposit. On Sepolia,
mint both at https://testnet.app.derive.xyz/developers. Copy .env.template to
.env first, or leave the signer out of .env to start from a new key.

Run:
    python examples/01-deposit.py

Nothing is submitted without confirmation at the prompt, so running this
anywhere non-interactive prepares the transactions and stops. On a terminal,
it ends by offering to record a new keystore and subaccount in .env, so the
other examples use them.
"""

import os
import sys
from decimal import Decimal
from pathlib import Path
from time import monotonic, sleep

import rich_click as click
from dotenv import set_key

from derive_py import HTTPClient
from derive_py.data_types import D, MarginType, RiskUniverseID
from derive_py.data_types.generated_models import PublicGetSubaccountsRequest
from derive_py.exceptions import (
    FinalityTimeout,
    InsufficientNativeBalance,
    InsufficientTokenBalance,
    TxPendingTimeout,
)
from derive_py.keystore import create_keystore, keystore_password, resolve_keystore

ASSET = "USDC"
AMOUNT = D("5")  # below the collateral's min_deposit_usd it is donated, not credited

CREATE_NEW_SUBACCOUNT = False
RISK_UNIVERSE = RiskUniverseID.PRIME  # creating one only: see client.markets.get_risk_universes()
MARGIN_TYPE = MarginType.SM  # creating one only
KEYSTORE_NAME = "owner"

CREDIT_TIMEOUT_SEC = 300
POLL_INTERVAL_SEC = 5

ENV_FILE = Path.cwd() / ".env"
INTERACTIVE = sys.stdin.isatty()

client = HTTPClient.from_env()
log = client.logger  # one stream: the client logs here too
env_updates: dict[str, str] = {}

if client._auth is None:
    keystore = resolve_keystore(KEYSTORE_NAME)
    if keystore.exists():
        raise SystemExit(f"No signer configured, but {keystore} exists: set DERIVE_KEYSTORE={KEYSTORE_NAME} in .env.")
    if not INTERACTIVE or not click.confirm(f"No signer configured. Create a new key in {keystore}?", default=False):
        log.warning("No signer: set DERIVE_KEYSTORE, or DERIVE_SESSION_KEY and DERIVE_WALLET, in .env.")
        raise SystemExit(0)
    owner = create_keystore(keystore, keystore_password(keystore, confirm=True))
    log.info(f"Created wallet {owner.address}, its key encrypted in {keystore}. Unlock it once more to continue.")
    os.environ["DERIVE_KEYSTORE"] = str(keystore)
    env_updates["DERIVE_KEYSTORE"] = KEYSTORE_NAME
    client = HTTPClient.from_env()
    log = client.logger

if client._auth is None:
    raise SystemExit("No signer configured.")
wallet = client._auth.wallet


def subaccount_ids() -> set[int]:
    """Public, so it works before the account exists: an empty list until the first deposit."""

    return set(client.public_api.rpc.get_subaccounts(PublicGetSubaccountsRequest(wallet=wallet)).subaccount_ids)


def usdc_balance(subaccount) -> Decimal:
    collateral = next((c for c in subaccount.state.collaterals if c.asset_name == ASSET), None)
    return Decimal(collateral.amount) if collateral else Decimal("0")


def choose_manager() -> tuple[RiskUniverseID, MarginType]:
    """Prompt for the universe and margin type on a terminal, else use the constants."""

    if not INTERACTIVE:
        return RISK_UNIVERSE, MARGIN_TYPE

    universes = {
        RiskUniverseID(ru.risk_universe_id).name: ru
        for ru in client.markets.get_risk_universes()
        if ru.risk_universe_id != RiskUniverseID.FALLBACK
    }
    name = click.prompt("Risk universe", type=click.Choice(list(universes)), default=RISK_UNIVERSE.name)
    margin_types = [m.margin_type.value for m in universes[name].managers]
    default = MARGIN_TYPE.value if MARGIN_TYPE.value in margin_types else margin_types[0]
    margin = click.prompt("Margin type", type=click.Choice(margin_types), default=default)
    return RiskUniverseID[name], MarginType(margin)


def submit(step) -> bool:
    """Show what the transaction costs, then submit it only if confirmed."""

    tx = step.tx_params
    worst_case_eth = Decimal(tx["gas"] * tx["maxFeePerGas"]) / Decimal(10**18)
    log.info(
        f"[{step.kind}] {step.description}\n"
        f"  gas {tx['gas']} at up to {tx['maxFeePerGas'] / 1e9:.2f} gwei, {worst_case_eth:.6f} ETH worst case"
    )

    if not INTERACTIVE:
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


known_ids = subaccount_ids()
create_new = (
    not known_ids
    or CREATE_NEW_SUBACCOUNT
    or (INTERACTIVE and click.confirm("Open a new subaccount rather than top up?", default=False))
)

if create_new:
    # A wallet's first deposit creates two subaccounts: the one you asked for,
    # plus a fallback under manager 0 that catches deposits which cannot be
    # applied. Two new ids on a first run is normal.
    risk_universe, margin_type = choose_manager()
    log.info(f"Creating a {margin_type} subaccount in {risk_universe.name} with {AMOUNT} {ASSET} for {wallet}.")
    steps = client.plan_deposit_to_new_subaccount(
        risk_universe_id=risk_universe,
        margin_type=margin_type,
        asset_name=ASSET,
        amount=AMOUNT,
    )

    def credited() -> str | None:
        """The receipt does not carry the new id, so diff the list instead."""

        new_ids = subaccount_ids() - known_ids
        if not new_ids:
            return None
        tradable = [
            s for s in map(client.fetch_subaccount, sorted(new_ids)) if s.risk_universe_id != RiskUniverseID.FALLBACK
        ]
        if tradable:
            env_updates["DERIVE_SUBACCOUNT_ID"] = str(tradable[0].id)
        return f"new subaccount(s) {sorted(new_ids)}"

else:
    # Never deposit into the FALLBACK universe: it holds orphaned collateral
    # for recovery and trades nothing.
    tradable = [s for s in client.fetch_subaccounts() if s.risk_universe_id is not RiskUniverseID.FALLBACK]
    if not tradable:
        raise SystemExit("No tradable subaccount on this wallet. Set CREATE_NEW_SUBACCOUNT = True to make one.")

    target = tradable[0]

    opening_balance = usdc_balance(target)
    log.info(f"Depositing {AMOUNT} {ASSET} from L1 into subaccount {target.id}, holding {opening_balance} {ASSET}.")
    steps = target.plan_deposit(asset_name=ASSET, amount=AMOUNT)

    def credited() -> str | None:
        balance = usdc_balance(target.refresh())
        return f"subaccount {target.id} now holds {balance} {ASSET}" if balance > opening_balance else None


def record_in_env() -> None:
    """Offer to write what this run created to .env, touching only those keys."""

    if not env_updates or not INTERACTIVE:
        return
    listing = ", ".join(f"{key}={value}" for key, value in env_updates.items())
    if click.confirm(f"Record {listing} in {ENV_FILE}?", default=True):
        for key, value in env_updates.items():
            set_key(ENV_FILE, key, value)
        log.info(f"Updated {ENV_FILE}")


try:
    for step in steps:
        if not submit(step):
            # Prepared but not submitted is the documented outcome of declining or
            # of running non-interactively, not a failure.
            log.info("Stopped before the deposit completed. Nothing further was submitted.")
            record_in_env()
            raise SystemExit(0)
except (InsufficientTokenBalance, InsufficientNativeBalance) as e:
    # The deposit is funded from the L1 wallet, not from the subaccount, so a
    # healthy exchange balance says nothing about whether this can run. An
    # unfunded wallet is a setup gap rather than a fault in the SDK.
    log.warning(f"{e}")
    log.warning(f"Fund {wallet} on L1 with {ASSET} and ETH for gas, then rerun.")
    record_in_env()
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

record_in_env()
