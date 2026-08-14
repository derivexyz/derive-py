from __future__ import annotations

import asyncio
import contextlib
from decimal import Decimal
from pathlib import Path
from typing import AsyncGenerator, AsyncIterator, cast

from hexbytes import HexBytes

from derive_client._clients.rest.async_http.account import LightAccount
from derive_client._clients.rest.async_http.api import AsyncPrivateAPI, AsyncPublicAPI
from derive_client._clients.rest.async_http.collateral import CollateralOperations
from derive_client._clients.rest.async_http.history import HistoryOperations
from derive_client._clients.rest.async_http.markets import MarketOperations
from derive_client._clients.rest.async_http.mmp import MMPOperations
from derive_client._clients.rest.async_http.orders import OrderOperations
from derive_client._clients.rest.async_http.positions import PositionOperations
from derive_client._clients.rest.async_http.rfq import RFQOperations
from derive_client._clients.rest.async_http.session import AsyncHTTPSession, request_timeout_override
from derive_client._clients.rest.async_http.subaccount import Subaccount
from derive_client._clients.rest.async_http.system import SystemOperations
from derive_client._clients.rest.async_http.vaults import VaultOperations
from derive_client._clients.utils import load_client_config, make_auth
from derive_client._web3 import ContractRegistry, Deposits
from derive_client._web3.async_utils import AsyncDepositStep, iterate_deposit_steps_in_thread
from derive_client.data_types import (
    AsyncHTTPSessionConfig,
    ChecksumAddress,
    ClientConfig,
    Environment,
    GasPriority,
    LoggerType,
    MarginType,
    RiskUniverseID,
)
from derive_client.exceptions import NotConnectedError
from derive_client.utils.logger import get_logger


