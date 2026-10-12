"""Which credential combinations ClientConfig and load_client_config accept."""

import os
from pathlib import Path

import pytest
from eth_account import Account
from hexbytes import HexBytes
from pydantic import SecretStr, ValidationError

from derive_py._clients.utils import load_client_config
from derive_py.data_types import Chain, ChecksumAddress, ClientConfig

KEY = "0x" + "11" * 32
WALLET = ChecksumAddress(Account.from_key(KEY).address)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hide DERIVE_* from the real environment, and keep load_dotenv's writes inside this test."""

    monkeypatch.setattr(os, "environ", {k: v for k, v in os.environ.items() if not k.startswith("DERIVE_")})


def write_env(directory: Path, values: dict[str, str]) -> Path:
    path = directory / ".env"
    path.write_text("".join(f"{name}={value}\n" for name, value in values.items()))
    return path


def test_chain_alone_is_public_only() -> None:
    config = ClientConfig(chain=Chain.SEPOLIA)
    assert (config.session_key, config.wallet, config.subaccount_id) == (None, None, None)


def test_signer_without_subaccount() -> None:
    config = ClientConfig(chain=Chain.SEPOLIA, session_key=SecretStr(KEY), wallet=WALLET)
    assert config.wallet == WALLET
    assert config.subaccount_id is None


@pytest.mark.parametrize(
    "fields",
    [
        {"session_key": SecretStr(KEY)},
        {"wallet": WALLET},
        {"subaccount_id": 1},
        {"wallet": WALLET, "subaccount_id": 1},
    ],
    ids=["key only", "wallet only", "subaccount only", "wallet and subaccount"],
)
def test_incomplete_signer_is_rejected(fields: dict[str, SecretStr | ChecksumAddress | int]) -> None:
    with pytest.raises(ValidationError):
        ClientConfig.model_validate({"chain": Chain.SEPOLIA, **fields})


@pytest.mark.usefixtures("clean_env")
def test_empty_env_loads_public_only(tmp_path: Path) -> None:
    config = load_client_config(env_file=write_env(tmp_path, {}))
    assert config.chain is Chain.SEPOLIA
    assert (config.session_key, config.wallet, config.subaccount_id) == (None, None, None)


@pytest.mark.usefixtures("clean_env")
def test_full_env_loads_signer_and_subaccount(tmp_path: Path) -> None:
    env = {
        "DERIVE_SESSION_KEY": KEY,
        "DERIVE_WALLET": WALLET,
        "DERIVE_SUBACCOUNT_ID": "7",
        "DERIVE_ETH_CHAIN": "ETHEREUM",
    }
    config = load_client_config(env_file=write_env(tmp_path, env))
    assert config.session_key is not None
    assert HexBytes(config.session_key.get_secret_value()) == HexBytes(KEY)
    assert (config.wallet, config.subaccount_id, config.chain) == (WALLET, 7, Chain.ETHEREUM)


@pytest.mark.usefixtures("clean_env")
@pytest.mark.parametrize(
    "env",
    [
        {"DERIVE_SESSION_KEY": KEY},
        {"DERIVE_WALLET": WALLET},
        {"DERIVE_SUBACCOUNT_ID": "7"},
    ],
    ids=["key only", "wallet only", "subaccount only"],
)
def test_incomplete_env_is_rejected(tmp_path: Path, env: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="Incomplete signer configuration"):
        load_client_config(env_file=write_env(tmp_path, env))
