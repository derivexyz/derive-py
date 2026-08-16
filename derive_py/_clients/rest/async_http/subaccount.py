"""Subaccount operations."""

from __future__ import annotations

import functools
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Optional, cast

from hexbytes import HexBytes

from derive_py._clients.rest.async_http.api import AsyncPrivateAPI, AsyncPublicAPI
from derive_py._clients.rest.async_http.collateral import CollateralOperations
from derive_py._clients.rest.async_http.history import HistoryOperations
from derive_py._clients.rest.async_http.markets import MarketOperations
from derive_py._clients.rest.async_http.mmp import MMPOperations
from derive_py._clients.rest.async_http.orders import OrderOperations
from derive_py._clients.rest.async_http.positions import PositionOperations
from derive_py._clients.rest.async_http.rfq import RFQOperations
from derive_py._clients.rest.async_http.system import SystemOperations
from derive_py._clients.rest.async_http.vaults import VaultOperations
from derive_py._clients.utils import AuthContext
from derive_py._web3.action_signing import ModuleData, SignedAction, WithdrawModuleData
from derive_py._web3.async_utils import AsyncDepositStep, iterate_deposit_steps_in_thread
from derive_py._web3.deposits import Deposits, resolve_collateral
from derive_py.data_types import ChainConfig, ChecksumAddress, GasPriority, LoggerType, RiskUniverseID
from derive_py.data_types.generated_models import (
    GetSubaccountRequest,
    PrivateWithdrawRequest,
    PrivateWithdrawResponse,
)
from derive_py.data_types.generated_models import Subaccount as SubaccountState


