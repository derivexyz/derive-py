"""Tests for Positions module."""

import time

import pytest

from derive_client._clients.rest.http.subaccount import Subaccount
from derive_client._clients.utils import PositionTransfer
from derive_client.data_types.generated_models import (
    BatchStatus,
    Direction,
    Position,
    TransferPositionsResponse,
)
from tests.conftest import assert_api_calls


def _get_open_positions_for_instrument(
    subaccount: Subaccount,
    *instrument_name: str,
) -> list[Position]:
    positions = subaccount.positions.list()
    return [p for p in positions if p.instrument_name in instrument_name and p.amount != 0]


def _wait_for_tx_settlement(
    client,
    transaction_id: str,
    timeout: int = 30,
    poll_interval: float = 1.0,
):
    start_time = time.time()
    while time.time() - start_time < timeout:
        transaction = client.transactions.get(op_uuid=transaction_id)
        if transaction.status == BatchStatus.Settled:
            return transaction
        time.sleep(poll_interval)
    raise TimeoutError(f"on transaction settlement: transaction_id={transaction_id} timeout={timeout}s")


@pytest.mark.skip("Requires liquidity on testnet for market orders.")
def test_position_transfer_batch(client_owner_wallet_with_position):
    client_owner_wallet_with_position.fetch_subaccounts()
    subaccount_a, subaccount_b = client_owner_wallet_with_position.cached_subaccounts[1:3]

    positions_a = [p for p in subaccount_a.positions.list(is_open=True)]
    positions_b = [p for p in subaccount_b.positions.list(is_open=True)]

    if len(positions_a) >= 2:
        source = subaccount_a
        target = subaccount_b
        initial_positions = positions_a
    elif len(positions_b) >= 2:
        source = subaccount_b
        target = subaccount_a
        initial_positions = positions_b
    else:
        raise ValueError(
            "Expected exactly one subaccount to have open positions. ",
            f"Found: subaccount_a={len(positions_a)}, subaccount_b={len(positions_b)}",
        )

    positions_by_currency: dict[str, list[Position]] = {}
    for position in initial_positions:
        positions_by_currency.setdefault(position.instrument_name.split("-")[0], []).append(position)

    most_position_currency = max(positions_by_currency.items(), key=lambda item: len(item[1]))[0]
    most_positions = positions_by_currency[most_position_currency]
    positions = [
        PositionTransfer(
            amount=position.amount,
            instrument_name=position.instrument_name,
        )
        for position in most_positions
    ]

    direction = Direction.buy
    with assert_api_calls(client_owner_wallet_with_position, expected=1):
        transfer_batch = source.positions.transfer_batch(
            positions=positions,
            direction=direction,
            to_subaccount=target.id,
        )
        time.sleep(1)

    assert isinstance(transfer_batch, TransferPositionsResponse)
    assert transfer_batch.maker_quote.rfq_id == transfer_batch.taker_quote.rfq_id

    source_positions = subaccount_a.positions.list(is_open=True, currency=most_position_currency)
    target_positions = subaccount_b.positions.list(is_open=True, currency=most_position_currency)

    assert len(source_positions) == 0
    assert len(target_positions) >= 0
