"""Tests for Transactions module."""

from derive_client.data_types.generated_models import (
    GetTransactionResult,
)


def test_transactions_get(client_admin_wallet):
    op_uuid = "f589e847-c7a5-40c4-82d5-2d8cec9c93da"
    transaction = client_admin_wallet.transactions.get(op_uuid=op_uuid)
    assert isinstance(transaction, GetTransactionResult)
