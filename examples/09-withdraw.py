"""
09 - Withdraw collateral to L1.

Two things make withdrawals unlike every other signed action:

    The amount is signed in the ERC-20's NATIVE decimals (USDC has 6), not
    the protocol's usual e18 fixed point. It is resolved from the
    subaccount's own risk universe, so you never pass it.
    The payout address is fixed by the action, not chosen freely. The client
    signs your wallet address as the recipient, and the amount leaves the
    subaccount regardless, so this is not a call to make casually.

TODO: resolve where the payout actually lands before this ships. The client
signs recipient=auth.wallet (subaccount.py:296), while WithdrawModuleData's
own docstring states the exchange forces recipient to equal the SIGNER, which
is the session key's address whenever a session key is configured. Those two
cannot both be true, and the difference is where your money goes. The
shipped .env signs with a session key distinct from the wallet, so a single
testnet run settles it.

Withdrawal is asynchronous. Submitting returns an op_uuid immediately and
settlement (Batching, Executing, Proving, Settling, Settled) follows later,
which is what this polls for. max_fee_usd is a cap signed into the action:
the exchange charges its own fee and the request fails rather than exceed it.

TODO: wait_for_settlement is imported from a private module, yet two
examples need it. Re-export it from derive_py.

Prerequisites: a subaccount holding USDC. Run 01-deposit.py first.
Copy .env.template to .env first.

Run:
    python examples/09-withdraw.py
"""

from derive_py import HTTPClient
from derive_py._clients.utils import wait_for_settlement
from derive_py.data_types import D
from derive_py.exceptions import SettlementFailed, SettlementTimeout

ASSET = "USDC"
AMOUNT = D("5")  # must clear the collateral's min_deposit_usd
MAX_FEE_USD = D("1")
FORCE_BATCH = False  # True settles straight to L1, skipping the batch, at a higher fee
SETTLEMENT_TIMEOUT_SEC = 300

client = HTTPClient.from_env()
log = client.logger

subaccount = client.active_subaccount

# Portfolio figures come back as human-readable decimal strings.
collateral = next((c for c in subaccount.state.collaterals if c.asset_name == ASSET), None)
balance = D(collateral.amount) if collateral else D("0")

if balance < AMOUNT:
    raise SystemExit(f"Subaccount {subaccount.id} holds {balance} {ASSET}. Run 01-deposit.py, or lower AMOUNT.")

log.info(
    f"Subaccount {subaccount.id} holds {balance} {ASSET}, withdrawing {AMOUNT}.\n"
    f"  signed payout recipient: {client.account.address}"
)

response = subaccount.withdraw(
    asset_name=ASSET,
    amount=AMOUNT,
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
