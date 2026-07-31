"""
Session keys: mint a scoped, expiring key, edit its off-chain fields,
then retire it.

Mirrors derive-ts's examples/02-session-keys.ts. Two separate mechanisms,
not one general-purpose "update":

  create_session_key -- signed by the OWNER wallet (no session key can
                         create another; there's no exception for "not the
                         first key"). Sets BOTH protocol_scopes (on-chain,
                         signed into the payload) and offchain_scopes
                         (server-side only) -- and this is also how you
                         RETIRE a key: call it again for the same
                         public_session_key with expiry_sec=0 and empty
                         scope lists. There's no separate delete endpoint.
  edit_session_key  -- no signing at all. Off-chain fields only (label,
                         ip_whitelist, offchain_scopes) -- protocol_scopes
                         can't be touched here; to change on-chain authority
                         you create a new key instead.

Prerequisites: a client configured with the OWNER wallet's key, not a
session key -- create_session_key rejects anything else.

Run:
    python examples/02-session-keys.py
"""

import time
from pathlib import Path

from eth_account import Account

from derive_client import HTTPClient
from derive_client.data_types import OffchainScope, ProtocolScope

env_file = Path(__file__).parent.parent / ".env.template"
client = HTTPClient.from_env(env_file=env_file)


def print_key(label: str, key) -> None:
    print(f"{label}:")
    print(f"  public_session_key: {key.public_session_key}")
    print(f"  protocol_scopes:    {key.protocol_scopes}")
    print(f"  offchain_scopes:    {key.offchain_scopes}")
    print(f"  expiry_sec:         {key.expiry_sec}")
    print(f"  label:              {key.label}")


# A brand-new keypair for the bot. Only its ADDRESS goes to Derive.
# Store the private key, it's what the bot signs with from now on.
session_wallet = Account.create()

created = client.account.create_session_key(
    expiry_sec=int(time.time()) + 24 * 60 * 60,  # the KEY's lifetime: 24h
    protocol_scopes=[ProtocolScope.TRADE_ALL],
    offchain_scopes=[],
    public_session_key=session_wallet.address,
    label="example-session-key",
)
print_key("Created", created)
print(f"  private key (save this -- it won't be shown again): {session_wallet.key.hex()}")

edited = client.account.edit_session_key(
    public_session_key=created.public_session_key,
    ip_whitelist=["127.0.0.1"],
    label="example-session-key-edited",
    offchain_scopes=[OffchainScope.ACCOUNT_INFO],
)
print_key("Edited", edited)
print(f"  ip_whitelist:       {edited.ip_whitelist}")
print(f"  registered_sec:     {edited.registered_sec}")

# Retiring the session key by setting expiry_sec=0 and empty scopes. The key is now dead.
retired = client.account.create_session_key(
    expiry_sec=0,
    protocol_scopes=[],
    offchain_scopes=[],
    public_session_key=session_wallet.address,
    label="example-session-key-retired",
)
print_key("Retired", retired)
