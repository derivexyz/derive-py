import pytest
from web3 import Web3

from derive_client._web3.provider import FailoverProvider, _describe
from derive_client.config import CONFIGS, DEFAULT_RPC_ENDPOINTS, resolve_rpc_endpoints
from derive_client.data_types import Environment, GasPriority


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


@pytest.mark.parametrize("env", list(Environment))
def test_packaged_defaults_are_wellformed(env):
    assert resolve_rpc_endpoints(env)


@pytest.mark.live
@pytest.mark.parametrize("env", list(Environment))
def test_every_default_endpoint_is_usable(env, logger):
    """Run before publishing. Public endpoints rot, and a dead default is a timeout every user pays for."""

    percentiles = tuple(map(int, GasPriority))
    failures: dict[str, str] = {}

    for uri in resolve_rpc_endpoints(env):
        try:
            provider = FailoverProvider([uri], chain_id=CONFIGS[env].chain_id, logger=logger)
            # Explicit, so a wrong chain surfaces as ChainIdMismatch rather than
            # being folded into AllEndpointsFailed by the next call.
            provider.verify_all()

            # Mirrors estimate_fees exactly: same block count, same percentiles.
            history = Web3(provider).eth.fee_history(30, "pending", list(percentiles))
            rewards = history["reward"]
            base_fees = history["baseFeePerGas"]

            # Row COUNT is allowed to fall short: a node that does not serve a
            # pending block returns the 29 preceding it, and estimate_fees just
            # takes a median over fewer samples. A large shortfall still matters.
            if len(rewards) < 20:
                failures[uri] = f"returned {len(rewards)} reward rows for a 30-block request"

            # Row WIDTH is not. zip() in estimate_fees truncates a short row
            # without complaint, leaving that percentile with no samples at all,
            # so GasPriority.HIGH silently collapses to MIN_PRIORITY_FEE.
            elif narrow := sorted({len(row) for row in rewards if len(row) < len(percentiles)}):
                failures[uri] = f"reward rows of width {narrow}, expected {len(percentiles)}"

            # estimate_fees reads base_fee_per_gas[-1] as the NEXT block's base
            # fee, which holds only when the array is one longer than `reward`.
            elif len(base_fees) != len(rewards) + 1:
                failures[uri] = f"{len(base_fees)} base fees for {len(rewards)} reward rows, expected one more"
        except Exception as exc:  # noqa: BLE001 - the point is to report, not to raise
            failures[uri] = _describe(exc)

    assert not failures, f"unusable {env.name} defaults: {failures}"
