"""CLI commands for transactions."""

from __future__ import annotations

import rich_click as click


@click.group("transaction")
@click.pass_context
def transaction(ctx):
    """Query transaction status and details."""


@transaction.command("get")
@click.argument(
    "op_uuid",
    required=True,
)
@click.pass_context
def get(ctx, op_uuid: str):
    """Used for getting a transaction by its operation UUID."""

    client = ctx.obj["client"]
    subaccount = client.active_subaccount
    transaction = subaccount.transactions.get(op_uuid=op_uuid)

    print("\n=== Transaction ===")
    print(f"Status: {transaction.status}")
    print(f"Tx Hash: {transaction.transaction_hash}")
    if transaction.error_log:
        print(f"\nError: {transaction.error_log}")
