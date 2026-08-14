"""
Asynchronous WebSocket client for Derive.
"""

from __future__ import annotations

import contextlib
from decimal import Decimal
from pathlib import Path
from textwrap import dedent
from typing import AsyncIterator, Generator, cast

from hexbytes import HexBytes

from derive_client._clients.rest.async_http.account import LightAccount
from derive_client._clients.rest.async_http.collateral import CollateralOperations
from derive_client._clients.rest.async_http.history import HistoryOperations
from derive_client._clients.rest.async_http.markets import MarketOperations
from derive_client._clients.rest.async_http.mmp import MMPOperations
from derive_client._clients.rest.async_http.orders import OrderOperations
from derive_client._clients.rest.async_http.positions import PositionOperations
from derive_client._clients.rest.async_http.rfq import RFQOperations
from derive_client._clients.rest.async_http.subaccount import Subaccount
from derive_client._clients.rest.async_http.system import SystemOperations
from derive_client._clients.rest.async_http.vaults import VaultOperations
from derive_client._clients.utils import (
    ClientConfig,
    UnsubscribeResult,
    load_client_config,
    make_auth,
)
from derive_client._clients.websockets.api import PrivateAPI, PublicAPI
from derive_client._clients.websockets.session import StateCallback, WebSocketSession
from derive_client._web3 import ContractRegistry, Deposits
from derive_client._web3.async_utils import AsyncDepositStep, iterate_deposit_steps_in_thread
from derive_client.data_types import (
    ChecksumAddress,
    ConnectionState,
    Environment,
    GasPriority,
    LoggerType,
    MarginType,
    RiskUniverseID,
    WebSocketSessionConfig,
)
from derive_client.data_types.channel_models import LoginRequest, SetCancelOnDisconnectRequest
from derive_client.utils.logger import get_logger


