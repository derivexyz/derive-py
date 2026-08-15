"""Tests for System module."""

from derive_py.data_types.generated_models import (
    GetTransactionResult,
    RateLimitResult,
)


def test_system_get_rate_limits(client_admin_wallet):
    rate_limits = client_admin_wallet.system.get_rate_limits()
    assert isinstance(rate_limits, RateLimitResult)


def test_system_get_time(client_admin_wallet):
    unix_millis = client_admin_wallet.system.get_time()
    assert isinstance(unix_millis, int)


def test_system_get_transaction(client_admin_wallet):
    op_uuid = "f589e847-c7a5-40c4-82d5-2d8cec9c93da"
    transaction = client_admin_wallet.system.get_transaction(op_uuid=op_uuid)
    assert isinstance(transaction, GetTransactionResult)
