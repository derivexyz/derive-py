"""Encrypted key storage in the Web3 Secret Storage v3 format, as used by geth and foundry.

Keystores live in ~/.derive-py/keystores/<name>.json unless DERIVE_KEYSTORE_DIR
points elsewhere, for example at ~/.foundry/keystores. The password comes from
DERIVE_KEYSTORE_PASSWORD, or is prompted for on a terminal.
"""

from __future__ import annotations

import json
import os
import sys
from getpass import getpass
from pathlib import Path

from eth_account import Account
from eth_account.signers.local import LocalAccount

from derive_py.data_types import ChecksumAddress

DEFAULT_KEYSTORE_DIR = Path.home() / ".derive-py" / "keystores"
PASSWORD_ENV = "DERIVE_KEYSTORE_PASSWORD"


def keystore_dir() -> Path:
    """DERIVE_KEYSTORE_DIR if set, otherwise ~/.derive-py/keystores."""

    configured = os.environ.get("DERIVE_KEYSTORE_DIR")
    return Path(configured).expanduser() if configured else DEFAULT_KEYSTORE_DIR


def resolve_keystore(name_or_path: str) -> Path:
    """A bare name means <keystore_dir>/<name>.json; anything else is a path."""

    path = Path(name_or_path).expanduser()
    if path.parent == Path(".") and path.suffix == "":
        return keystore_dir() / f"{name_or_path}.json"
    return path


def keystore_address(path: Path) -> ChecksumAddress:
    """The address a keystore holds, read without decrypting it."""

    return ChecksumAddress("0x" + json.loads(path.read_text())["address"])


def keystore_password(path: Path, *, confirm: bool = False) -> str:
    """DERIVE_KEYSTORE_PASSWORD if set, otherwise a prompt. Raises ValueError without a terminal."""

    if (password := os.environ.get(PASSWORD_ENV)) is not None:
        return password
    if not sys.stdin.isatty():
        raise ValueError(f"No terminal to prompt for the password of {path}; set {PASSWORD_ENV}.")
    password = getpass(f"Password for {path}: ")
    if confirm and getpass("Repeat password: ") != password:
        raise ValueError("Passwords differ.")
    return password


def load_keystore(path: Path, password: str) -> LocalAccount:
    """Decrypt a keystore. Raises ValueError on a wrong password."""

    try:
        return Account.from_key(Account.decrypt(path.read_text(), password))
    except ValueError as e:
        raise ValueError(f"Could not decrypt {path}: {e}") from e


def create_keystore(path: Path, password: str, *, private_key: str | None = None) -> LocalAccount:
    """Encrypt private_key, or a newly generated key, into a new keystore file.

    Never overwrites: raises FileExistsError if path exists. The directory is
    created owner-only, and the file is owner-readable before anything is written.
    """

    account = Account.from_key(private_key) if private_key is not None else Account.create()
    encrypted = Account.encrypt(account.key, password)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.touch(mode=0o600, exist_ok=False)
    path.write_text(json.dumps(encrypted))
    return account
