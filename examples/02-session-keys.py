"""
02 - Session keys: register a scoped, expiring key, edit it, retire it.

A session key is a plain Ethereum keypair you authorise to sign actions for
your wallet, limited by a scope list and an expiry. Two mechanisms, not one
general-purpose update:

    set_session_key   a signed action. Sets protocol_scopes (on-chain
                      authority, signed into the payload) and offchain_scopes
                      (server-side only). The same call registers, refreshes
                      and retires: retiring is writing a nearer expiry with
                      empty scopes. There is no delete, and expiry_sec is
                      floored at 300s from now (error 14039), so a retired
                      key stays listed until that lapses.
    edit_session_key  no signature at all. Off-chain fields only: label,
                      ip_whitelist, offchain_scopes. protocol_scopes cannot
                      be changed here; call set_session_key again for those.

Because keys are never deleted, a new keypair per run would leave a growing
list of dead entries. This registers one key the first time and refreshes
that same entry on every run after. Derive only ever returns a key's address,
so the private key is shown once, on the run that creates it, and never again.

This ends by retiring the key it made. To keep one instead, answer yes at the
first prompt. That skips the demo and registers a key labelled KEEP_LABEL, with
KEEP_SCOPES and KEEP_LIFETIME_SEC, encrypted in ~/.derive-py/keystores/<KEEP_LABEL>.json.
A later run refreshes that same key rather than minting another. It then offers
to point .env at it: DERIVE_KEYSTORE=<KEEP_LABEL> plus DERIVE_WALLET, removing
any plaintext DERIVE_SESSION_KEY, which would otherwise take precedence. The
session key holds no withdraw scope and no L1 funds, so for deposits and
withdrawals set DERIVE_KEYSTORE back to the owner keystore.

Prerequisites: a client whose key may register session keys, meaning the
owner wallet or a session key holding ADMIN or CREATE_SESSION_KEY.
Copy .env.template to .env first.

Run:
    python examples/02-session-keys.py
"""

import sys
import time
from pathlib import Path

import rich_click as click
from dotenv import set_key, unset_key
from eth_account import Account

from derive_py import HTTPClient
from derive_py.data_types import OffchainScope, ProtocolScope
from derive_py.keystore import create_keystore, keystore_password, load_keystore, resolve_keystore

LABEL = "example-session-key"
KEY_LIFETIME_SEC = 24 * 60 * 60  # the key's lifetime, not the signature's
RETIRE_AFTER_SEC = 360  # the server's 300s floor, plus slack for the round trip

SCOPES = [
    ProtocolScope.TRADE_ORDERBOOK_ALL,
    ProtocolScope.TRANSFER_EXISTING_SUBACCOUNT,
]

KEEP_LABEL = "examples"
KEEP_LIFETIME_SEC = 30 * 24 * 60 * 60
KEEP_SCOPES = [
    ProtocolScope.TRADE_ALL,
    ProtocolScope.TRANSFER_EXISTING_SUBACCOUNT,
]

ENV_FILE = Path.cwd() / ".env"

client = HTTPClient.from_env()
log = client.logger
if client._auth is None:
    raise SystemExit("This example needs a signer: run 01-deposit.py, or set DERIVE_KEYSTORE in .env.")


def log_key(heading: str, key) -> None:
    """One record, so the block stays intact under the log handler."""

    log.info(
        f"{heading}:\n"
        f"  public_session_key: {key.public_session_key}\n"
        f"  protocol_scopes:    {key.protocol_scopes}\n"
        f"  offchain_scopes:    {key.offchain_scopes}\n"
        f"  expiry_sec:         {key.expiry_sec}\n"
        f"  label:              {key.label}"
    )


if sys.stdin.isatty() and click.confirm("Register a session key to keep for the other examples?", default=False):
    keystore = resolve_keystore(KEEP_LABEL)
    if keystore.exists():
        kept = load_keystore(keystore, keystore_password(keystore))
        log.info(f"Refreshing the kept session key {kept.address} from {keystore}")
    else:
        kept = create_keystore(keystore, keystore_password(keystore, confirm=True))
        log.info(f"Created session key {kept.address}, encrypted in {keystore}")
    registered = client.account.set_session_key(
        expiry_sec=int(time.time()) + KEEP_LIFETIME_SEC,
        protocol_scopes=KEEP_SCOPES,
        offchain_scopes=[],
        public_session_key=kept.address,
        label=KEEP_LABEL,
    )
    log_key("Registered to keep", registered)
    wallet = client.account.address
    if click.confirm(
        f"In {ENV_FILE}, set DERIVE_KEYSTORE={KEEP_LABEL} and DERIVE_WALLET={wallet}, remove DERIVE_SESSION_KEY?"
    ):
        set_key(ENV_FILE, "DERIVE_KEYSTORE", KEEP_LABEL)
        set_key(ENV_FILE, "DERIVE_WALLET", wallet)
        unset_key(ENV_FILE, "DERIVE_SESSION_KEY")
        log.info(f"Updated {ENV_FILE}")
    raise SystemExit(0)


# -- Register, or refresh the one registered before ------------------------

existing = next((k for k in client.account.session_keys().public_session_keys if k.label == LABEL), None)

if existing is None:
    # Only the address is sent to Derive. The private key never leaves this
    # process, and no endpoint will hand it back.
    session_wallet = Account.create()
    public_session_key = session_wallet.address
    log.info(f"No key labelled '{LABEL}'. Registering one.")
    log.warning(f"Save this now, it is shown once: {session_wallet.key.hex()}")
else:
    public_session_key = existing.public_session_key
    log.info(f"Refreshing '{LABEL}' ({public_session_key}), current expiry {existing.expiry_sec}.")

# set_session_key also takes subaccount_ids, which confines the key to those
# subaccounts. Omitting it, as here, grants every subaccount the wallet owns.
registered = client.account.set_session_key(
    expiry_sec=int(time.time()) + KEY_LIFETIME_SEC,
    protocol_scopes=SCOPES,
    offchain_scopes=[],
    public_session_key=public_session_key,
    label=LABEL,
)
log_key("Registered" if existing is None else "Refreshed", registered)


# -- Edit the off-chain fields. No signature involved -----------------------

edited = client.account.edit_session_key(
    public_session_key=registered.public_session_key,
    ip_whitelist=["127.0.0.1"],
    label=LABEL,
    offchain_scopes=[OffchainScope.ACCOUNT_INFO],
)
log_key("Edited", edited)
log.info(f"  ip_whitelist: {edited.ip_whitelist}, registered_sec: {edited.registered_sec}")


# -- Retire it -------------------------------------------------------------
#
# A nearer expiry with no scopes. The floor is enforced server-side and cannot
# be shortened from here, so the entry stays listed until it lapses. The next
# run finds this same entry and reactivates it rather than minting another.

retired = client.account.set_session_key(
    expiry_sec=int(time.time()) + RETIRE_AFTER_SEC,
    protocol_scopes=[],
    offchain_scopes=[],
    public_session_key=registered.public_session_key,
    label=LABEL,
)
log_key("Retired", retired)
log.info(f"  usable for another {retired.expiry_sec - int(time.time())}s before it lapses")
