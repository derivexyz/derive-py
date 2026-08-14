"""Tests for RFQ module."""

from decimal import Decimal

from derive_client.data_types.generated_models import (
    AssetType,
    CancelBatchRfqsResponse,
    Direction,
    LegUnpricedParams,
    PricedLegParamsAndResponse,
    QuoteGetResponse,
    QuotePollResponse,
    Rfq,
    RfqGetBestQuoteResponse,
    RFQGetResponse,
    RFQPollResponse,
)


def _resolve_currency(client) -> str:
    """
    v3 change: Subaccount.currency is now list[str], not a single str (was
    used as a literal "all" sentinel for SM/all-currency subaccounts here).
    Best-effort translation of the old `if currency == "all": currency =
    "ETH"` fallback — not confirmed against Derive's actual list semantics
    (single specific currency? all supported currencies? empty for SM?).
    Verify before relying on this beyond local testing.
    """
    currencies = client.active_subaccount._state.currency
    if len(currencies) == 1:
        return currencies[0]
    return "ETH"


def _create_unpriced_legs(client):
    # Derive RPC 10004: Multiple currencies not supported
    # [data={
    #   'subaccount_currency': 'ETH', 'base_asset_currency': 'BTC',
    #   'note': 'sometimes due to risk caching of instruments local tests
    #           will create new currency_id without risk updating cache'
    # }]
    currency = _resolve_currency(client)

    n_legs = 2
    direction = Direction.buy
    get_all_instruments_response = client.markets.get_all_instruments(
        currency=currency,
        instrument_type=AssetType.option,
        expired=False,
    )
    instruments = get_all_instruments_response.instruments
    active_instruments = [instrument for instrument in instruments if instrument.is_active]

    legs = []
    for instrument in active_instruments[:n_legs]:
        amount = Decimal(instrument.amount_step)
        instrument_name = instrument.instrument_name
        leg = LegUnpricedParams(
            amount=amount,
            instrument_name=instrument_name,
            direction=direction,
        )
        legs.append(leg)

    return legs


def _create_priced_legs(client, rfq):
    # Price legs using current market prices
    priced_legs = []

    currency = _resolve_currency(client)
    for unpriced_leg in rfq.legs:
        expiry = unpriced_leg.instrument_name.split("-")[1]
        tickers = client.markets.get_tickers(instrument_type=AssetType.option, currency=currency, expiry_date=expiry)
        # v3 change: GetTickersResponse.tickers is dict[str, Any] upstream,
        # each value decodes to a plain dict, not a struct — bracket access,
        # not attribute access. Wrapped in Decimal(str(...)) since Any gives
        # no guarantee of the raw JSON value's type.
        ticker = tickers[unpriced_leg.instrument_name]

        # Derive RPC 11107: Quote maker total cost too high  [data={'worst_cost': '6.33919554', 'total_cost': '80.596'}]
        # Use mark price (more realistic than index for options)
        # Add a small buffer to ensure quote is profitable
        base_price = Decimal(ticker.mark_price)
        if base_price == Decimal("0.0"):
            base_price = Decimal(ticker.index_price)

        if unpriced_leg.direction == Direction.buy:
            # Maker is selling - quote ask side (higher)
            price = base_price * Decimal("1.02")  # 2% above mark
        else:
            # Maker is buying - quote bid side (lower)
            price = base_price * Decimal("0.98")  # 2% below mark

        instrument = client.markets.get_instrument(instrument_name=unpriced_leg.instrument_name)

        price = price.quantize(Decimal(instrument.tick_size))
        # keep original direction here:
        # Derive RPC 11103: Quote leg does not match RFQ leg
        # [data={'RFQ leg direction': 'buy', 'Quote leg direction': 'sell'}]
        priced_leg = PricedLegParamsAndResponse(
            price=price,
            amount=unpriced_leg.amount,
            direction=unpriced_leg.direction,
            instrument_name=unpriced_leg.instrument_name,
        )
        priced_legs.append(priced_leg)

    return priced_legs


def _create_rfq(client) -> Rfq:
    unpriced_legs = _create_unpriced_legs(client)
    label = "test_rfq"
    rfq = client.rfq.send_rfq(legs=unpriced_legs, label=label)
    return rfq


def test_rfq_send_rfq(client_admin_wallet):
    rfq = _create_rfq(client_admin_wallet)
    assert isinstance(rfq, Rfq)


def test_rfq_get_rfqs(client_admin_wallet):
    rfqs = client_admin_wallet.rfq.get_rfqs()
    assert isinstance(rfqs, RFQGetResponse)


def test_rfq_cancel_rfq(client_admin_wallet):
    rfq = _create_rfq(client_admin_wallet)
    result = client_admin_wallet.rfq.cancel_rfq(rfq_id=rfq.rfq_id)
    assert isinstance(result, str)


def test_rfq_cancel_batch_rfqs(client_admin_wallet):
    rfq = _create_rfq(client_admin_wallet)
    cancelled_batch = client_admin_wallet.rfq.cancel_batch_rfqs()
    assert isinstance(cancelled_batch, CancelBatchRfqsResponse)
    assert rfq.rfq_id in cancelled_batch.cancelled_ids


def test_rfq_poll_rfqs(client_admin_wallet):
    polled_rfqs = client_admin_wallet.rfq.poll_rfqs()
    assert isinstance(polled_rfqs, RFQPollResponse)


def test_rfq_get_quotes(client_admin_wallet):
    quotes = client_admin_wallet.rfq.get_quotes()
    assert isinstance(quotes, QuoteGetResponse)


def test_rfq_poll_quotes(client_admin_wallet):
    quotes = client_admin_wallet.rfq.poll_quotes()
    assert isinstance(quotes, QuotePollResponse)


def test_rfq_get_best_quote(client_admin_wallet):
    unpriced_legs = _create_unpriced_legs(client_admin_wallet)
    best_quote = client_admin_wallet.rfq.get_best_quote(legs=unpriced_legs)
    assert isinstance(best_quote, RfqGetBestQuoteResponse)
