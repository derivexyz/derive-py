"""
08 - Spot transfers: between your own subaccounts, and out to another owner.

Two flows, both EIP-712 signed actions, both acknowledged immediately and
settled asynchronously:

    transfer_spot           between two subaccounts of the same owner. Free.
    transfer_spot_external  to a subaccount belonging to a DIFFERENT owner.
                            The recipient must be whitelisted first, and a
                            fee is always charged.

The FALLBACK risk universe holds collateral that could not be applied to its
intended target. It trades nothing, so it is a valid transfer SOURCE and
never a valid target:
https://v3.docs.derive.xyz/trading/managers-and-risk-universes

max_fee_usd on the external transfer is a cap signed into the action, not a
target. The exchange charges its own fee and the request fails rather than
exceed the cap.

Set RECIPIENT_WALLET below to run the external transfer. It is off by
default because the alternatives are worse: a hardcoded subaccount id only
exists for one wallet, and creating one for the recipient on every run pays
a subaccount-creation fee each time.

TODO: wait_for_settlement is imported from a private module, yet two
examples need it. Re-export it from derive_py.

Prerequisites: two non-fallback subaccounts, one holding at least
TRANSFER_AMOUNT. See 01-deposit.py. Copy .env.template to .env first.

Run:
    python examples/08-transfers.py
"""

from decimal import Decimal

from derive_py import HTTPClient
from derive_py._clients.utils import wait_for_settlement
from derive_py.data_types import RiskUniverseID
from derive_py.exceptions import SettlementFailed, SettlementTimeout

ASSET = "USDC"
TRANSFER_AMOUNT = Decimal("1")
SETTLEMENT_TIMEOUT_SEC = 30

RECIPIENT_WALLET = ""  # another owner's wallet; empty skips the external transfer
RECIPIENT_SUBACCOUNT_ID = 0  # one of theirs; 0 is rejected, they must have one
EXTERNAL_AMOUNT = Decimal("5")  # must clear the risk universe's min_deposit_usd
EXTERNAL_MAX_FEE_USD = Decimal("5")

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

if not subaccounts or balance(subaccounts[0]) < TRANSFER_AMOUNT:
    raise SystemExit(f"No subaccount holds {TRANSFER_AMOUNT} {ASSET}. Run 01-deposit.py first.")

# Richest as source, which may be a fallback subaccount, recovering collateral
# stranded there. Poorest tradable one as target, which never may be.
source = subaccounts[0]
target = min((s for s in tradable if s.id != source.id), key=balance, default=None)
if target is None:
    raise SystemExit("Need a second non-fallback subaccount to receive the transfer.")

log.info(
    f"before:\n"
    f"  source #{source.id}: {balance(source):.4f} {ASSET}\n"
    f"  target #{target.id}: {balance(target):.4f} {ASSET}"
)

internal = source.collateral.transfer_spot(
    amount=TRANSFER_AMOUNT,
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

if not RECIPIENT_WALLET:
    raise SystemExit("Set RECIPIENT_WALLET and RECIPIENT_SUBACCOUNT_ID to run the external transfer.")

source = subaccounts[0].refresh()
if balance(source) < EXTERNAL_AMOUNT + EXTERNAL_MAX_FEE_USD:
    raise SystemExit(f"Subaccount #{source.id} cannot cover {EXTERNAL_AMOUNT} {ASSET} plus the fee cap.")

# External transfers only pay out to pre-approved wallets. Whitelisting is
# itself a signed action, so skip it when the recipient is already listed.
if RECIPIENT_WALLET in client.account.get().whitelisted_recipients:
    log.info(f"{RECIPIENT_WALLET} is already whitelisted")
else:
    whitelist = client.account.update_whitelisted_recipients(add=[RECIPIENT_WALLET], remove=[])
    if not settle(whitelist.op_uuid, "update_whitelisted_recipients"):
        raise SystemExit("Whitelisting has not settled; the transfer would be signed against unconfirmed state.")

external = source.collateral.transfer_spot_external(
    amount=EXTERNAL_AMOUNT,
    asset_name=ASSET,
    recipient_address=RECIPIENT_WALLET,
    to_subaccount_id=RECIPIENT_SUBACCOUNT_ID,
    max_fee_usd=EXTERNAL_MAX_FEE_USD,
)
settle(external.op_uuid, "transfer_spot_external")

# The recipient's balance is not readable from here: this client is
# authenticated as your wallet, not theirs.
log.info(f"source #{source.id} now holds {balance(source.refresh()):.4f} {ASSET}")
