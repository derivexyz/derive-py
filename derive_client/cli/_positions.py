"""CLI commands for positions."""

from __future__ import annotations

from decimal import Decimal

import rich_click as click

from derive_client.data_types import PositionTransfer
from derive_client.data_types.generated_models import Direction, RFQStatus

from ._columns import OPEN_POSITION_COLUMNS, QUOTE_COLUMNS
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
    df = structs_to_dataframe(positions)

    print(f"\n=== Active Positions of subaccount {subaccount.id} ===")
    if not df.empty:
        print(df[OPEN_POSITION_COLUMNS])
    else:
        print("No open positions")


@position.command("transfer")
@click.argument(
    "instrument_name",
    required=True,
)
@click.argument(
    "amount",
    required=True,
    type=Decimal,
)
@click.argument(
    "to_subaccount",
    required=True,
    type=int,
)
@click.pass_context
def transfer(ctx, instrument_name: str, amount: Decimal, to_subaccount: int):
    """Transfers a positions from one subaccount to another, owned by the same wallet.

    Examples:
        drv position transfer BTC-PERP 0.1 123456
        drv position transfer -- ETH-PERP -0.1 123456
    """

    client = ctx.obj["client"]
    subaccount = client.active_subaccount
    transfer = subaccount.positions.transfer(
        positions=[PositionTransfer(instrument_name, amount)],
        direction=Direction.buy,
        to_subaccount=to_subaccount,
    )

    print_table(
        structs_to_dataframe([transfer.maker_quote, transfer.taker_quote]),
        title=f"Transfer from subaccount {subaccount.id} to {to_subaccount}",
        columns=QUOTE_COLUMNS,
    )

    if RFQStatus.filled not in (transfer.maker_quote.status, transfer.taker_quote.status):
        console.print(f"[bold red]Transfer did not fill: {transfer.maker_quote.status}[/bold red]")
