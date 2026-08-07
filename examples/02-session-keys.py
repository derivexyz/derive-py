"""
Session keys: register a scoped, expiring key, edit its off-chain fields,
then retire it.

Two separate mechanisms, not one general-purpose "update":

  set_session_key  -- signed by the OWNER wallet (no session key can register
                      another). Sets BOTH protocol_scopes (on-chain, signed
                      into the payload) and offchain_scopes (server-side
                      only). The same call registers, refreshes, OR retires a
                      key: retiring means writing a nearer expiry with empty
                      scope lists. There is no delete endpoint, and
                      expiry_sec=0 is rejected -- the API enforces a floor of
                      300s from now (error 14039), so a retired key stays
                      listed until that lapses. Only the L1 SetSessionKey
                      action deletes outright.
  edit_session_key -- no signing at all. Off-chain fields only (label,
                      ip_whitelist, offchain_scopes); protocol_scopes cannot
                      be touched here. To change on-chain authority, call
                      set_session_key again.

Because keys are never deleted, a fresh keypair per run would leave a growing
list of expired entries on the account. So this example registers one key the
first time and REFRESHES that same one on every later run -- reactivating a
retired key by writing a new expiry and scopes back onto it. One entry, no
accumulation.

The trade-off: Derive only ever returns a key's ADDRESS, never its private
key. On a refresh run this example therefore cannot show you the secret the
bot would sign with -- it exists only in the output of the run that first
registered the key. Delete that entry from the account (or change LABEL) if
you have lost it and need a new one.

Prerequisites: a client configured with the OWNER wallet's key, not a session
key -- set_session_key rejects anything else.

Run:
    python examples/02-session-keys.py
"""

import time
from pathlib import Path

from eth_account import Account

from derive_client import HTTPClient
from derive_client.data_types import OffchainScope, ProtocolScope

LABEL = "example-session-key"
KEY_LIFETIME_SEC = 24 * 60 * 60  # the KEY's lifetime, not the signature's
RETIRE_EXPIRY_MARGIN_SEC = 360  # the 300s floor plus slack for the round trip

SCOPES = [
    ProtocolScope.TRADE_ORDERBOOK_ALL,
    ProtocolScope.TRANSFER_EXISTING_SUBACCOUNT,
]

env_file = Path(__file__).parent.parent / ".env.template"
client = HTTPClient.from_env(env_file=env_file)


def print_key(heading: str, key) -> None:
    print(f"{heading}:")
    print(f"  public_session_key: {key.public_session_key}")
    print(f"  protocol_scopes:    {key.protocol_scopes}")
    print(f"  offchain_scopes:    {key.offchain_scopes}")
    print(f"  expiry_sec:         {key.expiry_sec}")
    print(f"  label:              {key.label}")


def find_existing(label_prefix: str):
    """The key this example registered on a previous run, expired or not."""

    keys = client.account.session_keys().public_session_keys
    return next((key for key in keys if key.label.startswith(label_prefix)), None)


# -- Register, or refresh the one we registered before ---------------------

existing = find_existing(LABEL)

if existing is None:
    # Only the ADDRESS goes to Derive. The private key is yours alone: store
    # it, it is what the bot signs with, and it is never recoverable from the
    # API.
    session_wallet = Account.create()
    public_session_key = session_wallet.address
    print(f"No existing '{LABEL}' found -- registering a new one.")
else:
    session_wallet = None
    public_session_key = existing.public_session_key
    print(f"Reusing '{existing.label}' ({public_session_key}), expiry {existing.expiry_sec}.")

registered = client.account.set_session_key(
    expiry_sec=int(time.time()) + KEY_LIFETIME_SEC,
    protocol_scopes=SCOPES,
    offchain_scopes=[],
    public_session_key=public_session_key,
    label=LABEL,
)
print_key("Registered" if existing is None else "Refreshed", registered)

if session_wallet is not None:
    print(f"  private key (save this -- the API will never return it): {session_wallet.key.hex()}")


# -- Edit the off-chain fields. No signature involved -----------------------

edited = client.account.edit_session_key(
    public_session_key=registered.public_session_key,
    ip_whitelist=["127.0.0.1"],
    label=LABEL,
    offchain_scopes=[OffchainScope.ACCOUNT_INFO],
)
print_key("Edited", edited)
print(f"  ip_whitelist:       {edited.ip_whitelist}")
print(f"  registered_sec:     {edited.registered_sec}")


# -- Retire it -------------------------------------------------------------
#
# Writing a nearer expiry with no scopes. The key keeps working until that
# expiry lapses; the floor is enforced server-side and cannot be shortened
# from here. The next run of this example finds this same entry and
# reactivates it rather than minting another.

retired = client.account.set_session_key(
    expiry_sec=int(time.time()) + RETIRE_EXPIRY_MARGIN_SEC,
    protocol_scopes=[],
    offchain_scopes=[],
    public_session_key=registered.public_session_key,
    label=LABEL,
)
print_key("Retired", retired)
print(f"  still usable for {retired.expiry_sec - int(time.time())}s before it lapses")
