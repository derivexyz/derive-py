"""Turns data/abis/<network>/contracts.json into usable web3.py Contract instances."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from eth_typing import ChecksumAddress as EthChecksumAddress
from web3 import Web3
from web3.contract.contract import Contract

from derive_py.config import ABI_DATA_DIR
from derive_py.data_types import Chain, ChecksumAddress


def _abi_dir(chain: Chain) -> Path:
    return ABI_DATA_DIR / chain.network


class ContractRegistry:
    def __init__(self, w3: Web3, *, chain: Chain):
        self._w3 = w3
        self._chain = chain
        manifest_path = _abi_dir(chain) / "contracts.json"
        self._manifest: dict = json.loads(manifest_path.read_text())
        self._cache: dict[str, Contract] = {}

    def get(self, name: str) -> Contract:
        """Build (or return the cached) Contract for a manifest entry."""

        if name in self._cache:
            return self._cache[name]

        if name not in self._manifest:
            raise KeyError(f"{name!r} not in {self._chain.network} contract manifest. Known: {sorted(self._manifest)}")

        entry = self._manifest[name]
        address = ChecksumAddress(entry["address"])
        abi_source_address = entry.get("implementation", entry["address"])

        abi_path = _abi_dir(self._chain) / f"{abi_source_address}.json"
        abi = json.loads(abi_path.read_text())

        contract = self._w3.eth.contract(address=cast(EthChecksumAddress, address), abi=abi)
        self._cache[name] = contract
        return contract
