"""CLI commands for system operations."""

from __future__ import annotations

from datetime import datetime, timezone

import rich_click as click


@click.group("system")
@click.pass_context
def system(ctx):
    """Query system-level information."""


@system.command("rate-limits")
@click.pass_context
def rate_limits(ctx):
    """Get the caller's current rate limits."""

    client = ctx.obj["client"]
    rate_limits = client.system.get_rate_limits()

    print("\n=== Rate Limits ===")
    print(f"{rate_limits}")


@system.command("time")
@click.pass_context
def time(ctx):
    """Get the current system time."""

    client = ctx.obj["client"]
    unix_millis = client.system.get_time()
    dt = datetime.fromtimestamp(unix_millis / 1000, tz=timezone.utc)

    print("\n=== Current System Time ===")
    print(f"{unix_millis} ({dt.isoformat(timespec='milliseconds')})")


@system.command("transaction")
@click.argument(
    "op_uuid",
    required=True,
)
@click.pass_context
def transaction(ctx, op_uuid: str):
    """Get a transaction by its operation UUID."""

    client = ctx.obj["client"]
    transaction = client.system.get_transaction(op_uuid=op_uuid)

    print("\n=== Transaction ===")
    print(f"Status: {transaction.status}")
    print(f"Tx Hash: {transaction.transaction_hash}")
    if transaction.error_log:
        print(f"\nError: {transaction.error_log}")
