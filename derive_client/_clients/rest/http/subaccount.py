"""Subaccount operations."""

from __future__ import annotations

import functools
from decimal import Decimal
from typing import Iterator, Optional

from derive_action_signing import ModuleData, SignedAction

from derive_client._clients.rest.http.api import PrivateAPI, PublicAPI
from derive_client._clients.rest.http.collateral import CollateralOperations
from derive_client._clients.rest.http.markets import MarketOperations
from derive_client._clients.rest.http.mmp import MMPOperations
from derive_client._clients.rest.http.orders import OrderOperations
from derive_client._clients.rest.http.positions import PositionOperations
from derive_client._clients.rest.http.rfq import RFQOperations
from derive_client._clients.rest.http.trades import TradeOperations
from derive_client._clients.rest.http.transactions import TransactionOperations
from derive_client._clients.utils import AuthContext, WithdrawalResult
from derive_client._web3.deposits import Deposits, DepositStep, resolve_collateral
from derive_client.data_types import ChecksumAddress, EnvConfig, GasPriority, LoggerType
from derive_client.data_types.generated_models import (
    GetSubaccountRequest,
    PrivateWithdrawRequest,
)
from derive_client.data_types.generated_models import Subaccount as SubaccountState
from derive_client.data_types.module_data import WithdrawModuleData


@functools.total_ordering
class Subaccount:
    """Subaccount operations."""

    def __init__(
        self,
        *,
        subaccount_id: int,
        auth: AuthContext,
        config: EnvConfig,
        logger: LoggerType,
        markets: MarketOperations,
        transactions: TransactionOperations,
        deposits: Deposits,
        public_api: PublicAPI,
        private_api: PrivateAPI,
        _state: SubaccountState | None = None,
    ):
        """
        Initialize subaccount (internal use - use from_api() instead).

        Args:
            subaccount_id: Unique identifier for this subaccount
            auth: Authentication context for signing operations
            config: Environment configuration
            markets: Market operations interface
            transactions: Transaction operations interface
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
        self._transactions = transactions

        self._collateral = CollateralOperations(subaccount=self)
        self._orders = OrderOperations(subaccount=self)
        self._trades = TradeOperations(subaccount=self)
        self._positions = PositionOperations(subaccount=self)
        self._rfq = RFQOperations(subaccount=self)
        self._mmp = MMPOperations(subaccount=self)

        self._state: SubaccountState | None = _state

    @classmethod
    def from_api(
        cls,
        *,
        subaccount_id: int,
        auth: AuthContext,
        config: EnvConfig,
        logger: LoggerType,
        markets: MarketOperations,
        transactions: TransactionOperations,
        deposits: Deposits,
        public_api: PublicAPI,
        private_api: PrivateAPI,
    ) -> Subaccount:
        """
        Validate subaccount by fetching its state from the API.

        This performs a network call to verify the subaccount exists and
        caches immutable properties like margin_type and currency.

        Args:
            subaccount_id: Unique identifier for this subaccount
            auth: Authentication context for signing operations
            config: Environment configuration
            markets: Market operations interface
            transactions: Transaction operations interface
            deposits: Deposits interface for deposit operations
            public_api: Public API interface
            private_api: Private API interface for authenticated requests

        Returns:
            Initialized Subaccount instance

        Raises:
            APIError: If subaccount does not exist or API call fails
        """

        params = GetSubaccountRequest(subaccount_id=subaccount_id)
        result = private_api.rpc.get_subaccount(params)
        state = result
        logger.debug(f"Subaccount validated: {state.subaccount_id}")

        return cls(
            subaccount_id=subaccount_id,
            auth=auth,
            config=config,
            logger=logger,
            markets=markets,
            transactions=transactions,
            deposits=deposits,
            public_api=public_api,
            private_api=private_api,
            _state=state,
        )

    def refresh(self) -> Subaccount:
        """Refresh mutable state from API."""

        params = GetSubaccountRequest(subaccount_id=self.id)
        result = self._private_api.rpc.get_subaccount(params)
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
    def transactions(self) -> TransactionOperations:
        """Query transaction status and details."""

        return self._transactions

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
    def trades(self) -> TradeOperations:
        """View trade history."""

        return self._trades

    @property
    def mmp(self) -> MMPOperations:
        """Market maker protection settings."""

        return self._mmp

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

    def plan_deposit(
        self,
        *,
        asset_name: str,
        amount: Decimal,
        gas_priority: GasPriority = GasPriority.MEDIUM,
    ) -> Iterator[DepositStep]:
        """Deposit into this subaccount."""

        risk_universes = self._markets._risk_universes_cache or self._markets.get_risk_universes()

        return self._deposits.plan_deposit(
            risk_universes=risk_universes,
            manager_id=self._state.manager_id,
            subaccount_id=self.id,
            asset_name=asset_name,
            amount=amount,
            from_address=self._auth.account.address,
            fallback_recipient=self._auth.wallet,
            private_key=self._auth.account.key.to_0x_hex(),
            gas_priority=gas_priority,
        )

    def withdraw(
        self,
        *,
        asset_name: str,
        amount: Decimal,
        max_fee_usd: Decimal = Decimal("1"),
        force_batch: bool = False,
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
    ) -> WithdrawalResult:
        """Submits a signed request to withdraw a spot asset out of a subaccount."""

        risk_universes = self._markets._risk_universes_cache or self._markets.get_risk_universes()
        collateral = resolve_collateral(risk_universes, manager_id=self.state.manager_id, asset_name=asset_name)
        recipient = self._auth.account.address  # signer MUST be the recipient

        module_data = WithdrawModuleData(
            protocol_asset=collateral.protocol_asset_address,
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
            nonce=str(signed_action.nonce),
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
        )

        response = self._private_api.rpc.withdraw(params)
        return WithdrawalResult(op_uuid=response.op_uuid, response=response, _transactions=self._transactions)

    def __repr__(self) -> str:
        return f"<{self.__class__.__qualname__}({self.id}) object at {hex(id(self))}>"

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.id < other.id
