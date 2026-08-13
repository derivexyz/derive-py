import pytest

from derive_client.config import DEFAULT_RPC_ENDPOINTS, resolve_rpc_endpoints
from derive_client.data_types import Environment


def test_defaults_when_no_override():
    assert resolve_rpc_endpoints(Environment.TEST) == DEFAULT_RPC_ENDPOINTS[Environment.TEST]


def test_bare_string_is_not_iterated_per_character():
    assert resolve_rpc_endpoints(Environment.TEST, "https://a.example") == ("https://a.example",)


def test_override_replaces_and_never_appends_defaults():
    result = resolve_rpc_endpoints(Environment.TEST, "https://private.example")
    assert result == ("https://private.example",)
    assert not set(result) & set(DEFAULT_RPC_ENDPOINTS[Environment.TEST])


def test_duplicates_removed_order_preserved():
    given = ["https://b.example", "https://a.example", "https://b.example"]
    assert resolve_rpc_endpoints(Environment.TEST, given) == ("https://b.example", "https://a.example")


@pytest.mark.parametrize("bad", ["ws://a.example", "a.example", "https://", ""])
def test_rejects_malformed(bad):
    with pytest.raises(ValueError):
        resolve_rpc_endpoints(Environment.TEST, [bad])


def test_empty_override_rejected():
    with pytest.raises(ValueError):
        resolve_rpc_endpoints(Environment.TEST, [])
