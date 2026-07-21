"""Tests for Market module."""

from derive_client.data_types.generated_models import (
    AssetType,
    Currency,
    GetAllInstrumentsResponse,
    Instrument,
)
from derive_client.data_types.generated_models import (
    InstrumentType as AssetType,
)


def test_markets_get_currency(client_admin_wallet):
    currency = "ETH"
    currency = client_admin_wallet.markets.get_currency(currency=currency)
    assert isinstance(currency, Currency)


def test_markets_get_all_currencies(client_admin_wallet):
    currencies = client_admin_wallet.markets.get_all_currencies()
    assert isinstance(currencies, list)
    assert all(isinstance(item, Currency) for item in currencies)


def test_markets_get_instrument(client_admin_wallet):
    instrument_name = "ETH-PERP"
    instrument = client_admin_wallet.markets.get_instrument(instrument_name=instrument_name)
    assert isinstance(instrument, Instrument)


# test_markets_get_instruments removed: /public/get_instruments no longer exists
# in v3, MarketOperations.get_instruments() was deleted accordingly.
# get_all_instruments (paginated) is the surviving equivalent, covered below.


def test_markets_get_all_instruments(client_admin_wallet):
    expired = False
    instrument_type = AssetType.perp
    currency = None
    all_instruments = client_admin_wallet.markets.get_all_instruments(
        expired=expired,
        instrument_type=instrument_type,
        currency=currency,
    )
    assert isinstance(all_instruments, GetAllInstrumentsResponse)


def test_markets_get_tickers(client_admin_wallet):
    currency = "ETH"
    expired = False
    instrument_type = AssetType.option
    all_instruments = client_admin_wallet.markets.get_all_instruments(
        currency=currency,
        expired=expired,
        instrument_type=instrument_type,
    )

    _, expiry_date, _, _ = all_instruments.instruments[0].instrument_name.split("-")
    tickers = client_admin_wallet.markets.get_tickers(
        currency=currency,
        expiry_date=expiry_date,
        instrument_type=instrument_type,
    )

    assert isinstance(tickers, dict)
    # v3 change: GetTickersResponse.tickers is dict[str, Any] upstream now,
    # no per-ticker struct is generated anymore. Can't assert a richer type
    # here — check for an expected key on the raw value if you need more.
    assert all(isinstance(ticker, dict) for ticker in tickers.values())
