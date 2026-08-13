"""RPC endpoint resolution. Node choice is deployment config, not protocol truth."""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import urlparse

from derive_client.data_types import Environment

RPC_ENDPOINTS_ENV_VAR = "DERIVE_RPC_ENDPOINTS"

DEFAULT_RPC_ENDPOINTS: dict[Environment, tuple[str, ...]] = {
    Environment.TEST: (
        "https://ethereum-sepolia-rpc.publicnode.com",
        "https://sepolia.drpc.org",
        "https://rpc.sepolia.org",
    ),
    Environment.PROD: (
        "https://ethereum-rpc.publicnode.com",
        "https://eth.drpc.org",
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
