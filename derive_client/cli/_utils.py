"""Utility functions for the CLI."""

from __future__ import annotations

import math
from decimal import Decimal
from enum import Enum
from typing import Mapping, Sequence, TypeVar

import msgspec
import pandas as pd
from rich.console import Console
from rich.table import Table

StructT = TypeVar('StructT', bound=msgspec.Struct)


console = Console()


def fmt_sig_up_to(x: float, sig: int = 4) -> str:
    """Format x to up to `sig` significant digits, preserving all necessary decimals."""

    if x == 0:
        return "0"

    order = math.floor(math.log10(abs(x)))
    decimals = max(sig - order - 1, 0)
    formatted = f"{x:.{decimals}f}"
    return formatted.rstrip("0").rstrip(".")


def _quantize_safe(value: Decimal | None, quant=Decimal("0.0001")):
    if value is None:
        return value
    return value.quantize(quant)


def _check_enum_or_list(value):
    if isinstance(value, Enum):
        return True
    elif isinstance(value, list):
        return all(isinstance(y, Enum) for y in value)
    return False


def _convert_enum_value(value: Enum | list[Enum] | None):
    if isinstance(value, Enum):
        return value.value
    elif isinstance(value, list):
        return [item.value for item in value]
    return value


def _is_struct(value) -> bool:
    return isinstance(value, msgspec.Struct)


def struct_to_series(struct: msgspec.Struct) -> pd.Series:
    """Convert a msgspec.Struct to a formatted pandas Series.

    UNSET is normalised to None; Decimals are quantized; Enums are unwrapped.
    """

    series = pd.Series(msgspec.structs.asdict(struct), dtype=object)
    series = series.map(lambda x: None if x is msgspec.UNSET else x)

    decimal_mask = series.map(lambda x: isinstance(x, Decimal))
    series[decimal_mask] = series[decimal_mask].map(_quantize_safe)

    enum_mask = series.map(_check_enum_or_list)
    series[enum_mask] = series[enum_mask].map(_convert_enum_value)

    return series


def structs_to_dataframe(structs: Sequence[StructT]) -> pd.DataFrame:
    """Convert a sequence of msgspec.Structs to a formatted DataFrame, skipping non-structs."""

    return pd.DataFrame(struct_to_series(s) for s in structs if _is_struct(s))


def mapping_to_dataframe(mapping: Mapping[str, StructT], id_field: str) -> pd.DataFrame:
    """Convert a {id: Struct} response to a DataFrame with the key as a leading column."""

    rows = [
        pd.concat([pd.Series({id_field: key}, dtype=object), struct_to_series(value)])
        for key, value in mapping.items()
        if _is_struct(value)
    ]
    return pd.DataFrame(rows)


def explode_struct_field(structs: Sequence[StructT], id_field: str, field: str) -> pd.DataFrame:
    """One row per Struct found in `field`, tagged with `id_field`.

    Accepts scalar struct fields and list fields; empty lists, None and UNSET yield no rows.
    A struct carrying `id_field` itself keeps its own value rather than gaining a duplicate.
    """

    rows = []
    for struct in structs:
        value = getattr(struct, field)
        items = value if isinstance(value, list) else [value]

        for item in items:
            if not _is_struct(item):
                continue
            row = struct_to_series(item)
            if id_field not in row.index:
                ident = pd.Series({id_field: getattr(struct, id_field)}, dtype=object)
                row = pd.concat([ident, row])
            rows.append(row)

    return pd.DataFrame(rows)


def flatten_struct_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Expand a column of nested Structs into sibling columns."""

    if column not in df.columns:
        return df

    expanded = pd.DataFrame(
        [struct_to_series(v) if _is_struct(v) else pd.Series(dtype=object) for v in df[column]],
        index=df.index,
    )
    return pd.concat([df.drop(columns=[column]), expanded], axis=1)


def _cell(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value)


def dataframe_to_rich_table(df: pd.DataFrame, title: str | None = None) -> Table:
    """Convert DataFrame to a rich Table for better CLI display."""

    table = Table(title=title, show_header=True, header_style="bold magenta")

    for column in df.columns:
        table.add_column(column, style="cyan")

    for _, row in df.iterrows():
        table.add_row(*map(_cell, row.values))

    return table


def print_series(series: pd.Series, title: str | None = None):
    """Print a single struct as a two-column rich table."""

    table = Table(title=title, show_header=False, box=None)
    table.add_column(style="bold magenta")
    table.add_column(style="cyan", overflow="fold")

    for label, value in series.items():
        table.add_row(str(label), _cell(value))

    console.print(table)


def print_table(df: pd.DataFrame, title: str | None = None, columns: Sequence[str] | None = None):
    """Convert DataFrame to rich table and print it; missing columns render blank."""

    if columns is not None:
        if not df.empty and (missing := [c for c in columns if c not in df.columns]):
            console.print(f"[dim]missing columns: {', '.join(missing)}[/dim]")
        df = df.reindex(columns=list(columns))
    console.print(dataframe_to_rich_table(df, title=title))
