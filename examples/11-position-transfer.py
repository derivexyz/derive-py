"""
Position transfers: moving PART of an open perp/option position
between two subaccounts owned by the same wallet.

Position transfers execute as a zero-fee RFQ trade under the hood: both
sides get a maker quote and a matching taker execute, signed and sent
together in one private/transfer_positions call.

Requires a session key holding ProtocolScope.TRANSFER_EXISTING_SUBACCOUNT
(or the broader TRANSFER_ALL/ADMIN).

The two subaccounts must share a risk universe, otherwise the
instrument being transferred isn't one both subaccounts' managers
recognize.

Prerequisites: one wallet with at least two subaccounts in the PRIME risk
universe, one of them holding at least TRANSFER_AMOUNT of INSTRUMENT open,
and enough margin in the other to receive it.

Run:
    python examples/11-position-transfers.py
"""

from decimal import Decimal
from pathlib import Path

from derive_py import HTTPClient
from derive_py.data_types import PositionTransfer, RiskUniverseID
from derive_py.data_types.generated_models import Direction


def format_positions(positions) -> str:
    return ", ".join(f"{p.instrument_name}={p.amount}" for p in positions) or "(none)"


def min_position_transfer(position) -> PositionTransfer:
    """The smallest transferable slice of a position as a transfer object."""

    step = Decimal(position.amount_step)
    full = Decimal(position.amount)
    magnitude = min(step, abs(full))
    amount = -magnitude if full < 0 else magnitude
    return PositionTransfer(position.instrument_name, amount)


env_file = Path(__file__).parent.parent / ".env.template"
client = HTTPClient.from_env(env_file=env_file)

subaccounts = client.fetch_subaccounts()

# in order to transfer positions, both subaccounts must be in the same risk universe
prime_subaccounts = sorted(filter(lambda sa: sa.risk_universe_id is RiskUniverseID.PRIME, subaccounts))

if len(prime_subaccounts) < 2:
    raise SystemExit("Need at least two PRIME subaccounts to transfer a position between.")

# Need to have at least one subaccount with open positions to transfer from.
prime_subaccounts_with_positions = ((s, p) for s in prime_subaccounts if (p := s.positions.list()))
source_sub, source_positions = next(prime_subaccounts_with_positions, (None, None))
if not source_sub or not source_positions:
    raise SystemExit("No subaccount with open positions found.")

target_sub = next(s for s in prime_subaccounts if s.id != source_sub.id)
target_positions = target_sub.positions.list()

print("Before transfer:")
print(f"  Source subaccount #{source_sub.id}: {format_positions(source_positions)}")
print(f"  Target subaccount #{target_sub.id}: {format_positions(target_positions)}")

# Transfer one or multiple positions at once, in part or in full.
positions_to_transfer = list(map(min_position_transfer, source_positions))
print(f"Transferring: {format_positions(positions_to_transfer)}")

result = source_sub.positions.transfer(
    positions=positions_to_transfer,
    direction=Direction.buy,
    to_subaccount=target_sub.id,
)

print(
    f"Position transfer filled: maker={result.maker_quote.status}, taker={result.taker_quote.status}, "
    f"fees=${result.maker_quote.fee}/${result.taker_quote.fee}"
)

print("After transfer:")
print(f"  Source subaccount #{source_sub.id}: {format_positions(source_sub.positions.list())}")
print(f"  Target subaccount #{target_sub.id}: {format_positions(target_sub.positions.list())}")
