"""Tests for Positions module."""

from decimal import Decimal

import pytest

from derive_client.data_types import PositionTransfer
from derive_client.data_types.generated_models import (
    Direction,
    RFQStatus,
    TransferPositionsResponse,
    TxStatus,
)


def test_position_transfer(client_owner_wallet):
    subaccounts = {sa.id: sa for sa in client_owner_wallet.fetch_subaccounts()}

    subaccount_a = subaccounts.get(75723)
    subaccount_b = subaccounts.get(75726)
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

    positions_to_transfer = [
        PositionTransfer(instrument_name=p.instrument_name, amount=Decimal(p.amount)) for p in source_positions
    ]

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
    assert maker_quote.tx_status == TxStatus.settled
    assert taker_quote.tx_status == TxStatus.settled

    assert maker_quote.subaccount_id == source_account.id
    assert taker_quote.subaccount_id == target_account.id
