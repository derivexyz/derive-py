"""Tests for Market module."""

from derive_client.data_types.generated_models import (
    Asset,
    AssetType,
    Currency,
    GetAllInstrumentsResponse,
    GetLatestSignedFeedsResponse,
    Instrument,
    RiskUniverse,
    TickerSlimSnapshot,
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


def test_markets_get_all_live_instruments(client_admin_wallet):
    all_live_instruments = client_admin_wallet.markets.get_all_live_instruments()
    assert isinstance(all_live_instruments, list)
    assert all(isinstance(item, str) for item in all_live_instruments)


def test_markets_get_assets(client_admin_wallet):
    asset_type = AssetType.option
    currency = "ETH"
    expired = False
    assets = client_admin_wallet.markets.get_assets(
        asset_type=asset_type,
        currency=currency,
        expired=expired,
    )
    assert isinstance(assets, list)
    assert all(isinstance(item, Asset) for item in assets)


def test_markets_get_latest_signed_feeds(client_admin_wallet):
    currency = "ETH"
    signed_feeds = client_admin_wallet.markets.get_latest_signed_feeds(
        currency=currency,
        expiry=None,
    )
    assert isinstance(signed_feeds, GetLatestSignedFeedsResponse)


def test_markets_get_risk_universes(client_admin_wallet):
    risk_universes = client_admin_wallet.markets.get_risk_universes()
    assert isinstance(risk_universes, list)
    assert all(isinstance(item, RiskUniverse) for item in risk_universes)


def test_markets_get_ticker(client_admin_wallet):
    instrument_name = "ETH-PERP"
    ticker = client_admin_wallet.markets.get_ticker(instrument_name=instrument_name)
    assert isinstance(ticker, TickerSlimSnapshot)


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
    assert all(isinstance(ticker, TickerSlimSnapshot) for ticker in tickers.values())
