from __future__ import annotations

import threading

import pytest
import requests
from web3 import Web3
from web3.types import RPCEndpoint

from derive_py._web3.provider import FailoverProvider
from derive_py.data_types import Chain
from derive_py.exceptions import AllEndpointsFailed, ChainIdMismatch

from .conftest import FakeProvider, ok, rpc_error, static_handler

CHAIN = Chain.SEPOLIA


def build(*providers: FakeProvider, logger, cooldown: float = 60.0) -> FailoverProvider:
    return FailoverProvider(chain=CHAIN, logger=logger, cooldown=cooldown, providers=list(providers))


def test_chain_id_served_locally_without_touching_the_network(logger):
    a = FakeProvider("a", static_handler())
    provider = build(a, logger=logger)

    response = provider.make_request(RPCEndpoint("eth_chainId"), [])

    assert int(str(response.get("result")), 16) == CHAIN.value
    assert a.calls == []


def test_chain_id_probed_once_then_never_again(logger):
    a = FakeProvider("a", static_handler(eth_blockNumber=ok("0x1")))
    provider = build(a, logger=logger)

    for _ in range(3):
        provider.make_request(RPCEndpoint("eth_blockNumber"), [])

    assert len(a.method_calls("eth_chainId")) == 1


def test_chain_id_mismatch_disables_the_endpoint_and_fails_over(logger):
    wrong = FakeProvider("wrong", static_handler(chain=Chain.ETHEREUM, eth_blockNumber=ok("0x1")))
    right = FakeProvider("right", static_handler(eth_blockNumber=ok("0x2")))
    provider = build(wrong, right, logger=logger)

    assert provider.make_request(RPCEndpoint("eth_blockNumber"), []).get("result") == "0x2"
    # Permanently barred, not merely cooled down.
    provider.make_request(RPCEndpoint("eth_blockNumber"), [])
    assert wrong.method_calls("eth_blockNumber") == []


def test_verify_all_fails_fast_on_mismatch(logger):
    wrong = FakeProvider("wrong", static_handler(chain=Chain.ETHEREUM))
    provider = build(wrong, logger=logger)

    with pytest.raises(ChainIdMismatch) as excinfo:
        provider.verify_all()
    assert excinfo.value.actual == 1
    assert excinfo.value.expected == CHAIN.value


def test_transport_error_fails_over(logger):
    dead = FakeProvider("dead", static_handler(eth_blockNumber=requests.exceptions.ConnectTimeout("boom")))
    live = FakeProvider("live", static_handler(eth_blockNumber=ok("0x2")))
    provider = build(dead, live, logger=logger)

    assert provider.make_request(RPCEndpoint("eth_blockNumber"), []).get("result") == "0x2"


def test_retryable_rpc_error_fails_over(logger):
    limited = FakeProvider("limited", static_handler(eth_blockNumber=rpc_error(-32000, "rate limit exceeded")))
    live = FakeProvider("live", static_handler(eth_blockNumber=ok("0x2")))
    provider = build(limited, live, logger=logger)

    assert provider.make_request(RPCEndpoint("eth_blockNumber"), []).get("result") == "0x2"


def test_execution_reverted_is_returned_not_retried(logger):
    a = FakeProvider("a", static_handler(eth_call=rpc_error(-32000, "execution reverted: TokenTransferFailed")))
    b = FakeProvider("b", static_handler(eth_call=ok("0x")))
    provider = build(a, b, logger=logger)

    response = provider.make_request(RPCEndpoint("eth_call"), [{}])

    assert response.get("error", {}).get("code") == -32000
    assert b.method_calls("eth_call") == []


def test_never_retry_wins_over_a_retryable_substring(logger):
    # "exceeded" is in the retryable list; "execution reverted" must still win.
    a = FakeProvider("a", static_handler(eth_call=rpc_error(-32000, "execution reverted: quota exceeded")))
    b = FakeProvider("b", static_handler(eth_call=ok("0x")))
    provider = build(a, b, logger=logger)

    assert "error" in provider.make_request(RPCEndpoint("eth_call"), [{}])
    assert b.method_calls("eth_call") == []


