#!/usr/bin/env python3

"""Download ABIs for Derive v3 settlement contracts.

Addresses source: https://v3.docs.derive.xyz/getting-started/contracts
"""

import json
import os
import sys
import time

from web3 import Web3

from derive_client.config import ABI_DATA_DIR
from derive_client.utils.logger import get_logger
from derive_client.utils.retry import get_retry_session

TIMEOUT = 10
REQUEST_DELAY = 0.5
RATE_LIMIT_BACKOFF = 30  # seconds, per source, single retry

EIP1967_SLOT = (int.from_bytes(Web3.keccak(text="eip1967.proxy.implementation")[:32], "big") - 1).to_bytes(32, "big")

# Only Sepolia exists today. Add a "mainnet" entry here once Derive v3 is live on mainnet
NETWORK = "sepolia"
CHAIN_ID = 11155111

SEPOLIA_RPC_URL = os.environ.get("DERIVE_V3_SEPOLIA_RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com")

# Raw strings on purpose -- checksummed via Web3.to_checksum_address() below
# rather than trusted verbatim from the docs.
SEPOLIA_CONTRACTS: dict[str, str] = {
    "ACTION_MANAGER": "0x1b4f369b585D40a27F66775844FC265151f278A4",
    "VAPP": "0x806A2f83d5E01a5526629c1A5FB4A4AAc60bc393",
    "WITHDRAWAL_OUTBOX": "0x55B1A897E2ecbb4489218E961C64f3E6b1F0f988",
    "SPOT_VAULT": "0xB20790d63f648feA1A23948CDF1B8769DF78a173",
}

ABIDATA_URL = "https://abidata.net/{address}?network=sepolia"
SOURCIFY_URL = "https://sourcify.dev/server/v2/contract/{chain_id}/{address}?fields=abi"


def _fetch_abidata(session, address: str) -> list:
    url = ABIDATA_URL.format(address=address)
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if "abi" not in data:
        raise ValueError(f"abidata.net response had no 'abi' field: keys={list(data.keys())}")
    return data["abi"]


def _fetch_sourcify(session, address: str) -> list:
    url = SOURCIFY_URL.format(chain_id=CHAIN_ID, address=address)
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if "abi" in data:
        return data["abi"]
    # defensive: some Sourcify responses nest compiler output
    if isinstance(data.get("output"), dict) and "abi" in data["output"]:
        return data["output"]["abi"]
    raise ValueError(f"Sourcify response had no recognisable 'abi' field: keys={list(data.keys())}")


def get_abi(session, address: str, logger) -> list:
    """Fetch an ABI for `address` on Sepolia. Raises if no source has it."""
    sources = [("abidata.net", _fetch_abidata), ("sourcify", _fetch_sourcify)]
    errors: list[str] = []

    for name, fetch in sources:
        for attempt in range(2):
            try:
                return fetch(session, address)
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


def main() -> int:
    logger = get_logger()
    session = get_retry_session()
    w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))

    if not w3.is_connected():
        logger.error(f"Could not connect to Sepolia RPC at {SEPOLIA_RPC_URL}")
        return 1

    abi_dir = ABI_DATA_DIR.parent / "abis" / NETWORK
    abi_dir.mkdir(exist_ok=True, parents=True)

    to_process: list[tuple[str, str]] = [
        (name, Web3.to_checksum_address(addr)) for name, addr in SEPOLIA_CONTRACTS.items()
    ]

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
            abi = get_abi(session=session, address=address, logger=logger)
        except Exception as e:
            failures.append(f"{name} ({address}): {e}")
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

    if failures:
        logger.error(f"Failed to fetch {len(failures)} ABI(s):")
        for failure in failures:
            logger.error(f"  {failure}")
        return 1

    logger.info("Successfully downloaded all v3 Sepolia contract ABIs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
