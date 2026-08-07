"""ABI encoding for each module data type.

Expected values in expected.py are captured from the corresponding *_debug
endpoint on testnet and frozen. Regenerate with:

    python -m scripts.get_test_data

Every non-vault encoder here was confirmed byte-identical to the server's,
including session key and whitelisted recipients, which are canonical
abi.encode with dynamic arrays.

The vault module has NO *_debug endpoint, so its six encoders are captured
differently, in three tiers:

  A. deposit, withdraw  - submitted for real. The request body carries no data
     bytes, so the server rebuilds the payload from the typed params in order
     to verify the signature, and returns its reconstruction as
     signed_action.action.data on private/get_live_vault_requests. Byte-
     comparing that is equivalent to a debug endpoint.
  B. cancel             - no data read-back, but the request history carries a
     user_action_hash. Verified to hash strength IF the hash convention
     discovered during the deposit round trip applies.
  C. create, mint, burn - no read-back at all. Locally computed from derive-ts
     codecs/vault.ts; acceptance by the live endpoint is the only other signal,
     and creating a vault costs $11k and can only be done once.

Vault cases cannot reuse the pinned NONCE and EXPIRY: vault nonces are accepted
only from 60 days before to 1 hour after the server clock, and vault expiries
are capped at 30 days. They sign with a live nonce and a bounded expiry
instead. Module data encoding is independent of both, and the envelope hashes
in expected.py are captured from the TRADE case only, so nothing is weakened.

Flags:
    --skip-vault      run only the debug-endpoint cases
    --vault-only      run only the vault cases (leaves other constants stale)
    --create-vault    create a vault if this wallet curates none. IRREVERSIBLE
                      and one-shot: a vault cannot be deleted, only wound down.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import requests
from web3 import Web3

from derive_client._clients.utils import load_client_config
from derive_client._web3.action_signing import (
    ModuleData,
    RFQExecuteModuleData,
    RFQQuoteDetails,
    RFQQuoteModuleData,
    SessionKeyModuleData,
    SignedAction,
    TradeModuleData,
    TransferSpotExternalModuleData,
    TransferSpotModuleData,
    VaultBurnSharesModuleData,
    VaultCancelModuleData,
    VaultCreateModuleData,
    VaultDepositModuleData,
    VaultMintSharesModuleData,
    VaultWithdrawModuleData,
    WhitelistedRecipientModuleData,
    WithdrawModuleData,
    get_action_nonce,
)
from derive_client._web3.action_signing.utils import sign_rest_auth_header
from derive_client.config.constants import PUBLIC_HEADERS
from derive_client.config.contracts import CONFIGS
from derive_client.data_types import ProtocolScope

EXPECTED_PATH = Path(__file__).parent.parent / "tests" / "test_action_signing" / "expected.py"

NONCE = 1754472862000000000
EXPIRY = 1893456000  # 2030-01-01, inside every documented maximum
OTHER_SUBACCOUNT_ID = 75726
RECIPIENT = "0x0000000000000000000000000000000000000001"
USDC_ASSET_NAME = "USDC"

# Vault inputs, pinned. The amounts are deliberately small: deposit and
# withdraw are submitted for real, and a deposit holds funds on the source
# subaccount until it is cancelled at the end of the run.
VAULT_AMOUNT = "10"
VAULT_SHARES_TO_BURN = "1"
VAULT_SHARE_PRICE = "1.02"
# Synthetic, not a real queued request's hash. The settle encoders take an
# opaque bytes32; using a live hash would make the constant unreproducible
# without adding anything to what the encoding test proves.
VAULT_USER_ACTION_HASH = "0x" + "d1" * 32
VAULT_MANAGER_ID = 1
VAULT_INITIAL_DEPOSIT = "15000"
VAULT_MANAGEMENT_FEE_BPS = 100
VAULT_PERFORMANCE_FEE_BPS = 1000
VAULT_MAX_SLIPPAGE_BPS = 50
VAULT_COOLDOWN_SEC = 86400
VAULT_MAX_FEE_USD = "1000"
VAULT_INITIAL_SHARE_PRICE_USD = "1"
#: Vault signatures are capped at 30 days out. Queued intents are settled at
#: the curator's discretion within a 14-day SLA, so a short expiry is how an
#: intent silently reaches `expired` instead of being settled.
VAULT_SIGNATURE_TTL_SEC = 7 * 24 * 3600

CONFIG_CLIENT = load_client_config()
CONFIG = CONFIGS[CONFIG_CLIENT.env]
WALLET = CONFIG_CLIENT.wallet
SUBACCOUNT_ID = CONFIG_CLIENT.subaccount_id
W3 = Web3()
SIGNER = W3.eth.account.from_key(CONFIG_CLIENT.session_key)

HEADER_TEMPLATE = '''"""Expected ABI encodings for the action-signing tests.