def test_nonretryable_exception_propagates(logger):
    a = FakeProvider("a", static_handler(eth_blockNumber=KeyError("bug")))
    b = FakeProvider("b", static_handler(eth_blockNumber=ok("0x2")))
    provider = build(a, b, logger=logger)

    with pytest.raises(KeyError):
        provider.make_request(RPCEndpoint("eth_blockNumber"), [])
    assert b.method_calls("eth_blockNumber") == []


def test_all_endpoints_failed_carries_every_reason(logger):
    a = FakeProvider("a", static_handler(eth_blockNumber=rpc_error(-32000, "rate limit")))
    b = FakeProvider("b", static_handler(eth_blockNumber=requests.exceptions.ConnectTimeout("boom")))
    provider = build(a, b, logger=logger)

    with pytest.raises(AllEndpointsFailed) as excinfo:
        provider.make_request(RPCEndpoint("eth_blockNumber"), [])
    assert set(excinfo.value.failures) == {"a", "b"}


def test_already_known_returns_the_transaction_hash(logger):
    raw = "0xdeadbeef"
    a = FakeProvider("a", static_handler(eth_sendRawTransaction=rpc_error(-32000, "already known")))
    provider = build(a, logger=logger)

    response = provider.make_request(RPCEndpoint("eth_sendRawTransaction"), [raw])

    assert response.get("result") == str(Web3.to_hex(Web3.keccak(hexstr=raw)))


def test_cooldown_then_reset_to_head(logger):
    state = {"fail": True}

    def flaky(method: str, params):
        if method == "eth_chainId":
            return ok(hex(CHAIN))
        return rpc_error(-32000, "rate limit") if state["fail"] else ok("0x1")

    a = FakeProvider("a", flaky)
    b = FakeProvider("b", static_handler(eth_blockNumber=ok("0x2")))
    provider = build(a, b, logger=logger, cooldown=0.0)

    assert provider.make_request(RPCEndpoint("eth_blockNumber"), []).get("result") == "0x2"
    state["fail"] = False
    # cooldown=0 means a is immediately a candidate again, and it is at the head.
    assert provider.make_request(RPCEndpoint("eth_blockNumber"), []).get("result") == "0x1"


def test_pin_suppresses_reset_to_head(logger):
    a = FakeProvider("a", static_handler(eth_blockNumber=rpc_error(-32000, "rate limit")))
    b = FakeProvider("b", static_handler(eth_blockNumber=ok("0x2")))
    provider = build(a, b, logger=logger, cooldown=0.0)

    provider.make_request(RPCEndpoint("eth_blockNumber"), [])
    before = len(a.method_calls("eth_blockNumber"))
    with provider.pin():
        provider.make_request(RPCEndpoint("eth_blockNumber"), [])
    assert len(a.method_calls("eth_blockNumber")) == before


def test_generation_increments_only_on_switch(logger):
    a = FakeProvider("a", static_handler(eth_blockNumber=ok("0x1")))
    provider = build(a, logger=logger)

    provider.make_request(RPCEndpoint("eth_blockNumber"), [])
    assert provider.generation == 0
    provider.make_request(RPCEndpoint("eth_blockNumber"), [])
    assert provider.generation == 0


def test_concurrent_requests_do_not_corrupt_state(logger):
    a = FakeProvider("a", static_handler(eth_blockNumber=ok("0x1")))
    provider = build(a, logger=logger)
    errors: list[BaseException] = []

    def worker():
        try:
            for _ in range(50):
                provider.make_request(RPCEndpoint("eth_blockNumber"), [])
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(a.method_calls("eth_chainId")) <= 8  # idempotent races are fine
