"""RPC endpoint resolution. Node choice is deployment config, not protocol truth."""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import urlparse

from derive_client.data_types import Environment

DEFAULT_RPC_ENDPOINTS: dict[Environment, tuple[str, ...]] = {
    # Order matters: index 0 is the sticky head and serves every request until
    # it fails. Each entry is a DISTINCT operator, because two hostnames behind
    # one backend fail together and buy nothing.
    #
    # Excluded on purpose:
    #   - MEV-protected relays (flashbots, mevblocker, bloxroute, securerpc):
    #     they do not broadcast to the public mempool, which breaks
    #     wait_for_finality's pending-transaction probe, and several do not
    #     serve eth_feeHistory at all.
    #   - URLs carrying a shared demo API key: they rot on someone else's
    #     schedule.
    #   - Plan-gated gateways: drpc and 1rpc both refuse Sepolia on the free
    #     tier with HTTP 400 and {"code":35,"message":"...upgrade to paid
    #     plan"}, so they are unusable for an unauthenticated user.
    #
    # Verified with eth_feeHistory(30, "pending", percentiles); see the live
    # test in tests/test_web3/test_rpc_config.py, which is the pre-release gate.
    Environment.TEST: (
        "https://ethereum-sepolia-rpc.publicnode.com",  # Allnodes
        "https://sepolia.gateway.tenderly.co",  # Tenderly
        "https://sepolia.rpc.thirdweb.com",  # thirdweb
    ),
    Environment.PROD: (
        "https://ethereum-rpc.publicnode.com",  # Allnodes
        "https://eth.drpc.org",  # DRPC
        "https://ethereum-json-rpc.stakely.io",  # Stakely
        "https://eth.merkle.io",  # Merkle
    ),
}


def _normalise(value: str) -> str:
    uri = str(value).strip()
    parsed = urlparse(uri)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"RPC endpoint must be http(s), got {uri!r}")
    if not parsed.netloc:
        raise ValueError(f"RPC endpoint has no host: {uri!r}")
    return uri


def resolve_rpc_endpoints(
    env: Environment,
    override: str | Sequence[str] | None = None,
) -> tuple[str, ...]:
    """Explicit argument wins, otherwise the using packaged defaults."""
    raw = DEFAULT_RPC_ENDPOINTS[env] if override is None else ([override] if isinstance(override, str) else override)
    if not (seen := tuple(dict.fromkeys(map(_normalise, raw)))):
        raise ValueError(f"No RPC endpoints resolved for {env}.")
    return tuple(seen)