class WebSocketClient:
    """Asynchronous WebSocket client for real-time data and operations."""

    def __init__(
        self,
        client_config: ClientConfig,
        *,
        logger: LoggerType | None = None,
        session_config: WebSocketSessionConfig | None = None,
    ):
        logger = logger if logger is not None else get_logger()
        auth = make_auth(client_config, logger=logger)

        self._auth = auth
        self._config = auth.config
        self._subaccount_id = client_config.subaccount_id

        self._logger = logger
        self._session = WebSocketSession(
            url=self._config.ws_address,
            config=session_config,
            logger=self._logger,
            on_disconnect=self._handle_disconnect,
            on_reconnect=self._handle_reconnect,
            on_before_resubscribe=self._handle_before_resubscribe,  # Re-authentication hook
        )

        self._public_api = PublicAPI(session=self._session)
        self._private_api = PrivateAPI(session=self._session)

        self._markets = MarketOperations(public_api=self._public_api, logger=self._logger)  # type: ignore
        self._system = SystemOperations(public_api=self._public_api, logger=self._logger)  # type: ignore

        self._light_account: LightAccount | None = None
        self._subaccounts: dict[int, Subaccount] = {}

        network = "sepolia" if client_config.env == Environment.TEST else "ethereum"
        self._contract_registry = ContractRegistry(w3=auth.w3, network=network)
        self._deposits = Deposits(self._contract_registry, w3=auth.w3, logger=self._logger)

        self._logger.info(
            dedent(f"""
                        Initialized WebSocketClient for:
                            wallet:     {auth.wallet}
                            subaccount: {client_config.subaccount_id}
                            signer:     {auth.account.address}
                            environment {client_config.env.value} """)
        )

    @classmethod
    def from_env(
        cls,
        session_key_path: Path | None = None,
        env_file: Path | None = None,
    ) -> WebSocketClient:
        """Create WebSocketClient from environment configuration."""

        return cls(load_client_config(session_key_path=session_key_path, env_file=env_file))

    async def connect(self, *, on_state_change: StateCallback | None = None) -> None:
        """
        Connect to Derive via WebSocket, authenticate, and load account state.

        Args:
            on_state_change: Called on every connection state transition. Also
                settable afterwards via the property of the same name. Without
                it, a drop is only observable by polling `connection_state`.
        """
        if on_state_change is not None:
            self._session.on_state_change = on_state_change
        await self._session.open()
        await self._authenticate()
        await self._initialize_account_and_markets()

        if self._light_account is not None and self._light_account.state.cancel_on_disconnect:
            self._warn_if_cancel_on_disconnect_unwatched()

    @property
    def connection_state(self) -> ConnectionState:
        """Whether the session is usable right now."""

        return self._session.state

    @property
    def on_state_change(self) -> StateCallback | None:
        """
        Called on every connection state transition, with the new state.

        A drop reports RECONNECTING then CONNECTED, and CONNECTED means
        re-authenticated and every channel resubscribed, not merely a socket
        that is open. Delivered in order on its own task, so it may take as
        long as it needs without delaying the reconnect.

        CONNECTED is the resync point: updates during the outage were missed,
        so reload from `orders` and `positions` rather than trusting  local state.
        With cancel-on-disconnect enabled, the resting orders are also gone.
        """

        return self._session.on_state_change

    @on_state_change.setter
    def on_state_change(self, callback: StateCallback | None) -> None:
        self._session.on_state_change = callback

    async def _authenticate(self) -> None:
        """
        Perform WebSocket authentication via `public/login`.
        """
        login_dict = self._auth.sign_ws_login()
        login_params = LoginRequest(
            wallet=login_dict["wallet"],
            timestamp=int(login_dict["timestamp"]),
            signature=login_dict["signature"],
        )
        subaccount_ids = await self._public_api.rpc.login(login_params)
        self._logger.info(f"WebSocket authenticated; accessible subaccounts: {subaccount_ids}")

        # Validate subaccount
        if self._subaccount_id not in subaccount_ids:
            self._logger.warning(
                f"Subaccount {self._subaccount_id} does not exist for wallet {self._auth.wallet}. "
                f"Available subaccounts: {subaccount_ids}"
            )

    def _warn_if_cancel_on_disconnect_unwatched(self) -> None:
        """Orders that can vanish deserve someone listening."""

        if self._session.on_state_change is not None:
            return
        self._logger.warning(
            "cancel-on-disconnect is enabled but no on_state_change callback is registered: "
            "a dropped connection cancels every resting order, and auto-reconnect returns "
            "the client looking healthy with an empty book. Pass one to connect(), or poll "
            "connection_state."
        )

    async def set_cancel_on_disconnect(self, enabled: bool = True) -> str:
        """
        Toggle cancel-on-disconnect for the authenticated wallet.

        A persisted account setting, not a property of the connection: it
        survives a reconnect and does not need re-applying after a drop.

        Every drop therefore empties the book, including one the client
        recovers from on its own, after which it looks healthy and is not.
        Re-place from `orders.list_open()` when `on_state_change` reports
        CONNECTED; a warning is logged if no callback is registered.
        """
        if enabled:
            self._warn_if_cancel_on_disconnect_unwatched()
        params = SetCancelOnDisconnectRequest(enabled=enabled, wallet=self._auth.wallet)
        return await self._private_api.rpc.set_cancel_on_disconnect(params)

    async def _initialize_account_and_markets(self) -> None:
        """Initialize account and fetch market data."""
        self._light_account = await self._instantiate_account()
        await self._markets.fetch_all_instruments(expired=False)

        if self._subaccount_id in self._light_account.state.subaccount_ids:
            subaccount = await self._instantiate_subaccount(self._subaccount_id)
            self._subaccounts[subaccount.id] = subaccount

    def _handle_disconnect(self) -> None:
        """Called when WebSocket disconnects."""
        self._logger.warning("WebSocket client detected disconnect")

    def _handle_reconnect(self) -> None:
        """Called after WebSocket reconnects (before resubscribe)."""
        self._logger.info("WebSocket client reconnected")

    async def _handle_before_resubscribe(self) -> None:
        """Called before resubscribing - perform re-authentication here."""
        self._logger.info("Re-authenticating after reconnection")
        await self._authenticate()
        self._logger.info("Re-authentication successful")

    async def disconnect(self) -> None:
        """Close WebSocket connection and clear cached state. Idempotent."""

        await self._session.close()
        self._light_account = None
        self._subaccounts.clear()
        self._markets._erc20_instruments_cache.clear()
        self._markets._perp_instruments_cache.clear()
        self._markets._option_instruments_cache.clear()
        self._markets._risk_universes_cache.clear()

    async def _instantiate_account(self) -> LightAccount:
        """Instantiate account using WebSocket API."""
        return await LightAccount.from_api(
            auth=self._auth,
            config=self._config,
            logger=self._logger,
            public_api=self._public_api,  # type: ignore
            private_api=self._private_api,  # type: ignore
        )

    async def _instantiate_subaccount(self, subaccount_id: int) -> Subaccount:
        """Instantiate subaccount using WebSocket API."""
        return await Subaccount.from_api(
            subaccount_id=subaccount_id,
            auth=self._auth,
            config=self._config,
            logger=self._logger,
            markets=self._markets,
            system=self._system,
            deposits=self._deposits,
            public_api=self._public_api,  # type: ignore
            private_api=self._private_api,  # type: ignore
        )

    @property
    def logger(self) -> LoggerType:
        return self._logger

    @property
    def public_api(self) -> PublicAPI:
        """Direct access to the public API for requests."""

        return self._public_api

    @property
    def private_api(self) -> PrivateAPI:
        """Direct access to the private API for requests."""

        return self._private_api

    @property
    def account(self) -> LightAccount:
        """Get the LightAccount instance."""

        if self._light_account is None:
            raise RuntimeError("Account not initialized. Call connect() first.")
        return self._light_account

    @property
    def active_subaccount(self) -> Subaccount:
        """Get the currently active subaccount."""

        if (subaccount := self._subaccounts.get(self._subaccount_id)) is None:
            raise RuntimeError("Specified subaccount not initialized. Call connect() first.")
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
        subaccounts = []
        for sid in account_subaccounts.subaccount_ids:
            subaccounts.append(await self.fetch_subaccount(sid))
        return sorted(subaccounts)

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

    @property
    def public_channels(self):
        """Access public channel subscriptions."""
        return self._public_api.channels

    @property
    def private_channels(self):
        """Access private channel subscriptions."""
        return self._private_api.channels

    @property
    def subscriptions(self) -> tuple[str, ...]:
        """Channels currently subscribed, as the venue names them."""

        return self._session.subscriptions

    async def unsubscribe(self, *channels: str) -> UnsubscribeResult | None:
        """Unsubscribe from one or more channels and drop their handlers."""

        return await self._session.unsubscribe(*channels)

    @contextlib.contextmanager
    def timeout(self, seconds: float) -> Generator[None, None, None]:
        """Temporarily override request timeout for RPC calls."""

        prev = self._session._request_timeout
        try:
            self._session._request_timeout = float(seconds)
            yield
        finally:
            self._session._request_timeout = prev

    async def __aenter__(self) -> WebSocketClient:
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()