class AsyncHTTPClient:
    """Asynchronous HTTP client"""

    def __init__(
        self,
        client_config: ClientConfig,
        *,
        logger: LoggerType | None = None,
        session_config: AsyncHTTPSessionConfig | None = None,
    ):
        logger = logger if logger is not None else get_logger()
        auth = make_auth(client_config, logger=logger)

        self._auth = auth
        self._config = auth.config
        self._subaccount_id = client_config.subaccount_id

        self._logger = logger
        self._session = AsyncHTTPSession(config=session_config, logger=self._logger)

        self._public_api = AsyncPublicAPI(session=self._session, config=self._config)
        self._private_api = AsyncPrivateAPI(session=self._session, config=self._config, auth=auth)

        self._markets = MarketOperations(public_api=self._public_api, logger=self._logger)
        self._system = SystemOperations(public_api=self._public_api, logger=self._logger)

        self._light_account: LightAccount | None = None
        self._subaccounts: dict[int, Subaccount] = {}

        network = "sepolia" if client_config.env == Environment.TEST else "ethereum"
        self._contract_registry = ContractRegistry(w3=auth.w3, network=network)
        self._deposits = Deposits(self._contract_registry, w3=auth.w3, logger=self._logger)

    @classmethod
    def from_env(
        cls,
        session_key_path: Path | None = None,
        env_file: Path | None = None,
    ) -> AsyncHTTPClient:
        """Create the AsyncHTTPClient instance."""

        return cls(load_client_config(session_key_path=session_key_path, env_file=env_file))

    async def connect(self) -> None:
        """Connect to Derive and validate credentials, fetch and cache market instruments."""

        await self._session.open()

        self._light_account = await LightAccount.from_api(
            auth=self._auth,
            config=self._config,
            logger=self._logger,
            public_api=self._public_api,
            private_api=self._private_api,
        )

        await self._markets.fetch_all_instruments(expired=False)
        await self._markets.get_risk_universes()  # cache risk universes

        subaccount_ids = self._light_account.state.subaccount_ids
        if self._subaccount_id not in subaccount_ids:
            self._logger.warning(
                f"Subaccount {self._subaccount_id} does not exist for wallet {self._light_account.address}. "
                f"Available subaccounts: {subaccount_ids}"
            )
            return

        subaccount = await self._instantiate_subaccount(self._subaccount_id)
        self._subaccounts[subaccount.id] = subaccount

    async def disconnect(self) -> None:
        """Close the underlying session and clear cached state. Idempotent."""

        await self._session.close()
        self._light_account = None
        self._subaccounts.clear()
        self._markets._erc20_instruments_cache.clear()
        self._markets._perp_instruments_cache.clear()
        self._markets._option_instruments_cache.clear()
        self._markets._risk_universes_cache.clear()

    async def _instantiate_subaccount(self, subaccount_id: int) -> Subaccount:
        return await Subaccount.from_api(
            subaccount_id=subaccount_id,
            auth=self._auth,
            config=self._config,
            logger=self._logger,
            markets=self._markets,
            system=self._system,
            deposits=self._deposits,
            public_api=self._public_api,
            private_api=self._private_api,
        )

    @property
    def logger(self) -> LoggerType:
        return self._logger

    @property
    def public_api(self) -> AsyncPublicAPI:
        """Direct access to the public API for requests."""

        return self._public_api

    @property
    def private_api(self) -> AsyncPrivateAPI:
        """Direct access to the private API for requests."""

        return self._private_api

    @property
    def account(self) -> LightAccount:
        """Get the LightAccount instance (this is not a web3 contract instance)."""

        if self._light_account is None:
            raise NotConnectedError("AsyncHTTPClient.account accessed before connect(); call connect() first.")
        return self._light_account

    @property
    def active_subaccount(self) -> Subaccount:
        """Get the currently active subaccount."""

        if (subaccount := self._subaccounts.get(self._subaccount_id)) is None:
            raise NotConnectedError("No active subaccount. Call connect() first and ensure subaccount exists.")
        return subaccount

    async def plan_deposit_to_new_subaccount(
        self,
        *,
        risk_universe_id: RiskUniverseID,
        margin_type: MarginType,
        asset_name: str,
        amount: Decimal,
        gas_priority: GasPriority = GasPriority.MEDIUM,
    ) -> AsyncIterator[AsyncDepositStep]:
        """Yield a lazily-built sequence of DepositStep for depositing into a NEW subaccount."""

        risk_universes = self._markets._risk_universes_cache or await self._markets.get_risk_universes()

        sync_plan = self._deposits.plan_new_subaccount(
            risk_universes=risk_universes,
            risk_universe_id=risk_universe_id,
            margin_type=margin_type,
            asset_name=asset_name,
            amount=amount,
            from_address=ChecksumAddress(self._auth.account.address),
            owner=self._auth.wallet,
            private_key=cast(HexBytes, self._auth.account.key).to_0x_hex(),
            gas_priority=gas_priority,
        )

        async for step in iterate_deposit_steps_in_thread(sync_plan):
            yield step

    async def fetch_subaccount(self, subaccount_id: int) -> Subaccount:
        """Fetch a subaccount from API and cache it."""

        self._subaccounts[subaccount_id] = await self._instantiate_subaccount(subaccount_id)
        return self._subaccounts[subaccount_id]

    async def fetch_subaccounts(self) -> list[Subaccount]:
        """Fetch subaccounts from API and cache them."""

        account_subaccounts = await self.account.get_subaccounts()
        return sorted(await asyncio.gather(*(self.fetch_subaccount(sid) for sid in account_subaccounts.subaccount_ids)))

    @property
    def cached_subaccounts(self) -> list[Subaccount]:
        """Get all cached subaccounts."""

        return sorted(self._subaccounts.values())

    @property
    def markets(self) -> MarketOperations:
        """Access market data and instruments."""

        return self._markets

    @property
    def system(self) -> SystemOperations:
        """Access system operations."""

        return self._system

    @property
    def collateral(self) -> CollateralOperations:
        """Manage collateral and margin."""

        return self.active_subaccount.collateral

    @property
    def orders(self) -> OrderOperations:
        """Place and manage orders."""

        return self.active_subaccount.orders

    @property
    def positions(self) -> PositionOperations:
        """View and manage positions."""

        return self.active_subaccount.positions

    @property
    def rfq(self) -> RFQOperations:
        """Request for quote operations."""

        return self.active_subaccount.rfq

    @property
    def history(self) -> HistoryOperations:
        """Historical records for the ACTIVE SUBACCOUNT. For wallet-wide history use `client.account.history`."""

        return self.active_subaccount.history

    @property
    def mmp(self) -> MMPOperations:
        """Market maker protection settings."""

        return self.active_subaccount.mmp

    @property
    def vaults(self) -> VaultOperations:
        """Vault operations."""

        return self.active_subaccount.vaults

    @contextlib.asynccontextmanager
    async def timeout(self, seconds: float) -> AsyncGenerator[None, None]:
        """Temporarily override the request timeout for calls in this context."""
        with request_timeout_override(seconds):
            yield

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
