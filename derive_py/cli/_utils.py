"""Utility functions for the CLI."""

from __future__ import annotations

import math
import re
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from enum import Enum
from typing import Mapping, Sequence, TypeVar

import msgspec
import pandas as pd
from rich.console import Console
from rich.table import Table

StructT = TypeVar('StructT', bound=msgspec.Struct)


console = Console()


# The API returns money as strings, and the generated models keep them as strings
# rather than guessing a precision, so most numeric cells arrive here as text like
# "2500.123456789012". Match only strings that carry a decimal point: an id, a
# label of "123" or a hex address must survive untouched.
NUMERIC_TEXT = re.compile(r"^-?\d+\.\d+$")

SIG_DIGITS = 6
MIN_DECIMALS = 2
MAX_DECIMALS = 8


def fmt_number(value: Decimal | float | str, sig: int = SIG_DIGITS) -> str:
    """Format a number for display: `sig` significant digits, bounded decimals.

    Kept in Decimal throughout, so a value that arrived exact stays exact until it
    is rounded once, here, for the terminal.

    Magnitudes below the decimal cap render in scientific notation rather than as
    a row of zeros, so a small delta reads as 1e-12 instead of 0.
    """

    number = value if isinstance(value, Decimal) else Decimal(str(value))
    if number == 0:
        return "0"

    order = number.copy_abs().adjusted()
    if order < -MAX_DECIMALS:
        mantissa, _, exponent = f"{number:.{sig - 1}e}".partition("e")
        return f"{mantissa.rstrip('0').rstrip('.')}e{exponent}"

    decimals = min(max(sig - order - 1, MIN_DECIMALS if order >= 0 else 0), MAX_DECIMALS)
    text = format(number.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_EVEN), "f")

    if "." not in text:
        return text

    # Trailing zeros go, but a monetary column keeps its two decimal places so the
    # values in it line up.
    whole, _, fraction = text.partition(".")
    fraction = fraction.rstrip("0").ljust(MIN_DECIMALS if order >= 0 else 0, "0")
    return f"{whole}.{fraction}" if fraction else whole


def _as_number(value) -> Decimal | None:
    """The value as a Decimal if it is a number we should format, else None.

    bool is an int, and int is never formatted: ids, timestamps and counts are not
    quantities and must not grow decimal places.
    """

    if isinstance(value, (bool, int)):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return None if math.isnan(value) else Decimal(str(value))
    if isinstance(value, str) and NUMERIC_TEXT.match(value):
        try:
            return Decimal(value)
        except InvalidOperation:
            return None
    return None


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

    UNSET is normalised to None and Enums are unwrapped. Numbers are left alone:
    rounding twice, once here and once at render, can flatten a small value to
    zero on the way.
    """

    series = pd.Series(msgspec.structs.asdict(struct), dtype=object)
    series = series.map(lambda x: None if x is msgspec.UNSET else x)

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


def _is_numeric_column(values) -> bool:
    """True when every populated cell is a number, so the column can right align."""

    populated = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return bool(populated) and all(_as_number(v) is not None for v in populated)


def _cell(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    number = _as_number(value)
    return fmt_number(number) if number is not None else str(value)


def dataframe_to_rich_table(df: pd.DataFrame, title: str | None = None) -> Table:
    """Convert DataFrame to a rich Table for better CLI display."""

    table = Table(title=title, show_header=True, header_style="bold magenta")

    for column in df.columns:
        table.add_column(column, style="cyan", justify="right" if _is_numeric_column(df[column]) else "left")

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
