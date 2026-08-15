"""
11 - Position transfers: moving part of an open position between two
subaccounts owned by the same wallet.

A transfer executes as a zero-fee RFQ trade: the source subaccount signs the
maker side, the target signs the taker side, and both go out together in one
private/transfer_positions call.

    Both subaccounts must share a risk universe, otherwise the instrument is
    not one both managers recognise. This picks a universe that has two, so
    it works whichever universe your subaccounts live in.
    Each leg's direction is derived from the sign of its amount, so a
    negative amount transfers a short. The direction argument is the
    package-level direction signed on the MAKER side; the taker side is
    signed as its opposite.
    Amounts are quantized to the instrument's amount_step, so the smallest
    transferable slice is one step, or the whole position when it is smaller.

Requires a session key holding ProtocolScope.TRANSFER_EXISTING_SUBACCOUNT,
or the broader TRANSFER_ALL or ADMIN.

Prerequisites: two subaccounts in one non-fallback risk universe, one of
them holding an open position, and enough margin in the other to receive it.
Copy .env.template to .env first.

Run:
    python examples/11-position-transfer.py
"""

from decimal import Decimal

from derive_py import HTTPClient
from derive_py.data_types import PositionTransfer, RiskUniverseID
from derive_py.data_types.generated_models import Direction

client = HTTPClient.from_env()
log = client.logger


def format_positions(positions) -> str:
    return ", ".join(f"{p.instrument_name}={p.amount}" for p in positions) or "(none)"


def smallest_slice(position) -> PositionTransfer:
    """One amount_step of a position, or all of it when it is smaller."""

    full = Decimal(position.amount)
    magnitude = min(Decimal(position.amount_step), abs(full))
    return PositionTransfer(position.instrument_name, -magnitude if full < 0 else magnitude)


# FALLBACK holds orphaned collateral and trades nothing, so it never takes part.
subaccounts = [s for s in client.fetch_subaccounts() if s.risk_universe_id is not RiskUniverseID.FALLBACK]

source, positions = next(((s, p) for s in subaccounts if (p := s.positions.list())), (None, None))
if source is None or positions is None:
    raise SystemExit("No subaccount holds an open position. Run 05-place-order.py and let one fill.")

target = next((s for s in subaccounts if s.id != source.id and s.risk_universe_id is source.risk_universe_id), None)
if target is None:
    raise SystemExit(f"Need a second subaccount in {source.risk_universe_id.name} to receive the transfer.")

# transfer() takes a list, so several positions can move at once. This moves
# the smallest slice of one of them.
transfer = [smallest_slice(positions[0])]

log.info(
    f"before, in {source.risk_universe_id.name}:\n"
    f"  source #{source.id}: {format_positions(positions)}\n"
    f"  target #{target.id}: {format_positions(target.positions.list())}\n"
    f"  transferring: {format_positions(transfer)}"
)

result = source.positions.transfer(
    positions=transfer,
    direction=Direction.buy,
    to_subaccount=target.id,
)

log.info(
    f"filled: maker={result.maker_quote.status}, taker={result.taker_quote.status},"
    f" fees ${result.maker_quote.fee}/${result.taker_quote.fee}\n"
    f"  source #{source.id}: {format_positions(source.positions.list())}\n"
    f"  target #{target.id}: {format_positions(target.positions.list())}"
)
