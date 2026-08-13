from __future__ import annotations

import json

import pytest
from web3 import Web3

from derive_client._web3.provider import FailoverProvider
from derive_client._web3.tx import prepare_transaction
from derive_client.config import ABI_DATA_DIR
from derive_client.config import SEPOLIA_CHAIN_ID as CHAIN_ID
from derive_client.data_types import ChecksumAddress, GasPriority

from .conftest import FakeProvider, ok, static_handler

TOKEN = ChecksumAddress("0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984")
OWNER = ChecksumAddress("0x2170Ed0880ac9A755fd29B2688956BD959F933F8")
SPENDER = ChecksumAddress("0x6B175474E89094C44Da98b954EedeAC495271d0F")


def _fee_history(blocks: int = 30) -> dict:
    percentiles = len(list(GasPriority))
    return {
        "oldestBlock": "0x1",
        "baseFeePerGas": ["0x3b9aca00"] * (blocks + 1),
        "gasUsedRatio": [0.5] * blocks,
        "reward": [["0x3b9aca00"] * percentiles for _ in range(blocks)],
    }


@pytest.fixture
def w3_and_node(logger):
    node = FakeProvider(
        "node",
        static_handler(
            chain_id=CHAIN_ID,
            eth_getTransactionCount=ok("0x5"),
            eth_feeHistory=ok(_fee_history()),
            eth_estimateGas=ok("0x186a0"),
            eth_getBalance=ok(hex(10**18)),
            eth_call=ok("0x"),
            eth_blockNumber=ok("0x64"),
        ),
    )
    provider = FailoverProvider(chain_id=CHAIN_ID, logger=logger, providers=[node])
    return Web3(provider), node


def test_prepare_transaction_reads_the_pending_nonce(w3_and_node, logger):
    """Regression guard. The deposit planners yield an approve step and only
    then build the deposit. Under the default "latest" tag the deposit reuses
    the approve's nonce whenever the approve is broadcast but not yet mined."""

    w3, node = w3_and_node
    abi = json.loads((ABI_DATA_DIR / "erc20.json").read_text())
    func = w3.eth.contract(address=TOKEN, abi=abi).functions.approve(SPENDER, 1)

    tx = prepare_transaction(func, w3=w3, from_address=OWNER, logger=logger)

    call = node.method_calls("eth_getTransactionCount")[0]
    assert call.params[1] == "pending"
    assert tx.get("nonce") == 5
    assert tx.get("chainId") == CHAIN_ID


def test_chain_id_probed_once_then_served_locally_during_builds(w3_and_node, logger):
    """The probe is the cache fill. After it, prepare_transaction's chainId
    read is answered from config without touching the node."""

    w3, node = w3_and_node
    abi = json.loads((ABI_DATA_DIR / "erc20.json").read_text())
    func = w3.eth.contract(address=TOKEN, abi=abi).functions.approve(SPENDER, 1)

    prepare_transaction(func, w3=w3, from_address=OWNER, logger=logger)
    assert len(node.method_calls("eth_chainId")) == 1

    prepare_transaction(func, w3=w3, from_address=OWNER, logger=logger)
    assert len(node.method_calls("eth_chainId")) == 1
