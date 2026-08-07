"""ABI encoding for each module data type.

Expected values in expected.py are captured from the corresponding *_debug
endpoint on testnet and frozen. Regenerate with:

    python -m scripts.get_test_data

Every encoder here was confirmed byte-identical to the server's, including
session key and whitelisted recipients, which are canonical abi.encode with
dynamic arrays.
"""

from __future__ import annotations

import json
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
    WhitelistedRecipientModuleData,
    WithdrawModuleData,
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

CONFIG_CLIENT = load_client_config()
CONFIG = CONFIGS[CONFIG_CLIENT.env]
WALLET = CONFIG_CLIENT.wallet
SUBACCOUNT_ID = CONFIG_CLIENT.subaccount_id
W3 = Web3()
SIGNER = W3.eth.account.from_key(CONFIG_CLIENT.session_key)

HEADER = '''"""Expected ABI encodings for the action-signing tests.

GENERATED FILE - do not edit by hand.
Regenerate with:  python -m scripts.get_test_data

Each value is the `encoded_data` the server returned for the inputs pinned in
that script, split one 32-byte word per line so a dropped character is visible.

EXPECTED_WHITELISTED_RECIPIENTS may be locally computed: that action has no
debug endpoint, so its only reference is derive-ts codecs/whitelistedRecipients.ts.
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


def write_expected(found: dict, captured: dict[str, str]) -> None:
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
    blocks = [format_constant(name, value) for name, value in constants.items()]
    EXPECTED_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPECTED_PATH.write_text(HEADER + "\n\n".join(blocks) + "\n")


def main() -> None:
    print(f"environment: {CONFIG_CLIENT.env.name}")
    print(f"owner:       {WALLET}")
    print(f"signer:      {SIGNER.address}")
    print(f"subaccount:  {SUBACCOUNT_ID}\n")

    found = discover()

    captured: dict[str, str] = {}
    failures: list[str] = []
    for case in build_cases(found):
        try:
            captured |= run(case)
            print(f"  ok    {case.name}")
        except Exception as error:  # noqa: BLE001 - report every case, abort on none
            failures.append(f"{case.name}: {error}")
            print(f"  FAIL  {case.name}")

    if failures:
        print("\nfailures:")
        for failure in failures:
            print(f"  {failure}")
        print("\nnot writing expected.py while any case fails")
        raise SystemExit(1)

    write_expected(found, captured)
    print(f"\nwrote {EXPECTED_PATH}")


if __name__ == "__main__":
    main()
