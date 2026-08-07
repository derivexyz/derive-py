"""ABI encoding for each module data type.

Expected values captured once from the corresponding *_debug endpoint on
testnet, then frozen. Each is the `encoded_data` field of the result.

The hand-packed encoders (session key, whitelisted recipients) do not use
standard ABI encoding and were transcribed from derive-ts codecs, so their
captured values are the only check on the transcription.
"""

from decimal import Decimal

import pytest
from web3 import Web3

from derive_client._web3.action_signing import (
    RFQExecuteModuleData,
    RFQQuoteDetails,
    RFQQuoteModuleData,
    SessionKeyModuleData,
    TradeModuleData,
    TransferSpotExternalModuleData,
    TransferSpotModuleData,
    WhitelistedRecipientModuleData,
    WithdrawModuleData,
)
from derive_client.data_types import ProtocolScope

from .expected import (
    EXPECTED_RFQ_EXECUTE,
    EXPECTED_RFQ_QUOTE,
    EXPECTED_SESSION_KEY,
    EXPECTED_TRADE,
    EXPECTED_TRANSFER_SPOT,
    EXPECTED_TRANSFER_SPOT_EXTERNAL,
    EXPECTED_WHITELISTED_RECIPIENTS,
    EXPECTED_WITHDRAW,
    EXPIRY,
    OPTION_A_ADDRESS,
    OPTION_A_NAME,
    OPTION_A_SUB_ID,
    OPTION_B_ADDRESS,
    OPTION_B_NAME,
    OPTION_B_SUB_ID,
    OTHER_SUBACCOUNT_ID,
    OWNER_ADDRESS,
    RECIPIENT,
    SUBACCOUNT_ID,
    USDC_ADDRESS,
    USDC_ASSET_NAME,
    USDC_DECIMALS,
    USDC_SUB_ID,
)


def as_hex(module_data) -> str:
    return "0x" + module_data.to_abi_encoded().hex()


def rfq_legs(directions):
    legs = [
        RFQQuoteDetails(
            instrument_name=name,
            direction=direction,
            asset_address=address,
            sub_id=sub_id,
            price=price,
            amount=amount,
        )
        for name, address, sub_id, direction, price, amount in (
            (OPTION_A_NAME, OPTION_A_ADDRESS, OPTION_A_SUB_ID, directions[0], Decimal("50"), Decimal("1")),
            (OPTION_B_NAME, OPTION_B_ADDRESS, OPTION_B_SUB_ID, directions[1], Decimal("100"), Decimal("2")),
        )
    ]
    return sorted(legs, key=lambda leg: leg.instrument_name)


def test_trade():
    module_data = TradeModuleData(
        asset_address=OPTION_A_ADDRESS,
        sub_id=OPTION_A_SUB_ID,
        limit_price=Decimal("100"),
        amount=Decimal("1"),
        max_fee=Decimal("1000"),
        recipient_id=SUBACCOUNT_ID,
        is_bid=True,
    )
    assert as_hex(module_data) == EXPECTED_TRADE


def test_rfq_quote():
    module_data = RFQQuoteModuleData(
        global_direction="sell",
        max_fee=Decimal("1000"),
        legs=rfq_legs(("buy", "buy")),
    )
    assert as_hex(module_data) == EXPECTED_RFQ_QUOTE


def test_rfq_execute():
    module_data = RFQExecuteModuleData(
        global_direction="sell",
        max_fee=Decimal("1000"),
        legs=rfq_legs(("sell", "buy")),
    )
    assert as_hex(module_data) == EXPECTED_RFQ_EXECUTE
    # The first word of the encoding is keccak of the direction-inverted legs.
    assert Web3.keccak(module_data._encoded_legs()).to_0x_hex() == EXPECTED_RFQ_EXECUTE[:66]


