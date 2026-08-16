#!/usr/bin/env python3

"""Download ABIs for Derive v3 settlement contracts, for every chain.

Addresses come from derive_py.config.CONFIGS, which mirrors
https://v3.docs.derive.xyz/getting-started/contracts
"""

import json
import sys
import time
from collections.abc import Callable, Iterable

import requests
from web3 import Web3

from derive_py._web3 import make_web3
from derive_py.config import ABI_DATA_DIR, CONFIGS
from derive_py.data_types import Chain, LoggerType
from derive_py.utils.logger import get_logger

TIMEOUT = 10
REQUEST_DELAY = 0.5
RATE_LIMIT_BACKOFF = 30  # seconds, per source, single retry

EIP1967_SLOT = (int.from_bytes(Web3.keccak(text="eip1967.proxy.implementation")[:32], "big") - 1).to_bytes(32, "big")

# Explicit rather than list(Chain), so Sepolia is always attempted first: it is
# the one that currently resolves, and a mainnet RPC stall should not delay it.
CHAINS = (Chain.SEPOLIA, Chain.ETHEREUM)

# abidata.net network id, its own vocabulary and not Chain.network. Ethereum
# mainnet is its default and takes no param.
ABIDATA_NETWORKS: dict[Chain, str | None] = {
    Chain.ETHEREUM: None,
    Chain.SEPOLIA: "sepolia",
}

# The subset of CONFIGS[chain].contracts that is settlement infrastructure. The
# *_MODULE addresses are signing targets, not contracts we call, so no ABI.
CONTRACT_NAMES = ("ACTION_MANAGER", "VAPP", "WITHDRAWAL_OUTBOX", "SPOT_VAULT")

ABIDATA_URL = "https://abidata.net/{address}"
SOURCIFY_URL = "https://sourcify.dev/server/v2/contract/{chain_id}/{address}?fields=abi"


def _fetch_abidata(address: str, chain: Chain) -> list:
    network = ABIDATA_NETWORKS[chain]
    params = {"network": network} if network else None
    response = requests.get(ABIDATA_URL.format(address=address), params=params, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if "abi" not in data:
        raise ValueError(f"abidata.net response had no 'abi' field: keys={list(data.keys())}")
    return data["abi"]


def _fetch_sourcify(address: str, chain: Chain) -> list:
    # int() rather than relying on IntEnum.__format__, which only yields the
    # bare number because 3.11 delegates it to int.
    url = SOURCIFY_URL.format(chain_id=int(chain), address=address)
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if "abi" in data:
        return data["abi"]
    # defensive: some Sourcify responses nest compiler output
    if isinstance(data.get("output"), dict) and "abi" in data["output"]:
        return data["output"]["abi"]
    raise ValueError(f"Sourcify response had no recognisable 'abi' field: keys={list(data.keys())}")


def get_abi(address: str, chain: Chain, logger: LoggerType) -> list:
    """Fetch an ABI for `address` on `chain`. Raises if no source has it."""
    sources: tuple[tuple[str, Callable[[str, Chain], list]], ...] = (
        ("abidata.net", _fetch_abidata),
        ("sourcify", _fetch_sourcify),
    )
    errors: list[str] = []

    for name, fetch in sources:
        for attempt in range(2):
            try:
                return fetch(address, chain)
            except Exception as e:
                error_str = str(e).lower()
                if attempt == 0 and ("rate limit" in error_str or "429" in error_str):
                    logger.warning(f"Rate limited by {name} for {address}, backing off {RATE_LIMIT_BACKOFF}s")
                    time.sleep(RATE_LIMIT_BACKOFF)
                    continue
                errors.append(f"{name}: {e}")
                break

    raise RuntimeError(f"No source had a verified ABI for {address}: {'; '.join(errors)}")


def get_impl_address(w3: Web3, address: str) -> str | None:
    """Get EIP1967 proxy implementation address, if any."""
    data = w3.eth.get_storage_at(address, EIP1967_SLOT)
    impl_address = Web3.to_checksum_address(data[-20:])

    if int(impl_address, 16) == 0:
        return None

    return impl_address


def any_deployed(w3: Web3, addresses: Iterable[str]) -> bool:
    """False means the whole deployment is absent, which is the expected state
    for a chain v3 has not launched on yet. A PARTIAL set is not treated as
    absent: those addresses fail the ABI fetch and the run exits non-zero,
    which is what a genuinely wrong config should look like."""

    return any(w3.eth.get_code(Web3.to_checksum_address(address)) for address in addresses)


def process_chain(chain: Chain, logger: LoggerType) -> list[str]:
    """Download every ABI for one chain. Returns the failures."""
    contracts = CONFIGS[chain].contracts
    w3 = make_web3(chain, logger=logger)

    if not w3.is_connected():
        return [f"{chain.network}: no configured RPC endpoint answered"]

    to_process: list[tuple[str, str]] = [(name, Web3.to_checksum_address(contracts[name])) for name in CONTRACT_NAMES]

    if not any_deployed(w3, (address for _, address in to_process)):
        logger.warning(f"No bytecode at any {chain.network} address, so v3 is not deployed there. Skipping.")
        return []

    abi_dir = ABI_DATA_DIR / chain.network
    abi_dir.mkdir(exist_ok=True, parents=True)

    manifest: dict[str, dict] = {name: {"address": addr} for name, addr in to_process}
    proxy_mapping: dict[str, str] = {}
    failures: list[str] = []

    while to_process:
        name, address = to_process.pop()
        contract_abi_path = abi_dir / f"{address}.json"

        if impl_address := get_impl_address(w3=w3, address=address):
            logger.info(f"EIP1967 proxy detected: {name} ({address}) -> {impl_address}")
            proxy_mapping[address] = impl_address
            manifest[name]["implementation"] = impl_address
            impl_name = f"{name}_IMPLEMENTATION"
            to_process.append((impl_name, impl_address))
            manifest.setdefault(impl_name, {"address": impl_address})

        if contract_abi_path.exists():
            logger.info(f"Already present: {contract_abi_path}")
            continue

        try:
            abi = get_abi(address=address, chain=chain, logger=logger)
        except Exception as e:
            failures.append(f"{chain.network}: {name} ({address}): {e}")
            logger.warning(f"Failed to fetch ABI for {name} ({address}): {e}")
            continue

        contract_abi_path.write_text(json.dumps(abi, indent=4))
        logger.info(f"Saved ABI: {contract_abi_path}")

        if to_process:
            time.sleep(REQUEST_DELAY)

    manifest_path = abi_dir / "contracts.json"
    manifest_path.write_text(json.dumps(manifest, indent=4))
    logger.info(f"Saved contract manifest: {manifest_path}")

    if proxy_mapping:
        proxy_mapping_path = abi_dir / "proxy_mapping.json"
        proxy_mapping_path.write_text(json.dumps(proxy_mapping, indent=4))
        logger.info(f"Saved proxy mapping: {proxy_mapping_path}")

    return failures


def main() -> int:
    logger = get_logger()
    failures: list[str] = []

    for chain in CHAINS:
        logger.info(f"Downloading v3 ABIs for {chain.network}")
        try:
            failures.extend(process_chain(chain, logger))
        except Exception as e:
            failures.append(f"{chain.network}: {e}")
            logger.warning(f"Aborted {chain.network}: {e}")

    if failures:
        logger.error(f"Failed to fetch {len(failures)} ABI(s):")
        for failure in failures:
            logger.error(f"  {failure}")
        return 1

    logger.info("Successfully downloaded all v3 contract ABIs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