GENERATED FILE - do not edit by hand.
Regenerate with:  python -m scripts.get_test_data

Each value is the `encoded_data` the server returned for the inputs pinned in
that script, split one 32-byte word per line so a dropped character is visible.

EXPECTED_WHITELISTED_RECIPIENTS may be locally computed: that action has no
debug endpoint, so its only reference is derive-ts codecs/whitelistedRecipients.ts.

The vault module has no debug endpoint either. Of its six encodings, these were
verified against the server in this run:
{verified}
Every other EXPECTED_VAULT_* value below is locally computed from derive-ts
codecs/vault.ts and is pinned only against accidental change.
"""

'''


def post(path: str, payload: dict, *, private: bool = False) -> dict:
    headers = dict(PUBLIC_HEADERS)
    if private:
        headers |= sign_rest_auth_header(W3, WALLET, CONFIG_CLIENT.session_key)
    response = requests.post(f"{CONFIG.base_url}/{path}", json=payload, headers=headers, timeout=30)
    body = response.json()
    if "result" not in body:
        raise RuntimeError(f"{path} -> {json.dumps(body)}")
    return body["result"]


def pick(record: dict, *candidates: str) -> Any:
    """Field names are unconfirmed for v3; fail loudly with the real keys."""
    for name in candidates:
        if name in record:
            return record[name]
    raise KeyError(f"none of {candidates} in {sorted(record)}")


def discover() -> dict:
    """Fetch two live ETH options and USDC's spot asset.

    Options rather than perps: a perp's base_asset_sub_id is 0, which encodes as
    a zero word and would not prove sub_id reaches the encoding at all. The
    captured constants are frozen hex, so the option expiring costs nothing
    until the next recapture.
    """
    result = post(
        "public/get_all_instruments",
        {"instrument_type": "option", "currency": "ETH", "expired": False, "page": 1, "page_size": 100},
    )
    instruments = result["instruments"] if isinstance(result, dict) else result
    live = [i for i in instruments if i.get("is_active")]
    if len(live) < 2:
        raise RuntimeError(f"need two live ETH options, found {len(live)}")

    options = [
        {
            "name": pick(option, "instrument_name"),
            "address": pick(option, "base_asset_address"),
            "sub_id": int(pick(option, "base_asset_sub_id")),
        }
        for option in live[:2]
    ]

    currency = post("public/get_currency", {"currency": USDC_ASSET_NAME})
    spot = currency["spot"][0] if isinstance(currency.get("spot"), list) else currency["spot"]
    usdc = {
        "address": pick(spot, "address"),
        "sub_id": int(spot.get("sub_id", 0)),
        "decimals": int(pick(spot["erc20"], "decimals")),
    }
    return {"options": options, "usdc": usdc}


@dataclass
class Case:
    name: str
    endpoint: str
    module_data: ModuleData
    module_address: str
    private: bool = False
    extra: dict = field(default_factory=dict)
    subaccount_id: int | None = None


def build_cases(found: dict) -> list[Case]:
    option_a, option_b = found["options"]
    usdc = found["usdc"]
    contracts = CONFIG.contracts

    def legs(directions):
        details = [
            RFQQuoteDetails(
                instrument_name=option["name"],
                direction=direction,
                asset_address=option["address"],
                sub_id=option["sub_id"],
                price=price,
                amount=amount,
            )
            for option, direction, price, amount in (
                (option_a, directions[0], Decimal("50"), Decimal("1")),
                (option_b, directions[1], Decimal("100"), Decimal("2")),
            )
        ]
        return sorted(details, key=lambda leg: leg.instrument_name)

    return [
        Case(
            name="TRADE",
            endpoint="private/order_debug",
            private=True,
            module_address=contracts.TRADE_MODULE,
            module_data=TradeModuleData(
                asset_address=option_a["address"],
                sub_id=option_a["sub_id"],
                limit_price=Decimal("100"),
                amount=Decimal("1"),
                max_fee=Decimal("1000"),
                recipient_id=SUBACCOUNT_ID,
                is_bid=True,
            ),
            extra={
                "instrument_name": option_a["name"],
                "direction": "buy",
                "order_type": "limit",
                "time_in_force": "gtc",
                "mmp": False,
            },
        ),
        Case(
            name="RFQ_QUOTE",
            endpoint="public/send_quote_debug",
            module_address=contracts.RFQ_MODULE,
            module_data=RFQQuoteModuleData(
                global_direction="sell",
                max_fee=Decimal("1000"),
                legs=legs(("buy", "buy")),
            ),
            extra={"label": "", "mmp": False, "rfq_id": "00000000-0000-4000-8000-000000000001"},
        ),
        Case(
            name="RFQ_EXECUTE",
            endpoint="public/execute_quote_debug",
            module_address=contracts.RFQ_MODULE,
            module_data=RFQExecuteModuleData(
                global_direction="sell",
                max_fee=Decimal("1000"),
                legs=legs(("sell", "buy")),
            ),
            extra={
                "label": "",
                "rfq_id": "00000000-0000-4000-8000-000000000001",
                "quote_id": "00000000-0000-4000-8000-000000000002",
            },
        ),
        Case(
            name="WITHDRAW",
            endpoint="public/withdraw_debug",
            module_address=contracts.WITHDRAW_MODULE,
            module_data=WithdrawModuleData(
                protocol_asset=usdc["address"],
                asset_name=USDC_ASSET_NAME,
                max_fee_usd=Decimal("1.5"),
                # The exchange only constructs withdrawals paying out to the
                # action signer; any other recipient is silently replaced.
                recipient=WALLET,
                amount=Decimal("10"),
                decimals=usdc["decimals"],
                force_batch=False,
            ),
        ),
        Case(
            name="TRANSFER_SPOT",
            endpoint="private/transfer_spot_debug",
            private=True,
            module_address=contracts.TRANSFER_MODULE,
            module_data=TransferSpotModuleData(
                to_subaccount_id=OTHER_SUBACCOUNT_ID,
                new_subaccount_manager=0,
                asset=usdc["address"],
                asset_name=USDC_ASSET_NAME,
                sub_id=usdc["sub_id"],
                amount=Decimal("10"),
                max_fee_usd=Decimal("1.5"),
            ),
        ),
        Case(
            name="TRANSFER_SPOT_EXTERNAL",
            endpoint="private/transfer_spot_external_debug",
            private=True,
            module_address=contracts.EXTERNAL_TRANSFER_MODULE,
            module_data=TransferSpotExternalModuleData(
                to_subaccount_id=0,
                new_subaccount_manager=1,
                asset=usdc["address"],
                asset_name=USDC_ASSET_NAME,
                sub_id=usdc["sub_id"],
                amount=Decimal("10"),
                max_fee_usd=Decimal("1.5"),
                recipient=RECIPIENT,
            ),
        ),
        Case(
            name="SESSION_KEY",
            endpoint="private/set_session_key_debug",
            private=True,
            subaccount_id=0,  # session-key actions sign against subaccount 0
            module_address=contracts.CREATE_SESSION_KEY_MODULE,
            module_data=SessionKeyModuleData(
                session_key=RECIPIENT,
                expiry_sec=EXPIRY,
                protocol_scopes=[ProtocolScope.WITHDRAW],
                subaccount_ids=[],
            ),
        ),
        Case(
            name="WHITELISTED_RECIPIENTS",
            endpoint="private/update_whitelisted_recipients_debug",
            private=True,
            module_address=contracts.WHITELISTED_RECIPIENT_MODULE,
            module_data=WhitelistedRecipientModuleData(add=[RECIPIENT], remove=[]),
        ),
    ]


def run(case: Case) -> dict[str, str]:
    action = SignedAction(
        subaccount_id=SUBACCOUNT_ID if case.subaccount_id is None else case.subaccount_id,
        owner=WALLET,
        signer=SIGNER.address,
        signature_expiry_sec=EXPIRY,
        nonce=NONCE,
        module_address=case.module_address,
        module_data=case.module_data,
        DOMAIN_SEPARATOR=CONFIG.DOMAIN_SEPARATOR,
        ACTION_TYPEHASH=CONFIG.ACTION_TYPEHASH,
    )
    action.sign(SIGNER.key)
    local = "0x" + case.module_data.to_abi_encoded().hex()

    try:
        result = post(case.endpoint, {**action.to_json(), **case.extra}, private=case.private)
    except Exception as error:
        raise RuntimeError(f"{case.endpoint} -> {error}") from error

    if local != result["encoded_data"]:
        raise RuntimeError(f"encoder disagrees with the server\n  local  {local}\n  server {result['encoded_data']}")

    captured = {f"EXPECTED_{case.name}": result["encoded_data"]}
    if case.name == "TRADE":
        # The envelope hashes are captured once, from the trade action only.
        captured["EXPECTED_ACTION_HASH"] = result["action_hash"]
        captured["EXPECTED_TYPED_DATA_HASH"] = result["typed_data_hash"]
        captured["EXPECTED_SIGNATURE"] = action.signature
        server_typehash = result.get("action_typehash")
        if server_typehash not in (None, CONFIG.ACTION_TYPEHASH):
            raise RuntimeError(f"ACTION_TYPEHASH differs: config {CONFIG.ACTION_TYPEHASH}, server {server_typehash}")
    return captured


# ---------------------------------------------------------------------------
# Vault
# ---------------------------------------------------------------------------


def sign_vault(module_data: ModuleData, subaccount_id: int) -> SignedAction:
    """Sign a vault action with a live nonce and a bounded expiry.

    The pinned NONCE and EXPIRY are outside the vault windows (60 days before
    to 1 hour after the clock, and 30 days respectively), and a vault nonce must
    strictly increase per subaccount. Neither field reaches the module data, so
    the captured encodings are unaffected.
    """

    action = SignedAction(
        subaccount_id=subaccount_id,
        owner=WALLET,
        signer=SIGNER.address,
        signature_expiry_sec=int(time.time()) + VAULT_SIGNATURE_TTL_SEC,
        nonce=get_action_nonce(),
        module_address=CONFIG.contracts.VAULT_MODULE,
        module_data=module_data,
        DOMAIN_SEPARATOR=CONFIG.DOMAIN_SEPARATOR,
        ACTION_TYPEHASH=CONFIG.ACTION_TYPEHASH,
    )
    action.sign(SIGNER.key)
    return action


def check_vault_scopes(*, need_curator: bool) -> None:
    """A missing scope fails at the server with a permission error that reads
    nothing like a signature mismatch, which is exactly what this script exists
    to detect."""

    keys = post("private/session_keys", {"wallet": WALLET}, private=True)
    registered = {key["public_session_key"]: key for key in keys["public_session_keys"]}
    key = registered.get(SIGNER.address)
    if key is None:
        print(f"  warn  signer {SIGNER.address} is not a registered session key")
        return

    scopes = set(key.get("protocol_scopes") or [])
    required = {ProtocolScope.VAULT_USER_DEPOSIT, ProtocolScope.VAULT_USER_WITHDRAW, ProtocolScope.VAULT_USER_CANCEL}
    if need_curator:
        required |= {ProtocolScope.VAULT_CURATOR_CREATE, ProtocolScope.VAULT_CURATOR_MINT_AND_BURN}

    covered = {ProtocolScope.ADMIN, ProtocolScope.VAULT_ALL} & scopes
    missing = sorted(str(scope) for scope in required if str(scope) not in scopes) if not covered else []
    if missing:
        print(f"  warn  session key is missing vault scopes: {', '.join(missing)}")


def discover_vault(*, allow_create: bool) -> dict | None:
    """Find a vault to exercise the shareholder tier against.

    Curated first: a curator may also hold shares in their own vault, and only a
    curated vault can exercise mint and burn later. Otherwise any public vault
    that is not whitelist-only will do for deposit, withdraw and cancel.
    """

    curated = post("private/get_curated_vaults", {"wallet": WALLET}, private=True)["subaccount_ids"]
    if curated:
        vault = post("public/get_vault", {"subaccount_id": curated[0]})
        print(f"  curating vault {curated[0]} ({vault['name']})")
        return vault

    listed = post("public/get_vaults", {"page": 1, "page_size": 50})["vaults"]
    open_vaults = [v for v in listed if not v["whitelist_only"] and not v["protocol"]["closed"]]
    if open_vaults:
        vault = open_vaults[0]
        print(f"  using public vault {vault['protocol']['subaccount_id']} ({vault['name']}), not curated by us")
        return vault

    print(f"  no usable vault found ({len(listed)} listed, none open)")
    if not allow_create:
        print("  rerun with --create-vault to create one (irreversible, one-shot, ~$11k)")
        return None
    return create_vault()


def create_vault() -> dict | None:
    """Create a vault. There is no delete: a vault only ever winds down.

    The new subaccount id is not returned, so it is resolved by diffing the
    curated set. Racy if this wallet creates two vaults concurrently, which is
    not a situation this script should ever be in.
    """

    usdc = post("public/get_currency", {"currency": USDC_ASSET_NAME})
    spot = usdc["spot"][0] if isinstance(usdc.get("spot"), list) else usdc["spot"]
    before = set(post("private/get_curated_vaults", {"wallet": WALLET}, private=True)["subaccount_ids"])

    module_data = VaultCreateModuleData(
        manager_id=VAULT_MANAGER_ID,
        deposit_spot_asset=pick(spot, "address"),
        initial_deposit=Decimal(VAULT_INITIAL_DEPOSIT),
        management_fee_bps=VAULT_MANAGEMENT_FEE_BPS,
        performance_fee_bps=VAULT_PERFORMANCE_FEE_BPS,
        max_slippage_bps=VAULT_MAX_SLIPPAGE_BPS,
        cooldown_sec=VAULT_COOLDOWN_SEC,
        max_fee_usd=Decimal(VAULT_MAX_FEE_USD),
        initial_share_price_usd=Decimal(VAULT_INITIAL_SHARE_PRICE_USD),
        benchmark_asset=None,
    )
    action = sign_vault(module_data, SUBACCOUNT_ID)
    result = post("private/create_vault", action.to_json(), private=True)
    print(f"  create_vault accepted, op_uuid {result['op_uuid']}")

    deadline = time.time() + 300
    while time.time() < deadline:
        time.sleep(5)
        after = set(post("private/get_curated_vaults", {"wallet": WALLET}, private=True)["subaccount_ids"])
        if new := sorted(after - before):
            print(f"  vault created: subaccount {new[0]}")
            return post("public/get_vault", {"subaccount_id": new[0]})
    raise RuntimeError(f"create_vault op {result['op_uuid']} did not surface a new curated vault within 300s")


def identify_hash_convention(action: SignedAction, module_data: ModuleData, user_action_hash: str) -> str:
    """Determine what the server means by user_action_hash.

    Mint and burn are bound to a queued request by this hash, so getting the
    convention wrong produces a valid signature that settles nothing. Nothing
    documents which of the three it is, and one deposit round trip answers it.
    """

    candidates = {
        "keccak(module_data)": Web3.keccak(module_data.to_abi_encoded()).to_0x_hex(),
        "action_hash": action._get_action_hash().to_0x_hex(),
        "typed_data_hash": action._to_typed_data_hash().to_0x_hex(),
    }
    for name, value in candidates.items():
        if value.lower() == user_action_hash.lower():
            print(f"  user_action_hash is {name}")
            return name
    raise RuntimeError(
        "user_action_hash matches none of the candidates; mint/burn cannot be bound correctly\n"
        f"  server {user_action_hash}\n" + "\n".join(f"  {n:22} {v}" for n, v in candidates.items())
    )


def find_live_request(request_id: dict) -> dict:
    live = post("private/get_live_vault_requests", {"wallet": WALLET}, private=True)
    for row in live["requests"]:
        if row["id"] == request_id:
            return row
    raise RuntimeError(f"queued request {request_id} not in the live queue ({live['total']} entries)")


def submit_and_read_back(name: str, endpoint: str, module_data: ModuleData) -> tuple[str, SignedAction, dict]:
    """Submit a shareholder intent and byte-compare the server's rebuild.

    The request body carries only typed params, so the data returned here is the
    server's own reconstruction, not an echo of ours.
    """

    action = sign_vault(module_data, SUBACCOUNT_ID)
    ack = post(endpoint, action.to_json(), private=True)
    row = find_live_request(ack["request_id"])

    server = "0x" + bytes(row["signed_action"]["action"]["data"]).hex()
    local = "0x" + module_data.to_abi_encoded().hex()
    if local != server:
        raise RuntimeError(f"{name} encoder disagrees with the server\n  local  {local}\n  server {server}")
    return server, action, row


def cancel_all(vault_subaccount_id: int) -> tuple[VaultCancelModuleData, SignedAction, dict]:
    """Drain every intent this run queued. Also the cancel encoder's only live
    exercise: there is no cancel-one, and no data read-back for it."""

    module_data = VaultCancelModuleData(vault_subaccount_id=vault_subaccount_id)
    action = sign_vault(module_data, SUBACCOUNT_ID)
    result = post("private/cancel_all_vault_requests", action.to_json(), private=True)
    return module_data, action, result


def verify_cancel_hash(action: SignedAction, module_data: ModuleData, convention: str) -> bool:
    """Best effort: match the cancel in the request history and compare hashes.

    It is not documented whether a cancel row's vault_nonce is the cancel's own
    nonce or the cancelled request's, so a miss here is reported, not fatal.
    """

    history = post("private/get_vault_request_history", {"wallet": WALLET, "page": 1, "page_size": 50}, private=True)
    expected = {
        "keccak(module_data)": Web3.keccak(module_data.to_abi_encoded()).to_0x_hex(),
        "action_hash": action._get_action_hash().to_0x_hex(),
        "typed_data_hash": action._to_typed_data_hash().to_0x_hex(),
    }[convention]
    for row in history["actions"]:
        if row.get("user_action_hash", "").lower() == expected.lower():
            print(f"  cancel verified to hash strength (event_type={row.get('event_type')})")
            return True
    print("  cancel not matched in the request history; encoding stays locally computed")
    return False


def run_vault(*, allow_create: bool) -> tuple[dict[str, Any], set[str]]:
    """Capture the six vault encodings. Returns (constants, server-verified names)."""

    check_vault_scopes(need_curator=allow_create)
    vault = discover_vault(allow_create=allow_create)

    if vault is None:
        usdc = post("public/get_currency", {"currency": USDC_ASSET_NAME})
        spot = usdc["spot"][0] if isinstance(usdc.get("spot"), list) else usdc["spot"]
        vault_subaccount_id, deposit_asset = 0, pick(spot, "address")
        print("  vault tier is locally computed only")
    else:
        vault_subaccount_id = vault["protocol"]["subaccount_id"]
        deposit_asset = vault["protocol"]["config"]["deposit_spot_asset"]

    create = VaultCreateModuleData(
        manager_id=VAULT_MANAGER_ID,
        deposit_spot_asset=deposit_asset,
        initial_deposit=Decimal(VAULT_INITIAL_DEPOSIT),
        management_fee_bps=VAULT_MANAGEMENT_FEE_BPS,
        performance_fee_bps=VAULT_PERFORMANCE_FEE_BPS,
        max_slippage_bps=VAULT_MAX_SLIPPAGE_BPS,
        cooldown_sec=VAULT_COOLDOWN_SEC,
        max_fee_usd=Decimal(VAULT_MAX_FEE_USD),
        initial_share_price_usd=Decimal(VAULT_INITIAL_SHARE_PRICE_USD),
        # Set, not omitted, so the captured constant exercises the non-trivial
        # has_benchmark branch; the omitted branch is covered structurally in
        # tests/test_action_signing/test_module_data.py.
        benchmark_asset=deposit_asset,
    )
    deposit = VaultDepositModuleData(
        vault_subaccount_id=vault_subaccount_id,
        deposit_spot_asset=deposit_asset,
        amount=Decimal(VAULT_AMOUNT),
    )
    withdraw = VaultWithdrawModuleData(
        vault_subaccount_id=vault_subaccount_id,
        shares_to_burn=Decimal(VAULT_SHARES_TO_BURN),
    )
    cancel = VaultCancelModuleData(vault_subaccount_id=vault_subaccount_id)
    mint = VaultMintSharesModuleData(share_price=Decimal(VAULT_SHARE_PRICE), user_action_hash=VAULT_USER_ACTION_HASH)
    burn = VaultBurnSharesModuleData(share_price=Decimal(VAULT_SHARE_PRICE), user_action_hash=VAULT_USER_ACTION_HASH)

    captured = {
        "VAULT_SUBACCOUNT_ID": vault_subaccount_id,
        "VAULT_DEPOSIT_ASSET": deposit_asset,
        "VAULT_BENCHMARK_ASSET": deposit_asset,
        "VAULT_MANAGER_ID": VAULT_MANAGER_ID,
        "VAULT_AMOUNT": VAULT_AMOUNT,
        "VAULT_SHARES_TO_BURN": VAULT_SHARES_TO_BURN,
        "VAULT_SHARE_PRICE": VAULT_SHARE_PRICE,
        "VAULT_USER_ACTION_HASH": VAULT_USER_ACTION_HASH,
        "VAULT_INITIAL_DEPOSIT": VAULT_INITIAL_DEPOSIT,
        "VAULT_MANAGEMENT_FEE_BPS": VAULT_MANAGEMENT_FEE_BPS,
        "VAULT_PERFORMANCE_FEE_BPS": VAULT_PERFORMANCE_FEE_BPS,
        "VAULT_MAX_SLIPPAGE_BPS": VAULT_MAX_SLIPPAGE_BPS,
        "VAULT_COOLDOWN_SEC": VAULT_COOLDOWN_SEC,
        "VAULT_MAX_FEE_USD": VAULT_MAX_FEE_USD,
        "VAULT_INITIAL_SHARE_PRICE_USD": VAULT_INITIAL_SHARE_PRICE_USD,
        "EXPECTED_VAULT_CREATE": "0x" + create.to_abi_encoded().hex(),
        "EXPECTED_VAULT_DEPOSIT": "0x" + deposit.to_abi_encoded().hex(),
        "EXPECTED_VAULT_WITHDRAW": "0x" + withdraw.to_abi_encoded().hex(),
        "EXPECTED_VAULT_CANCEL": "0x" + cancel.to_abi_encoded().hex(),
        "EXPECTED_VAULT_MINT_SHARES": "0x" + mint.to_abi_encoded().hex(),
        "EXPECTED_VAULT_BURN_SHARES": "0x" + burn.to_abi_encoded().hex(),
    }
    verified: set[str] = set()
    if vault is None:
        return captured, verified

    convention = None
    try:
        server, action, row = submit_and_read_back("DEPOSIT", "private/request_vault_deposit", deposit)
        captured["EXPECTED_VAULT_DEPOSIT"] = server
        verified.add("EXPECTED_VAULT_DEPOSIT")
        convention = identify_hash_convention(action, deposit, row["user_action_hash"])
        print("  ok    VAULT_DEPOSIT (server rebuild)")
    except Exception as error:
        print(f"  FAIL  VAULT_DEPOSIT: {error}")

    try:
        server, _, _ = submit_and_read_back("WITHDRAW", "private/request_vault_withdraw", withdraw)
        captured["EXPECTED_VAULT_WITHDRAW"] = server
        verified.add("EXPECTED_VAULT_WITHDRAW")
        print("  ok    VAULT_WITHDRAW (server rebuild)")
    except Exception as error:
        # Expected when this wallet holds no shares in the vault, or while the
        # deposit cooldown is still running.
        print(f"  skip  VAULT_WITHDRAW, stays locally computed: {error}")

    try:
        module_data, action, _ = cancel_all(vault_subaccount_id)
        print("  ok    cancelled every intent this run queued")
        if convention and verify_cancel_hash(action, module_data, convention):
            verified.add("EXPECTED_VAULT_CANCEL")
    except Exception as error:
        print(f"  FAIL  cleanup cancel_all_vault_requests: {error}")
        print("        intents may still be holding funds; cancel them manually")

    return captured, verified


def format_constant(name: str, value: str | int) -> str:
    """Hex split at 32-byte boundaries, one word per line.

    ABI data divides evenly. A 65-byte signature leaves a 2-char remainder,
    which lands on its own line as the v byte -- r, s, v.
    """
    if isinstance(value, int):
        return f"{name} = {value}"
    body = value.removeprefix("0x")
    if len(body) <= 64 or any(c not in "0123456789abcdefABCDEF" for c in body):
        return f'{name} = "{value}"'
    prefix = "0x" if value.startswith("0x") else ""
    words = [body[i : i + 64] for i in range(0, len(body), 64)]
    lines = [f'    "{prefix}{words[0]}"'] + [f'    "{word}"' for word in words[1:]]
    return f"{name} = (\n" + "\n".join(lines) + "\n)"


def write_expected(found: dict, captured: dict[str, Any], verified: set[str]) -> None:
    option_a, option_b = found["options"]
    usdc = found["usdc"]
    constants = {
        "OPTION_A_NAME": option_a["name"],
        "OPTION_A_ADDRESS": option_a["address"],
        "OPTION_A_SUB_ID": option_a["sub_id"],
        "OPTION_B_NAME": option_b["name"],
        "OPTION_B_ADDRESS": option_b["address"],
        "OPTION_B_SUB_ID": option_b["sub_id"],
        "USDC_ASSET_NAME": USDC_ASSET_NAME,
        "USDC_ADDRESS": usdc["address"],
        "USDC_SUB_ID": usdc["sub_id"],
        "USDC_DECIMALS": usdc["decimals"],
        "SIGNER_ADDRESS": SIGNER.address,
        "OWNER_ADDRESS": WALLET,
        "SUBACCOUNT_ID": SUBACCOUNT_ID,
        "OTHER_SUBACCOUNT_ID": OTHER_SUBACCOUNT_ID,
        "NONCE": NONCE,
        "EXPIRY": EXPIRY,
        "RECIPIENT": RECIPIENT,
        **captured,
    }
    listed = "\n".join(f"  {name}" for name in sorted(verified)) or "  (none)"
    header = HEADER_TEMPLATE.format(verified=listed)
    blocks = [format_constant(name, value) for name, value in constants.items()]
    EXPECTED_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPECTED_PATH.write_text(header + "\n\n".join(blocks) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-vault", action="store_true", help="run only the debug-endpoint cases")
    parser.add_argument("--vault-only", action="store_true", help="run only the vault cases")
    parser.add_argument(
        "--create-vault",
        action="store_true",
        help="create a vault if this wallet curates none. Irreversible and one-shot.",
    )
    args = parser.parse_args()
    if args.skip_vault and args.vault_only:
        parser.error("--skip-vault and --vault-only are mutually exclusive")

    print(f"environment: {CONFIG_CLIENT.env.name}")
    print(f"owner:       {WALLET}")
    print(f"signer:      {SIGNER.address}")
    print(f"subaccount:  {SUBACCOUNT_ID}\n")

    found = discover()

    captured: dict[str, Any] = {}
    verified: set[str] = set()
    failures: list[str] = []

    if not args.vault_only:
        for case in build_cases(found):
            try:
                captured |= run(case)
                verified.add(f"EXPECTED_{case.name}")
                print(f"  ok    {case.name}")
            except Exception as error:  # noqa: BLE001 - report every case, abort on none
                failures.append(f"{case.name}: {error}")
                print(f"  FAIL  {case.name}")

    if not args.skip_vault:
        print("\nvault (no debug endpoint; see module docstring for what each tier proves):")
        try:
            vault_captured, vault_verified = run_vault(allow_create=args.create_vault)
            captured |= vault_captured
            verified |= vault_verified
        except Exception as error:  # noqa: BLE001
            failures.append(f"VAULT: {error}")
            print(f"  FAIL  VAULT: {error}")

    if failures:
        print("\nfailures:")
        for failure in failures:
            print(f"  {failure}")
        print("\nnot writing expected.py while any case fails")
        raise SystemExit(1)

    if args.vault_only:
        print("\n--vault-only leaves every non-vault constant stale; not writing expected.py")
        raise SystemExit(0)

    write_expected(found, captured, verified)
    print(f"\nwrote {EXPECTED_PATH}")


if __name__ == "__main__":
    main()