def test_rfq_execute_encodes_differently_from_quote():
    """RFQExecuteModuleData inherits from RFQQuoteModuleData but overrides
    to_abi_encoded and inverts leg directions. An accidental super() call would
    produce a valid signature over the wrong payload."""
    legs = rfq_legs(("sell", "buy"))
    quote = RFQQuoteModuleData(global_direction="sell", max_fee=Decimal("1000"), legs=legs)
    execute = RFQExecuteModuleData(global_direction="sell", max_fee=Decimal("1000"), legs=legs)
    assert execute.to_abi_encoded() != quote.to_abi_encoded()


def test_withdraw():
    module_data = WithdrawModuleData(
        protocol_asset=USDC_ADDRESS,
        asset_name=USDC_ASSET_NAME,
        max_fee_usd=Decimal("1.5"),
        recipient=OWNER_ADDRESS,
        amount=Decimal("10"),
        decimals=USDC_DECIMALS,
        force_batch=False,
    )
    assert as_hex(module_data) == EXPECTED_WITHDRAW


def test_withdraw_uses_native_decimals():
    """v3 takes the withdrawal amount in the asset's native ERC-20 decimals."""
    six = WithdrawModuleData(
        protocol_asset=USDC_ADDRESS,
        asset_name=USDC_ASSET_NAME,
        max_fee_usd=Decimal("1.5"),
        recipient=OWNER_ADDRESS,
        amount=Decimal("10"),
        decimals=6,
        force_batch=False,
    )
    eighteen = WithdrawModuleData(
        protocol_asset=USDC_ADDRESS,
        asset_name=USDC_ASSET_NAME,
        max_fee_usd=Decimal("1.5"),
        recipient=OWNER_ADDRESS,
        amount=Decimal("10"),
        decimals=18,
        force_batch=False,
    )
    assert six.to_abi_encoded() != eighteen.to_abi_encoded()


def test_transfer_spot():
    module_data = TransferSpotModuleData(
        to_subaccount_id=OTHER_SUBACCOUNT_ID,
        new_subaccount_manager=0,
        asset=USDC_ADDRESS,
        asset_name=USDC_ASSET_NAME,
        sub_id=USDC_SUB_ID,
        amount=Decimal("10"),
        max_fee_usd=Decimal("1.5"),
    )
    assert as_hex(module_data) == EXPECTED_TRANSFER_SPOT


def test_transfer_spot_external():
    module_data = TransferSpotExternalModuleData(
        to_subaccount_id=0,
        new_subaccount_manager=1,
        asset=USDC_ADDRESS,
        asset_name=USDC_ASSET_NAME,
        sub_id=USDC_SUB_ID,
        amount=Decimal("10"),
        max_fee_usd=Decimal("1.5"),
        recipient=RECIPIENT,
    )
    assert as_hex(module_data) == EXPECTED_TRANSFER_SPOT_EXTERNAL


def test_session_key():
    module_data = SessionKeyModuleData(
        session_key=RECIPIENT,
        expiry_sec=EXPIRY,
        protocol_scopes=[ProtocolScope.WITHDRAW],
        subaccount_ids=[],
    )
    assert as_hex(module_data) == EXPECTED_SESSION_KEY


def test_whitelisted_recipients():
    module_data = WhitelistedRecipientModuleData(add=[RECIPIENT], remove=[])
    assert as_hex(module_data) == EXPECTED_WHITELISTED_RECIPIENTS


@pytest.mark.parametrize(
    "module_data",
    [
        WhitelistedRecipientModuleData(add=[RECIPIENT], remove=[]),
        WhitelistedRecipientModuleData(add=[], remove=[RECIPIENT]),
    ],
    ids=["add", "remove"],
)
def test_whitelisted_recipients_distinguishes_add_from_remove(module_data):
    """The hand-packed layout is (add_count, remove_count, add[], remove[]).
    Swapping the counts would silently whitelist instead of revoke."""
    other = WhitelistedRecipientModuleData(
        add=module_data.remove,
        remove=module_data.add,
    )
    assert module_data.to_abi_encoded() != other.to_abi_encoded()
