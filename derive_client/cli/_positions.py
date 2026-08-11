"""CLI commands for positions."""

from __future__ import annotations

from decimal import Decimal

import rich_click as click

from derive_client.data_types import PositionTransfer
from derive_client.data_types.generated_models import Direction, RFQStatus

from ._columns import OPEN_POSITION_COLUMNS
from ._utils import console, print_table, structs_to_dataframe


@click.group("position")
@click.pass_context
def position(ctx):
    """Inspect and transfer positions across subaccounts."""


@position.command("list")
@click.pass_context
def list(ctx):
    """List active positions of a subaccount."""

    client = ctx.obj["client"]
    subaccount = client.active_subaccount
    positions = subaccount.positions.list()

    print_table(
        structs_to_dataframe(positions),
        title=f"Active Positions (subaccount {subaccount.id})",
        columns=OPEN_POSITION_COLUMNS,
    )


@position.command("transfer")
@click.argument("instrument_name")
@click.argument("amount", type=Decimal)
@click.argument("to_subaccount", type=int)
@click.pass_context
def transfer(ctx, instrument_name: str, amount: Decimal, to_subaccount: int):
    """Transfer part of a position to another subaccount of the same wallet.

    The amount is a magnitude; its sign is taken from the position you hold.

    Examples:
        drv position transfer ETH-PERP 0.01 75726
    """

    client = ctx.obj["client"]
    subaccount = client.active_subaccount

    held = next((p for p in subaccount.positions.list() if p.instrument_name == instrument_name), None)
    if held is None:
        raise click.ClickException(f"No {instrument_name} position on subaccount {subaccount.id}")

    magnitude = abs(amount)
    if magnitude > abs(Decimal(held.amount)):
        raise click.ClickException(f"Error: Position is {held.amount}, cannot transfer {magnitude}")

    signed = -magnitude if Decimal(held.amount) < 0 else magnitude

    result = subaccount.positions.transfer(
        positions=[PositionTransfer(instrument_name, signed)],
        direction=Direction.buy,
        to_subaccount=to_subaccount,
    )

    filled = RFQStatus.filled == result.maker_quote.status == result.taker_quote.status
    outcome = "filled" if filled else f"[bold red]{result.maker_quote.status}[/bold red]"
    console.print(f"Transferred {signed} {instrument_name}: subaccount {subaccount.id} → {to_subaccount} ({outcome})")
