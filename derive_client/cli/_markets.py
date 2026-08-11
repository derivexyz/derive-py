"""CLI commands for market queries."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

import rich_click as click

from derive_client._clients.utils import iter_instrument_pages
from derive_client.data_types import DeriveJSONRPCErrorCode, RiskUniverseID
from derive_client.data_types.generated_models import AssetType
from derive_client.exceptions import DeriveJSONRPCError

from ._columns import (
    ASSET_COLUMNS,
    CURRENCY_COLUMNS,
    INSTRUMENT_COLUMNS,
    MANAGER_COLUMNS,
    OPTION_PRICING_COLUMNS,
    SPOT_COLUMNS,
    TICKER_COLUMNS,
    TICKER_STATS_COLUMNS,
    UNIVERSE_COLLATERAL_COLUMNS,
    UNIVERSE_COLUMNS,
    UNIVERSE_MANAGER_COLUMNS,
)
from ._utils import (
    console,
    explode_struct_field,
    flatten_struct_column,
    mapping_to_dataframe,
    print_table,
    struct_to_series,
    structs_to_dataframe,
)

if TYPE_CHECKING:
    from derive_client.data_types.generated_models import Instrument


def _collect_instruments(
    client,
    asset_types: Sequence[AssetType],
    *,
    currency: str | None,
    risk_universe_id: RiskUniverseID | None,
    expired: bool,
    limit: int | None,
) -> tuple[list[Instrument], int]:
    """Pull pages lazily until `limit` rows are held. Returns (instruments, total_seen)."""

    page_size = min(limit, 1000) if limit else 1000
    instruments: list[Instrument] = []
    total = 0

    for asset_type in asset_types:
        pages = iter_instrument_pages(
            markets=client.markets,
            instrument_type=asset_type,
            expired=expired,
            currency=currency,
            risk_universe_id=risk_universe_id,
            page_size=page_size,
        )
        try:
            for index, page in enumerate(pages):
                if index == 0:
                    total += page.pagination.count
                instruments.extend(page.instruments)
                if limit and len(instruments) >= limit:
                    return instruments[:limit], total
        except DeriveJSONRPCError as error:
            if error.rpc_error.code != DeriveJSONRPCErrorCode.INSTRUMENT_NOT_FOUND:
                raise

    return instruments, total


def _print_instrument(instrument) -> None:
    series = struct_to_series(instrument)
    detail_cols = ["erc20_details", "perp_details", "option_details"]

    print("\n=== Instrument Info ===")
    print(series.drop(detail_cols).to_string(index=True))

    for column, title in zip(detail_cols, ("ERC20", "Perp", "Option")):
        if series[column] is not None:
            print(f"\n=== {title} Details ===")
            print(struct_to_series(series[column]).to_string(index=True))


def _matches_universe(risk_universe, value: str) -> bool:
    """Match a universe by id or by name, case-insensitively."""

    if value.isdigit():
        return risk_universe.risk_universe_id == int(value)
    name = risk_universe.name if isinstance(risk_universe.name, str) else ""
    return name.upper() == value.upper()


@click.group("market")
@click.pass_context
def market(ctx):
    """Query market data: currencies, instruments, tickers."""


@market.command("currency")
@click.argument("currency", required=False)
@click.option("--all", "-a", is_flag=True, help="Get all currencies")
@click.pass_context
def currency(ctx, currency, all):
    """Get currency details.

    Examples:
        drv market currency USDC
        drv market currency --all
    """

    client = ctx.obj["client"]

    if all:
        currencies = client.markets.get_all_currencies()
    elif currency:
        currencies = [client.markets.get_currency(currency=currency)]
    else:
        click.echo("Error: Provide a currency or use --all")
        ctx.exit(1)

    spot_df = flatten_struct_column(explode_struct_field(currencies, "currency", "spot"), "erc20")

    print_table(structs_to_dataframe(currencies), title="Currencies", columns=CURRENCY_COLUMNS)
    print_table(explode_struct_field(currencies, "currency", "managers"), title="Managers", columns=MANAGER_COLUMNS)
    print_table(spot_df, title="Spot", columns=SPOT_COLUMNS)
    print_table(explode_struct_field(currencies, "currency", "perp"), title="Perps", columns=ASSET_COLUMNS)
    print_table(explode_struct_field(currencies, "currency", "option"), title="Options", columns=ASSET_COLUMNS)


@market.command("instrument")
@click.argument("instrument_name", required=False)
@click.option("--currency", "-c", help="Filter by currency")
@click.option(
    "--type",
    "-t",
    "instrument_type",
    type=click.Choice([x.name for x in AssetType]),
    help="Filter by instrument type (default: all types)",
)
@click.option(
    "--universe",
    "-u",
    "risk_universe",
    type=click.Choice([x.name for x in RiskUniverseID]),
    help="Filter by risk universe",
)
@click.option("--expired", is_flag=True, default=False, help="Include expired instruments")
@click.option("--limit", "-n", type=int, default=100, help="Max rows (0 for no limit)")
@click.pass_context
def instrument(ctx, instrument_name, currency, instrument_type, risk_universe, expired, limit):
    """Get instrument details.

    Examples:
        drv market instrument BTC-USDC
        drv market instrument BTC-PERP
        drv market instrument --currency BTC
        drv market instrument --type option --currency ETH
        drv market instrument --type perp --universe ALTCOIN
    """

    client = ctx.obj["client"]

    if instrument_name and (currency or instrument_type or risk_universe or expired):
        click.echo("Error: Cannot combine an instrument name with filters")
        ctx.exit(1)

    if instrument_name:
        _print_instrument(client.markets.get_instrument(instrument_name=instrument_name))
        return

    asset_types = [AssetType[instrument_type]] if instrument_type else list(AssetType)
    limit = None if limit == 0 else limit
    risk_universe_id = RiskUniverseID[risk_universe] if risk_universe else None

    instruments, total = _collect_instruments(
        client,
        asset_types,
        currency=currency,
        risk_universe_id=risk_universe_id,
        expired=expired,
        limit=limit,
    )

    print_table(structs_to_dataframe(instruments), title="Instruments", columns=INSTRUMENT_COLUMNS)

    truncated = limit is not None and len(instruments) >= limit
    console.print(f"Showing {len(instruments)} of {total}{'+' if truncated else ''}")


@market.command("ticker")
@click.argument("instrument_name", required=False)
@click.option("--currency", "-c", help="Currency (required for options)")
@click.option(
    "--type",
    "-t",
    "instrument_type",
    type=click.Choice([x.name for x in AssetType]),
    help="Instrument type (required without an instrument name)",
)
@click.option("--expiry-date", "-e", type=int, help="Expiry date as YYYYMMDD (options only)")
@click.option("--limit", "-n", type=int, default=100, help="Max rows (0 for no limit)")
@click.pass_context
def ticker(ctx, instrument_name, currency, instrument_type, expiry_date, limit):
    """Get ticker details.

    Examples:
        drv market ticker BTC-PERP
        drv market ticker --type erc20
        drv market ticker --type perp
        drv market ticker --type option --currency ETH --expiry-date 20251226
    """

    client = ctx.obj["client"]

    if instrument_name:
        if currency or instrument_type or expiry_date:
            click.echo("Error: Cannot combine an instrument name with filters")
            ctx.exit(1)
        tickers = {instrument_name: client.markets.get_ticker(instrument_name=instrument_name)}
    else:
        if not instrument_type:
            click.echo("Error: --type is required without an instrument name")
            ctx.exit(1)

        asset_type = AssetType[instrument_type]
        if asset_type is AssetType.option:
            if not currency:
                click.echo("Error: --currency is required for options")
                ctx.exit(1)
            if not expiry_date:
                click.echo("Error: --expiry-date is required for options (YYYYMMDD)")
                ctx.exit(1)
        elif expiry_date:
            click.echo(f"Error: --expiry-date is not allowed for {instrument_type}")
            ctx.exit(1)

        tickers = client.markets.get_tickers(
            currency=currency,
            instrument_type=asset_type,
            expiry_date=expiry_date,
        )

    if not tickers:
        click.echo("No tickers found")
        return

    df = mapping_to_dataframe(tickers, "instrument_name").sort_values("instrument_name", ignore_index=True)
    total = len(df)
    if limit:
        df = df.head(limit)

    print_table(df, title="Tickers", columns=TICKER_COLUMNS)
    print_table(
        flatten_struct_column(df[["instrument_name", "stats"]], "stats"),
        title="Stats",
        columns=TICKER_STATS_COLUMNS,
    )
    if "option_pricing" in df.columns and df.option_pricing.notna().any():
        print_table(
            flatten_struct_column(df[["instrument_name", "option_pricing"]], "option_pricing"),
            title="Option Pricing",
            columns=OPTION_PRICING_COLUMNS,
        )

    console.print(f"Showing {len(df)} of {total}")


@market.command("universe")
@click.argument("universe", required=False)
@click.pass_context
def universe(ctx, universe):
    """List risk universes, their managers and accepted collaterals.

    Examples:
        drv market universe
        drv market universe PRIME
        drv market universe 1
    """

    client = ctx.obj["client"]
    universes = client.markets.get_risk_universes()

    if universe:
        universes = [u for u in universes if _matches_universe(u, universe)]
        if not universes:
            click.echo(f"Error: Unknown risk universe {universe!r}")
            ctx.exit(1)

    print_table(
        flatten_struct_column(structs_to_dataframe(universes), "security_module"),
        title="Risk Universes",
        columns=UNIVERSE_COLUMNS,
    )

    managers_df = explode_struct_field(universes, "risk_universe_id", "managers")
    if not managers_df.empty:
        managers_df = managers_df.assign(
            num_instruments=managers_df.instruments.map(len),
            num_collaterals=managers_df.collaterals.map(len),
        )
    print_table(managers_df, title="Managers", columns=UNIVERSE_MANAGER_COLUMNS)

    if not universe:
        return

    for risk_universe in universes:
        collaterals_df = flatten_struct_column(
            explode_struct_field(risk_universe.managers, "manager_id", "collaterals"), "erc20"
        )
        print_table(collaterals_df, title="Collaterals", columns=UNIVERSE_COLLATERAL_COLUMNS)
