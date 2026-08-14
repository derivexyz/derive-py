"""CLI commands related to wallet."""

from __future__ import annotations

import rich_click as click

from ._columns import COLLATERAL_COLUMNS, ORDER_COLUMNS, POSITION_COLUMNS, SUBACCOUNT_COLUMNS
from ._utils import explode_struct_field, print_series, print_table, struct_to_series, structs_to_dataframe


@click.group("account")
@click.pass_context
def account(ctx):
    """Account details."""


@account.command("get")
@click.pass_context
def get(ctx):
    """Account details."""

    client = ctx.obj["client"]
    account = client.account.get()
    series = struct_to_series(account)

    print_series(series.drop("fee_info"), title="Account")
    print_series(struct_to_series(series.fee_info), title="Fee Info")


@account.command("portfolios")
@click.pass_context
def portfolios(ctx):
    """Get all portfolios of a wallet."""

    client = ctx.obj["client"]
    portfolios = client.account.get_all_portfolios()

    print_table(structs_to_dataframe(portfolios), title="Portfolios", columns=SUBACCOUNT_COLUMNS)
    print_table(
        explode_struct_field(portfolios, "subaccount_id", "collaterals"),
        title="Collaterals",
        columns=COLLATERAL_COLUMNS,
    )
    print_table(
        explode_struct_field(portfolios, "subaccount_id", "positions"),
        title="Positions",
        columns=POSITION_COLUMNS,
    )
    print_table(
        explode_struct_field(portfolios, "subaccount_id", "open_orders"),
        title="Open Orders",
        columns=ORDER_COLUMNS,
    )
