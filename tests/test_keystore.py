"""Encrypted keystores: create, load, locate, and never overwrite."""

import io
import os
from pathlib import Path

import pytest
from eth_account import Account

from derive_py.keystore import (
    create_keystore,
    keystore_address,
    keystore_dir,
    keystore_password,
    load_keystore,
    resolve_keystore,
)

KEY = "0x" + "33" * 32
PASSWORD = "correct horse battery staple"


@pytest.fixture(scope="module")
def keystore(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("home") / "keystores" / "owner.json"
    create_keystore(path, PASSWORD, private_key=KEY)
    return path


def test_round_trip(keystore: Path) -> None:
    assert load_keystore(keystore, PASSWORD).address == Account.from_key(KEY).address


def test_address_readable_without_password(keystore: Path) -> None:
    assert keystore_address(keystore) == Account.from_key(KEY).address


def test_wrong_password_names_the_file(keystore: Path) -> None:
    with pytest.raises(ValueError, match="Could not decrypt"):
        load_keystore(keystore, "wrong")


def test_owner_only_permissions(keystore: Path) -> None:
    assert keystore.stat().st_mode & 0o777 == 0o600
    assert keystore.parent.stat().st_mode & 0o777 == 0o700


def test_never_overwrites(keystore: Path) -> None:
    with pytest.raises(FileExistsError):
        create_keystore(keystore, PASSWORD)


def test_bare_name_resolves_into_keystore_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DERIVE_KEYSTORE_DIR", str(tmp_path))
    assert keystore_dir() == tmp_path
    assert resolve_keystore("owner") == tmp_path / "owner.json"


def test_paths_are_kept(tmp_path: Path) -> None:
    assert resolve_keystore(str(tmp_path / "owner.json")) == tmp_path / "owner.json"
    assert resolve_keystore("owner.json") == Path("owner.json")
    assert resolve_keystore("~/owner.json") == Path.home() / "owner.json"


def test_password_from_environment(monkeypatch: pytest.MonkeyPatch, keystore: Path) -> None:
    monkeypatch.setenv("DERIVE_KEYSTORE_PASSWORD", PASSWORD)
    assert keystore_password(keystore) == PASSWORD


def test_password_without_terminal_is_an_error(monkeypatch: pytest.MonkeyPatch, keystore: Path) -> None:
    monkeypatch.delenv("DERIVE_KEYSTORE_PASSWORD", raising=False)
    monkeypatch.setattr("sys.stdin", io.StringIO())
    with pytest.raises(ValueError, match="DERIVE_KEYSTORE_PASSWORD"):
        keystore_password(keystore)


def test_default_dir_is_under_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "environ", {k: v for k, v in os.environ.items() if k != "DERIVE_KEYSTORE_DIR"})
    assert keystore_dir() == Path.home() / ".derive-py" / "keystores"