@functools.total_ordering
class Subaccount:
    """Subaccount operations."""

    def __init__(
        self,
        *,
        subaccount_id: int,
        auth: AuthContext,
        config: ChainConfig,
        logger: LoggerType,
        markets: MarketOperations,
        system: SystemOperations,
        deposits: Deposits,
        public_api: AsyncPublicAPI,
        private_api: AsyncPrivateAPI,
        _state: SubaccountState | None = None,
    ):
        """
        Initialize subaccount (internal use - use from_api() instead).

        Args:
            subaccount_id: Unique identifier for this subaccount
            auth: Authentication context for signing operations
            config: Chain configuration
            markets: Market operations interface
            system: System operations interface
            public_api: Public API interface
            private_api: Private API interface for authenticated requests
            _state: Initial state (internal use only)
        """

        self._id = subaccount_id
        self._auth = auth
        self._config = config
        self._logger = logger
        self._public_api = public_api
        self._private_api = private_api

        self._markets = markets
        self._deposits = deposits
        self._system = system

        self._collateral = CollateralOperations(subaccount=self)
        self._orders = OrderOperations(subaccount=self)
        self._positions = PositionOperations(subaccount=self)
        self._rfq = RFQOperations(subaccount=self)
        self._mmp = MMPOperations(subaccount=self)
        self._history = HistoryOperations.for_subaccount(self)

        self._state: SubaccountState | None = _state

    @classmethod
    async def from_api(
        cls,
        *,
        subaccount_id: int,
        auth: AuthContext,
        config: ChainConfig,
        logger: LoggerType,
        markets: MarketOperations,
        system: SystemOperations,
        deposits: Deposits,
        public_api: AsyncPublicAPI,
        private_api: AsyncPrivateAPI,
    ) -> Subaccount:
        """
        Validate subaccount by fetching its state from the API.

        This performs a network call to verify the subaccount exists and
        caches immutable properties like margin_type and currency.

        Args:
            subaccount_id: Unique identifier for this subaccount
            auth: Authentication context for signing operations
            config: Chain configuration
            markets: Market operations interface
            system: System operations interface
            deposits: Deposits interface for deposit operations
            public_api: Public API interface
            private_api: Private API interface for authenticated requests

        Returns:
            Initialized Subaccount instance

        Raises:
            APIError: If subaccount does not exist or API call fails
        """

        params = GetSubaccountRequest(subaccount_id=subaccount_id)
        result = await private_api.rpc.get_subaccount(params)
        state = result
        logger.debug(f"Subaccount validated: {state.subaccount_id}")

        return cls(
            subaccount_id=subaccount_id,
            auth=auth,
            config=config,
            logger=logger,
            markets=markets,
            system=system,
            deposits=deposits,
            public_api=public_api,
            private_api=private_api,
            _state=state,
        )

    async def refresh(self) -> Subaccount:
        """Refresh mutable state from API."""

        params = GetSubaccountRequest(subaccount_id=self.id)
        result = await self._private_api.rpc.get_subaccount(params)
        self._state = result
        return self

    @property
    def state(self) -> SubaccountState:
        """Current mutable state (positions, orders, collateral, etc)."""

        if not self._state:
            raise RuntimeError(
                "Subaccount state not loaded. Use Subaccount.from_api() to create "
                "instances or call refresh() to load state."
            )
        return self._state

    @property
    def risk_universe_id(self) -> RiskUniverseID:
        """
        Risk Universe ID of subaccount.
        """

        return RiskUniverseID(self.state.risk_universe_id)

    @property
    def margin_type(self) -> str:
        """
        Margin type of subaccount.
        """

        return self.state.margin_type

    @property
    def currency(self) -> list[str]:
        """
        Currency of subaccount.
        """

        return self.state.currency

    @property
    def id(self) -> int:
        """Subaccount ID."""

        return self._id

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

        return self._collateral

    @property
    def orders(self) -> OrderOperations:
        """Place and manage orders."""

        return self._orders

    @property
    def positions(self) -> PositionOperations:
        """View and manage positions."""

        return self._positions

    @property
    def rfq(self) -> RFQOperations:
        """Request for quote operations."""

        return self._rfq

    @property
    def mmp(self) -> MMPOperations:
        """Market maker protection settings."""

        return self._mmp

    @property
    def vaults(self) -> VaultOperations:
        """Vault operations."""

        return VaultOperations(subaccount=self)

    @property
    def history(self) -> HistoryOperations:
        """Historical records for this subaccount only."""

        return self._history

    def sign_action(
        self,
        *,
        module_address: ChecksumAddress,
        module_data: ModuleData,
        signature_expiry_sec: Optional[int] = None,
        nonce: Optional[int] | None = None,
    ) -> SignedAction:
        return self._auth.sign_action(
            nonce=nonce,
            module_address=module_address,
            module_data=module_data,
            signature_expiry_sec=signature_expiry_sec,
            subaccount_id=self.id,
        )

    async def plan_deposit(
        self,
        *,
        asset_name: str,
        amount: Decimal,
        gas_priority: GasPriority = GasPriority.MEDIUM,
    ) -> AsyncIterator[AsyncDepositStep]:
        """Deposit into this subaccount."""

        risk_universes = self.markets._risk_universes_cache or await self.markets.get_risk_universes()
        sync_plan = self._deposits.plan_deposit(
            risk_universes=risk_universes,
            manager_id=self.state.manager_id,
            subaccount_id=self.id,
            asset_name=asset_name,
            amount=amount,
            from_address=ChecksumAddress(self._auth.account.address),
            fallback_recipient=self._auth.wallet,
            private_key=cast(HexBytes, self._auth.account.key).to_0x_hex(),
            gas_priority=gas_priority,
        )
        async for step in iterate_deposit_steps_in_thread(sync_plan):
            yield step

    async def withdraw(
        self,
        *,
        asset_name: str,
        amount: Decimal,
        max_fee_usd: Decimal = Decimal("1"),
        force_batch: bool = False,
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
    ) -> PrivateWithdrawResponse:
        """Submits a signed request to withdraw a spot asset out of a subaccount."""

        risk_universes = self.markets._risk_universes_cache or await self.markets.get_risk_universes()
        collateral = resolve_collateral(risk_universes, manager_id=self.state.manager_id, asset_name=asset_name)
        recipient = self._auth.wallet

        module_data = WithdrawModuleData(
            protocol_asset=collateral.protocol_asset_address,
            asset_name=asset_name,
            max_fee_usd=max_fee_usd,
            recipient=recipient,
            amount=amount,
            decimals=collateral.decimals,
            force_batch=force_batch,
        )

        module_address = self._config.contracts.WITHDRAW_MODULE
        signed_action = self.sign_action(
            nonce=nonce,
            module_address=module_address,
            module_data=module_data,
            signature_expiry_sec=signature_expiry_sec,
        )

        params = PrivateWithdrawRequest(
            subaccount_id=self.id,
            asset_name=asset_name,
            amount_in_underlying=str(amount),
            max_fee_usd=max_fee_usd,
            force_batch=force_batch,
            nonce=signed_action.nonce,
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
        )

        response = await self._private_api.rpc.withdraw(params)
        return response

    def __repr__(self) -> str:
        return f"<{self.__class__.__qualname__}({self.id}) object at {hex(id(self))}>"

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.id < other.id
