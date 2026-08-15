"""Tests for the SignedAction envelope.

The action below is byte-identical to the TRADE case in
scripts/get_test_data.py, so the hashes and signature in expected.py are the
ones private/order_debug returned for it. Regenerate with:

    python -m scripts.get_test_data

The tests that assert a field *changes* the hash need no captured value; they
catch a field being dropped from the encoding, which has no other symptom.
"""

from dataclasses import replace
from decimal import Decimal

import pytest
from web3 import Account

from derive_py._web3.action_signing import SignedAction, TradeModuleData
from derive_py.config.contracts import CONFIGS
from derive_py.data_types import Environment
from tests.conftest import env_template_value

from . import expected
from .expected import (
    EXPECTED_ACTION_HASH,
    EXPECTED_SIGNATURE,
    EXPECTED_TYPED_DATA_HASH,
    EXPIRY,
    NONCE,
    OPTION_A_ADDRESS,
    OPTION_A_SUB_ID,
    OWNER_ADDRESS,
    SIGNER_ADDRESS,
    SUBACCOUNT_ID,
)

CONFIG = CONFIGS[Environment.TEST]

OTHER_ADDRESS = "0x0000000000000000000000000000000000000001"

SESSION_KEY_PRIVATE_KEY = env_template_value("DERIVE_SESSION_KEY")


@pytest.fixture
def signer():
    return Account.from_key(SESSION_KEY_PRIVATE_KEY)


@pytest.fixture
def trade_module_data():
    return TradeModuleData(
        asset_address=OPTION_A_ADDRESS,
        sub_id=OPTION_A_SUB_ID,
        limit_price=Decimal("100"),
        amount=Decimal("1"),
        max_fee=Decimal("1000"),
        recipient_id=SUBACCOUNT_ID,
        is_bid=True,
    )


@pytest.fixture
def action(signer, trade_module_data):
    return SignedAction(
        subaccount_id=SUBACCOUNT_ID,
        owner=OWNER_ADDRESS,
        signer=signer.address,
        signature_expiry_sec=EXPIRY,
        nonce=NONCE,
        module_address=CONFIG.contracts.TRADE_MODULE,
        module_data=trade_module_data,
        DOMAIN_SEPARATOR=CONFIG.DOMAIN_SEPARATOR,
        ACTION_TYPEHASH=CONFIG.ACTION_TYPEHASH,
    )


def test_session_key_matches_the_one_the_constants_were_captured_with(signer):
    """The capture script reads DERIVE_SESSION_KEY from .env; this file reads
    tests/conftest. If they diverge, every frozen hash below fails for a reason
    that looks nothing like the cause."""
    assert signer.address == SIGNER_ADDRESS


def test_action_hash(action):
    assert action._get_action_hash().to_0x_hex() == EXPECTED_ACTION_HASH


def test_typed_data_hash(action):
    assert action._to_typed_data_hash().to_0x_hex() == EXPECTED_TYPED_DATA_HASH


def test_signature(action, signer):
    assert action.sign(signer.key) == EXPECTED_SIGNATURE


def test_validate_signature_accepts_its_own_signature(action, signer):
    action.sign(signer.key)
    action.validate_signature()


def test_validate_signature_rejects_a_different_signer(action):
    """The recovered address must equal the declared signer."""
    action.sign(Account.create().key)
    with pytest.raises(ValueError):
        action.validate_signature()


@pytest.mark.parametrize(
    "changes",
    [
        {"subaccount_id": SUBACCOUNT_ID + 1},
        {"nonce": NONCE + 1},
        {"signature_expiry_sec": EXPIRY + 1},
        {"module_address": CONFIG.contracts.WITHDRAW_MODULE},
        {"owner": OTHER_ADDRESS},
        {"signer": OTHER_ADDRESS},
        {"ACTION_TYPEHASH": "0x" + "11" * 32},
    ],
    ids=lambda changes: ",".join(changes),
)
def test_every_envelope_field_binds_into_the_action_hash(action, changes):
    """A field omitted from the encoding could be tampered with freely, and
    nothing else in the suite would notice."""
    assert replace(action, **changes)._get_action_hash() != action._get_action_hash()


def test_module_data_binds_into_the_action_hash(action, trade_module_data):
    """The envelope commits to keccak(data), not to the data itself."""
    other = replace(trade_module_data, amount=Decimal("2"))
    assert replace(action, module_data=other)._get_action_hash() != action._get_action_hash()


def test_action_typehash_binds_into_the_action_hash(action):
    before = action._get_action_hash()
    action.ACTION_TYPEHASH = "0x" + "11" * 32
    assert action._get_action_hash() != before


def test_domain_separator_binds_into_the_digest(action):
    """Only the domain separator distinguishes testnet from mainnet, so a
    signature would otherwise be replayable across chains."""
    before = action._to_typed_data_hash()
    action.DOMAIN_SEPARATOR = CONFIGS[Environment.PROD].DOMAIN_SEPARATOR
    assert action._to_typed_data_hash() != before


@pytest.mark.parametrize("value", ["0xnothex", "0x" + "11" * 31, ""])
def test_malformed_action_typehash_is_rejected(action, value):
    with pytest.raises(ValueError):
        replace(action, ACTION_TYPEHASH=value)._get_action_hash()


@pytest.mark.parametrize("value", ["0xnothex", "0x" + "11" * 31, ""])
def test_malformed_domain_separator_is_rejected(action, value):
    with pytest.raises(ValueError):
        replace(action, DOMAIN_SEPARATOR=value)._to_typed_data_hash()


def test_to_json_is_subaccount_scoped_for_trade(action, signer):
    """Trade actions carry subaccount_id; only session key and whitelisted
    recipients are wallet-scoped."""
    action.sign(signer.key)
    payload = action.to_json()
    assert payload["subaccount_id"] == SUBACCOUNT_ID
    assert "wallet" not in payload


def test_to_json_serialises_the_nonce_as_a_string(action, signer):
    """A nanosecond nonce exceeds 2^53 and is corrupted by any JSON consumer
    using doubles. private/order_debug rejects an integer outright."""
    action.sign(signer.key)
    payload = action.to_json()
    assert payload["nonce"] == str(NONCE)
    assert int(payload["nonce"]) == NONCE


def test_expected_encodings_are_word_aligned():
    """A truncated constant would otherwise fail as an unreadable hex diff."""
    skip = {"EXPECTED_SIGNATURE"}  # 65-byte r||s||v, not ABI data
    for name in dir(expected):
        if not name.startswith("EXPECTED_") or name in skip:
            continue
        value = getattr(expected, name)
        if isinstance(value, str) and value.startswith("0x"):
            assert len(value[2:]) % 64 == 0, f"{name} is {len(value[2:])} hex chars, not a multiple of 64"


def test_expected_signature_is_65_bytes():
    """r||s||v, unprefixed -- the server rejects a 0x-prefixed signature."""
    assert len(EXPECTED_SIGNATURE) == 130
    assert not EXPECTED_SIGNATURE.startswith("0x")


def test_constants_accept_an_unprefixed_value(action):
    """0x is optional; the length check is what guards against truncation."""
    prefixed = action._to_typed_data_hash()
    action.DOMAIN_SEPARATOR = CONFIG.DOMAIN_SEPARATOR.removeprefix("0x")
    assert action._to_typed_data_hash() == prefixed
