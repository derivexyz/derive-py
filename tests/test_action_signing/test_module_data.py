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

from derive_py._web3.action_signing import (
    RFQExecuteModuleData,
    RFQQuoteDetails,
    RFQQuoteModuleData,
    SessionKeyModuleData,
    TradeModuleData,
    TransferSpotExternalModuleData,
    TransferSpotModuleData,
    VaultAction,
    VaultBurnSharesModuleData,
    VaultCancelModuleData,
    VaultCreateModuleData,
    VaultDepositModuleData,
    VaultMintSharesModuleData,
    VaultWithdrawModuleData,
    WhitelistedRecipientModuleData,
    WithdrawModuleData,
)
from derive_py.data_types import ProtocolScope

from .expected import (
    EXPECTED_RFQ_EXECUTE,
    EXPECTED_RFQ_QUOTE,
    EXPECTED_SESSION_KEY,
    EXPECTED_TRADE,
    EXPECTED_TRANSFER_SPOT,
    EXPECTED_TRANSFER_SPOT_EXTERNAL,
    EXPECTED_VAULT_BURN_SHARES,
    EXPECTED_VAULT_CANCEL,
    EXPECTED_VAULT_CREATE,
    EXPECTED_VAULT_DEPOSIT,
    EXPECTED_VAULT_MINT_SHARES,
    EXPECTED_VAULT_WITHDRAW,
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
    VAULT_AMOUNT,
    VAULT_BENCHMARK_ASSET,
    VAULT_COOLDOWN_SEC,
    VAULT_DEPOSIT_ASSET,
    VAULT_INITIAL_DEPOSIT,
    VAULT_INITIAL_SHARE_PRICE_USD,
    VAULT_MANAGEMENT_FEE_BPS,
    VAULT_MANAGER_ID,
    VAULT_MAX_FEE_USD,
    VAULT_MAX_SLIPPAGE_BPS,
    VAULT_PERFORMANCE_FEE_BPS,
    VAULT_SHARE_PRICE,
    VAULT_SHARES_TO_BURN,
    VAULT_SUBACCOUNT_ID,
    VAULT_USER_ACTION_HASH,
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


def vault_create(benchmark_asset: str | None = VAULT_BENCHMARK_ASSET) -> VaultCreateModuleData:
    return VaultCreateModuleData(
        manager_id=VAULT_MANAGER_ID,
        deposit_spot_asset=VAULT_DEPOSIT_ASSET,
        initial_deposit=Decimal(VAULT_INITIAL_DEPOSIT),
        management_fee_bps=VAULT_MANAGEMENT_FEE_BPS,
        performance_fee_bps=VAULT_PERFORMANCE_FEE_BPS,
        max_slippage_bps=VAULT_MAX_SLIPPAGE_BPS,
        cooldown_sec=VAULT_COOLDOWN_SEC,
        max_fee_usd=Decimal(VAULT_MAX_FEE_USD),
        initial_share_price_usd=Decimal(VAULT_INITIAL_SHARE_PRICE_USD),
        benchmark_asset=benchmark_asset,
    )


def vault_deposit() -> VaultDepositModuleData:
    return VaultDepositModuleData(
        vault_subaccount_id=VAULT_SUBACCOUNT_ID,
        deposit_spot_asset=VAULT_DEPOSIT_ASSET,
        amount=Decimal(VAULT_AMOUNT),
    )


def vault_withdraw() -> VaultWithdrawModuleData:
    return VaultWithdrawModuleData(
        vault_subaccount_id=VAULT_SUBACCOUNT_ID,
        shares_to_burn=Decimal(VAULT_SHARES_TO_BURN),
    )


def vault_cancel() -> VaultCancelModuleData:
    return VaultCancelModuleData(vault_subaccount_id=VAULT_SUBACCOUNT_ID)


def vault_mint() -> VaultMintSharesModuleData:
    return VaultMintSharesModuleData(
        share_price=Decimal(VAULT_SHARE_PRICE),
        user_action_hash=VAULT_USER_ACTION_HASH,
    )


def vault_burn() -> VaultBurnSharesModuleData:
    return VaultBurnSharesModuleData(
        share_price=Decimal(VAULT_SHARE_PRICE),
        user_action_hash=VAULT_USER_ACTION_HASH,
    )


ALL_VAULT_BUILDERS = {
    VaultAction.CREATE: vault_create,
    VaultAction.DEPOSIT: vault_deposit,
    VaultAction.WITHDRAW: vault_withdraw,
    VaultAction.CANCEL: vault_cancel,
    VaultAction.MINT_SHARES: vault_mint,
    VaultAction.BURN_SHARES: vault_burn,
}


def test_vault_create():
    assert as_hex(vault_create()) == EXPECTED_VAULT_CREATE


def test_vault_deposit():
    assert as_hex(vault_deposit()) == EXPECTED_VAULT_DEPOSIT


def test_vault_withdraw():
    assert as_hex(vault_withdraw()) == EXPECTED_VAULT_WITHDRAW


def test_vault_cancel():
    assert as_hex(vault_cancel()) == EXPECTED_VAULT_CANCEL


def test_vault_mint_shares():
    assert as_hex(vault_mint()) == EXPECTED_VAULT_MINT_SHARES


def test_vault_burn_shares():
    assert as_hex(vault_burn()) == EXPECTED_VAULT_BURN_SHARES


@pytest.mark.parametrize("kind", list(VaultAction), ids=lambda kind: kind.name)
def test_vault_kind_word_is_exact(kind):
    """Word 0 is the protocol's only discriminator between the six vault
    actions, all of which are signed under the same module address. Since the
    canonical-ABI change the server rejects dirty high bytes rather than
    truncating them, so the whole word is pinned, not just its low byte."""
    encoded = ALL_VAULT_BUILDERS[kind]().to_abi_encoded()
    assert encoded[:32] == kind.to_bytes(32, "big")


def test_vault_kinds_are_distinct():
    """A copy-pasted KIND on a new subclass has no other symptom: the payload
    still encodes, still signs, and decodes server-side as the wrong action."""
    kinds = [builder().to_abi_encoded()[:32] for builder in ALL_VAULT_BUILDERS.values()]
    assert len(set(kinds)) == len(ALL_VAULT_BUILDERS)


@pytest.mark.parametrize(
    ("kind", "words"),
    [
        (VaultAction.CREATE, 12),
        (VaultAction.DEPOSIT, 4),
        (VaultAction.WITHDRAW, 3),
        (VaultAction.CANCEL, 2),
        (VaultAction.MINT_SHARES, 3),
        (VaultAction.BURN_SHARES, 3),
    ],
    ids=lambda value: value.name if isinstance(value, VaultAction) else str(value),
)
def test_vault_word_counts(kind, words):
    """Every vault payload is fixed-width with no dynamic tail, so a dropped or
    duplicated field shows up as a length change before it shows up as a diff."""
    assert len(ALL_VAULT_BUILDERS[kind]().to_abi_encoded()) == words * 32


def test_mint_and_burn_differ_only_in_the_kind_word():
    """The two settle layouts are identical, so the kind word is the only thing
    stopping a signed mint from decoding as a burn, at a price the curator
    quoted for the opposite side of the queue."""
    mint = vault_mint().to_abi_encoded()
    burn = vault_burn().to_abi_encoded()
    assert mint[:32] != burn[:32]
    assert mint[32:] == burn[32:]


def test_withdraw_is_not_a_cancel_with_a_trailing_word():
    """Cancel's fields are a prefix of withdraw's. Only the kind word separates
    'burn these shares' from 'drain every pending intent'."""
    withdraw = vault_withdraw().to_abi_encoded()
    cancel = vault_cancel().to_abi_encoded()
    assert not withdraw.startswith(cancel)
    assert withdraw[32:64] == cancel[32:64]


def test_create_omitted_benchmark_encodes_zero_address_and_false():
    """Presence of benchmark_asset, not its value, drives the encoded
    has_benchmark flag, matching how the exchange derives it from the wire
    param."""
    encoded = vault_create(benchmark_asset=None).to_abi_encoded()
    assert encoded[-64:] == bytes(32) + bytes(32)


def test_create_explicit_zero_benchmark_differs_from_an_omitted_one():
    """The two produce the same benchmark word and must still differ: passing
    the zero address is a request for a zero-address benchmark, not for the
    feed-less USD default."""
    zero_address = "0x" + "00" * 20
    assert (
        vault_create(benchmark_asset=zero_address).to_abi_encoded()
        != vault_create(benchmark_asset=None).to_abi_encoded()
    )


def test_create_bps_and_cooldown_are_not_scaled():
    """bps rates and cooldown_sec are plain integers while every value beside
    them is e18. Scaling them would be silently accepted by the encoder."""
    encoded = vault_create().to_abi_encoded()
    words = [encoded[i : i + 32] for i in range(0, len(encoded), 32)]
    assert [int.from_bytes(word, "big") for word in words[4:8]] == [
        VAULT_MANAGEMENT_FEE_BPS,
        VAULT_PERFORMANCE_FEE_BPS,
        VAULT_MAX_SLIPPAGE_BPS,
        VAULT_COOLDOWN_SEC,
    ]


@pytest.mark.parametrize(
    "build",
    [
        lambda value: VaultDepositModuleData(VAULT_SUBACCOUNT_ID, VAULT_DEPOSIT_ASSET, value),
        lambda value: VaultWithdrawModuleData(VAULT_SUBACCOUNT_ID, value),
        lambda value: VaultMintSharesModuleData(value, VAULT_USER_ACTION_HASH),
    ],
    ids=["deposit_amount", "shares_to_burn", "share_price"],
)
def test_vault_rejects_sub_1e12_precision(build):
    """The protocol holds decimals at 1e12 and rejects, rather than truncates,
    an e18 word carrying finer precision. scale_amount would have truncated it
    into a word the exchange refuses to verify."""
    with pytest.raises(ValueError, match="12 decimal"):
        build(Decimal("0.0000000000001")).to_abi_encoded()


@pytest.mark.parametrize(
    "build",
    [
        lambda value: VaultDepositModuleData(VAULT_SUBACCOUNT_ID, VAULT_DEPOSIT_ASSET, value),
        lambda value: VaultWithdrawModuleData(VAULT_SUBACCOUNT_ID, value),
    ],
    ids=["deposit_amount", "shares_to_burn"],
)
@pytest.mark.parametrize("value", [Decimal("0"), Decimal("-1")], ids=["zero", "negative"])
def test_vault_amounts_must_be_strictly_positive(build, value):
    with pytest.raises(ValueError):
        build(value).to_abi_encoded()


def test_vault_share_price_may_be_zero():
    """Mirrors derive-ts unsignedE18. Rejecting zero here would refuse a
    payload the exchange accepts, which is a worse failure than allowing one
    the exchange will reject on its own slippage check."""
    encoded = VaultMintSharesModuleData(Decimal("0"), VAULT_USER_ACTION_HASH).to_abi_encoded()
    assert encoded[32:64] == bytes(32)


@pytest.mark.parametrize("value", ["0xd1d1", "0x" + "d1" * 33, "0x" + "zz" * 32, ""])
def test_settle_rejects_a_hash_that_is_not_32_bytes(value):
    """The hash binds the quoted price to one exact queued request. A malformed
    one would sign cleanly and settle nothing."""
    with pytest.raises(ValueError):
        VaultMintSharesModuleData(Decimal(VAULT_SHARE_PRICE), value).to_abi_encoded()


@pytest.mark.parametrize(
    ("build", "field"),
    [
        (vault_deposit, "amount"),
        (vault_withdraw, "shares_to_burn"),
        (vault_create, "initial_deposit"),
        (vault_mint, "share_price"),
    ],
    ids=["deposit", "withdraw", "create", "mint"],
)
def test_wire_decimal_and_signed_word_agree(build, field):
    """The signature commits to the e18 word while the request body carries a
    decimal string; nothing on the server cross-checks them for us, so both are
    rendered from the same integer."""
    module_data = build()
    payload = module_data.to_json()
    encoded = module_data.to_abi_encoded()
    words = [int.from_bytes(encoded[i : i + 32], "big") for i in range(0, len(encoded), 32)]
    assert int(Decimal(payload[field]) * Decimal(10**18)) in words


def test_wire_decimal_never_uses_scientific_notation():
    """str(Decimal("1E+3")) is "1E+3", which the API rejects. format_units
    renders from the scaled integer instead."""
    module_data = VaultDepositModuleData(VAULT_SUBACCOUNT_ID, VAULT_DEPOSIT_ASSET, Decimal("1E+3"))
    assert module_data.to_json()["amount"] == "1000"


def test_create_json_sends_an_explicit_null_benchmark():
    """An omitted key and a null are equivalent to the exchange, but the value
    must not silently become the zero address, which would flip has_benchmark
    on the server's side of the rebuild and invalidate the signature."""
    assert vault_create(benchmark_asset=None).to_json()["benchmark_asset"] is None


@pytest.mark.parametrize("kind", list(VaultAction), ids=lambda kind: kind.name)
def test_vault_actions_are_subaccount_scoped(kind):
    """Every vault action carries subaccount_id, never wallet, even the curator
    settle approvals signed on the vault subaccount itself."""
    assert ALL_VAULT_BUILDERS[kind]().WALLET_SCOPED is False
