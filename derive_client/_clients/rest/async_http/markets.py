"""Market data queries."""

from __future__ import annotations

from typing import Optional

import msgspec

from derive_client._clients.rest.async_http.api import AsyncPublicAPI
from derive_client._clients.utils import async_fetch_all_pages_of_instrument_type, infer_instrument_type
from derive_client.data_types import LoggerType
from derive_client.data_types.generated_models import (
    Asset,
    AssetType,
    Currency,
    GetAllInstrumentsRequest,
    GetAllInstrumentsResponse,
    GetAssetsRequest,
    GetCurrencyRequest,
    GetInstrumentRequest,
    GetLatestSignedFeedsRequest,
    GetLatestSignedFeedsResponse,
    GetTickerRequest,
    GetTickersRequest,
    Instrument,
    RiskUniverse,
    TickerSlimSnapshot,
)


class MarketOperations:
    """Market data queries."""

    def __init__(self, *, public_api: AsyncPublicAPI, logger: LoggerType):
        """
        Initialize market data queries.

        Args:
            public_api: PublicAPI instance providing access to public APIs
        """
        self._public_api = public_api
        self._logger = logger

        self._erc20_instruments_cache: dict[str, Instrument] = {}
        self._perp_instruments_cache: dict[str, Instrument] = {}
        self._option_instruments_cache: dict[str, Instrument] = {}
        self._risk_universes_cache: list[RiskUniverse] = []

    @property
    def erc20_instruments_cache(self) -> dict[str, Instrument]:
        """Get cached ERC20 instruments."""

        if not self._erc20_instruments_cache:
            raise RuntimeError(
                "Call fetch_instruments() or fetch_all_instruments() to create the erc20_instruments_cache."
            )
        return self._erc20_instruments_cache

    @property
    def perp_instruments_cache(self) -> dict[str, Instrument]:
        """Get cached perpetual instruments."""

        if not self._perp_instruments_cache:
            raise RuntimeError(
                "Call fetch_instruments() or fetch_all_instruments() to create the perp_instruments_cache."
            )
        return self._perp_instruments_cache

    @property
    def option_instruments_cache(self) -> dict[str, Instrument]:
        """Get cached option instruments."""

        if not self._option_instruments_cache:
            raise RuntimeError(
                "Call fetch_instruments() or fetch_all_instruments() to create the option_instruments_cache."
            )
        return self._option_instruments_cache

    async def fetch_instruments(
        self,
        *,
        instrument_type: AssetType,
        expired: bool = False,
    ) -> dict[str, Instrument]:
        """
        Fetch instruments for a specific instrument type from API.

        Args:
            instrument_type: The type of instruments to fetch (erc20, perp, or option)
            expired: If False (default), update cache with active instruments.
                     If True, return expired instruments without caching.

        Returns:
            Dictionary mapping instrument_name to instrument data
        """

        instruments = {}
        for instrument in await async_fetch_all_pages_of_instrument_type(
            markets=self,
            instrument_type=instrument_type,
            expired=expired,
        ):
            instruments[instrument.instrument_name] = instrument

        if expired:
            return instruments

        cache = self._get_cache_for_type(instrument_type)
        cache.clear()
        cache.update(instruments)
        self._logger.debug(f"Cached {len(cache)} {instrument_type.name.upper()} instruments")
        return cache

    async def fetch_all_instruments(self, *, expired: bool = False) -> dict[str, Instrument]:
        """
        Fetch all instrument types from API.

        Args:
            expired: If False (default), update all caches with active instruments.
                     If True, return expired instruments without caching.

        Returns:
            Dictionary mapping instrument_name to instrument data for all types
        """

        all_instruments = {}
        for instrument_type in AssetType:
            instruments = await self.fetch_instruments(instrument_type=instrument_type, expired=expired)
            all_instruments.update(instruments)

        return all_instruments

    def _get_cache_for_type(self, instrument_type: AssetType) -> dict[str, Instrument]:
        """Get the cache for a specific instrument type."""

        match instrument_type:
            case AssetType.erc20:
                return self._erc20_instruments_cache
            case AssetType.perp:
                return self._perp_instruments_cache
            case AssetType.option:
                return self._option_instruments_cache
            case _:
                raise TypeError(f"Unsupported instrument_type: {instrument_type!r}")

    def _get_cached_instrument(self, *, instrument_name: str) -> Instrument:
        """Internal helper to retrieve an instrument from cache."""

        instrument_type = infer_instrument_type(instrument_name=instrument_name)

        cache = self._get_cache_for_type(instrument_type)

        if (instrument := cache.get(instrument_name)) is None:
            raise RuntimeError(
                f"Instrument '{instrument_name}' not found in {instrument_type} instrument cache. "
                "Either the name is incorrect, or the local cache is stale. "
                "Call fetch_instruments() or fetch_all_instruments() to refresh the cache."
            )

        return instrument

    async def get_currency(self, *, currency: str) -> Currency:
        """Get currency related risk params, spot price 24hrs ago and lending details for a specific currency."""

        params = GetCurrencyRequest(currency=currency)
        result = await self._public_api.rpc.get_currency(params)
        return result

    async def get_all_currencies(self) -> list[Currency]:
        """Get all active currencies with their spot price, spot price 24hrs ago."""

        result = await self._public_api.rpc.get_all_currencies(None)
        return result

    async def get_instrument(self, *, instrument_name: str) -> Instrument:
        """Get single instrument by asset name."""

        params = GetInstrumentRequest(instrument_name=instrument_name)
        result = await self._public_api.rpc.get_instrument(params)
        return result

    async def get_all_instruments(
        self,
        *,
        expired: bool,
        instrument_type: AssetType,
        currency: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        risk_universe_id: Optional[int] = None,
    ) -> GetAllInstrumentsResponse:
        """Get a paginated history of all instruments."""

        params = GetAllInstrumentsRequest(
            expired=expired,
            instrument_type=instrument_type,
            currency=currency,
            page=page,
            page_size=page_size,
            risk_universe_id=risk_universe_id,
        )
        result = await self._public_api.rpc.get_all_instruments(params)
        return result

    async def get_all_live_instruments(self) -> list[str]:
        """Returns a sorted list of the names of every currently live instrument."""

        result = await self._public_api.rpc.get_all_live_instruments(None)
        return result

    async def get_assets(self, *, asset_type: AssetType, currency: str, expired: bool = False) -> list[Asset]:
        """Returns the assets of a given asset_type (option, perp, or erc20) for a currency."""

        params = GetAssetsRequest(
            asset_type=asset_type,
            currency=currency,
            expired=expired,
        )

        result = await self._public_api.rpc.get_assets(params)
        return result

    async def get_latest_signed_feeds(
        self,
        *,
        currency: Optional[str] = None,
        expiry: Optional[int] = None,
    ) -> GetLatestSignedFeedsResponse:
        """Returns the most recent oracle-signed feed data."""

        params = GetLatestSignedFeedsRequest(
            currency=currency,
            expiry=expiry,
        )

        result = await self._public_api.rpc.get_latest_signed_feeds(params)
        return result

    async def get_risk_universes(self) -> list[RiskUniverse]:
        """List every universe with its managers and their accepted collaterals / instruments."""

        self._risk_universes_cache = await self._public_api.rpc.get_risk_universes(None)
        return self._risk_universes_cache

    async def get_ticker(self, *, instrument_name: str) -> TickerSlimSnapshot:
        """
        Get ticker information (best bid / ask, instrument contraints, fees info, etc.) for a single instrument.
        """

        params = GetTickerRequest(instrument_name=instrument_name)
        result = await self._public_api.rpc.get_ticker(params)
        return result

    async def get_tickers(
        self,
        *,
        instrument_type: AssetType,
        currency: Optional[str] = None,
        expiry_date: Optional[int] = None,
    ) -> dict[str, TickerSlimSnapshot]:
        """
        Get tickers information (best bid / ask, stats, etc.) for multiple instruments.

        v3 change: the response's tickers field is now dict[str, Any] upstream,
        no per-ticker struct is generated anymore, precision lost at the spec
        level, nothing to fix on this end.

        For options: currency is required and expiry_date is required.
        For perps: currency is optional, expiry_date will throw an error.
        For erc20s: currency is optional, expiry_date will throw an error.
        """

        params = GetTickersRequest(
            currency=currency,
            instrument_type=instrument_type,
            expiry_date=expiry_date or msgspec.UNSET,
        )
        result = await self._public_api.rpc.get_tickers(params)
        return result.tickers
