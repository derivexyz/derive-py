"""CLI commands for collateral."""

from __future__ import annotations

import rich_click as click

from ._columns import COLLATERAL_COLUMNS
from ._utils import print_table, structs_to_dataframe


@click.group("collateral")
@click.pass_context
def collateral(ctx):
    """Manage collateral."""


@collateral.command("get")
@click.pass_context
def get(ctx):
    """Get subaccount collaterals."""

    client = ctx.obj["client"]
    subaccount = client.active_subaccount
    collateral = subaccount.collateral.get()

    print_table(
        structs_to_dataframe(collateral.collaterals),
        title=f"Collaterals (subaccount {subaccount.id})",
        columns=COLLATERAL_COLUMNS,
    )
