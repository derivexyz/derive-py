"""Tests for Positions module."""

from decimal import Decimal

import pytest

from derive_py.data_types.generated_models import (
    Direction,
    RFQStatus,
    TransferPositionsResponse,
)


def test_position_transfer(client_admin_wallet, min_position_transfer, transfer_subaccounts):
    subaccounts = {sa.id: sa for sa in client_admin_wallet.fetch_subaccounts()}

    subaccount_a_id, subaccount_b_id = transfer_subaccounts
    subaccount_a = subaccounts.get(subaccount_a_id)
    subaccount_b = subaccounts.get(subaccount_b_id)
    if not subaccount_a or not subaccount_b:
        pytest.fail("Expected subaccounts not found. Both must be part of the same risk universe.")

    positions_a = subaccount_a.positions.list()
    positions_b = subaccount_b.positions.list()

    if positions_a:
        source_account, target_account, source_positions = subaccount_a, subaccount_b, positions_a
    elif positions_b:
        source_account, target_account, source_positions = subaccount_b, subaccount_a, positions_b
    else:
        pytest.fail("No open positions found in either subaccount.")

    def _currency(position) -> str:
        instrument = client_admin_wallet.markets.get_instrument(instrument_name=position.instrument_name)
        return instrument.base_currency

    transfer_currency = _currency(source_positions[0])
    same_currency = [p for p in source_positions if _currency(p) == transfer_currency]
    positions_to_transfer = list(map(min_position_transfer, same_currency))

    transfer_position_response: TransferPositionsResponse = source_account.positions.transfer(
        positions=positions_to_transfer,
        direction=Direction.buy,
        to_subaccount=target_account.id,
    )

    maker_quote = transfer_position_response.maker_quote
    taker_quote = transfer_position_response.taker_quote

    assert maker_quote.status == RFQStatus.filled
    assert taker_quote.status == RFQStatus.filled
    assert maker_quote.fill_pct == Decimal("1")
    assert taker_quote.fill_pct == Decimal("1")

    assert maker_quote.subaccount_id == source_account.id
    assert taker_quote.subaccount_id == target_account.id
