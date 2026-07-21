"""Account management operations."""

from __future__ import annotations

from typing import Optional

from derive_client._clients.rest.http.api import PrivateAPI, PublicAPI
from derive_client._clients.utils import AuthContext
from derive_client.data_types import ChecksumAddress, EnvConfig, LoggerType
from derive_client.data_types.generated_models import (
    EditSessionKeyRequest,
    GetAccountRequest,
    GetAllPortfoliosRequest,
    GetSubaccountsRequest,
    PrivateGetAccountResponse,
    PrivateGetSubaccountsResponse,
    PrivateSessionKeysResponse,
    SessionKey,
    SessionKeysRequest,
    Subaccount,
)


class LightAccount:
    """LightAccount smart contract wallet operations."""

    def __init__(
        self,
        *,
        auth: AuthContext,
        config: EnvConfig,
        logger: LoggerType,
        public_api: PublicAPI,
        private_api: PrivateAPI,
        _state: PrivateGetAccountResponse | None = None,
    ):
        """
        Initialize LightAccount (internal use - use from_api() instead).

        Args:
            auth: Authentication context for signing operations
            config: Environment configuration
            public_api: Public API interface
            private_api: Private API interface for authenticated requests
            _state: Initial state (internal use only)
        """
        self._auth = auth
        self._config = config
        self._logger = logger
        self._public_api = public_api
        self._private_api = private_api
        self._state = _state

    @classmethod
    def from_api(
        cls,
        *,
        auth: AuthContext,
        config: EnvConfig,
        logger: LoggerType,
        public_api: PublicAPI,
        private_api: PrivateAPI,
    ) -> LightAccount:
        """
        Validate LightAccount by fetching its state from the API.

        This performs a network call to verify the wallet exists and that
        the provided session key is registered and valid.

        Args:
            auth: Authentication context for signing operations
            config: Environment configuration
            public_api: Public API interface
            private_api: Private API interface for authenticated requests

        Returns:
            Initialized LightAccount instance

        Raises:
            APIError: If wallet does not exist
        """

        params = GetAccountRequest(wallet=auth.wallet)
        result = private_api.rpc.get_account(params)
        state = result
        logger.debug(f"LightAccount validated: {state.wallet}")

        # Check if the current signer is in the list of valid session keys
        session_keys_params = SessionKeysRequest(wallet=auth.wallet)
        session_keys_result = private_api.rpc.session_keys(session_keys_params)

        valid_signers = {key.public_session_key: key for key in session_keys_result.public_session_keys}
        signer_address = auth.account.address  # type: ignore[attr-defined]
        if signer_address not in valid_signers:
            logger.warning(f"Session key {signer_address} is not registered for wallet {auth.wallet}")
        else:
            logger.debug(f"Session key validated: {signer_address}")

        return cls(
            auth=auth,
            config=config,
            logger=logger,
            public_api=public_api,
            private_api=private_api,
            _state=state,
        )

    @property
    def state(self) -> PrivateGetAccountResponse:
        """Current mutable state."""
        if not self._state:
            msg = "Account state not loaded. Use Account.from_api() to instantiate or call refresh() to load state."
            raise RuntimeError(msg)
        return self._state

    @property
    def address(self) -> ChecksumAddress:
        """LightAccount wallet address."""
        return self._auth.wallet

    def refresh(self) -> LightAccount:
        """Refresh mutable state from API."""
        params = GetAccountRequest(wallet=self._auth.wallet)
        response = self._private_api.rpc.get_account(params)
        self._state = response
        return self

    def session_keys(self) -> PrivateSessionKeysResponse:
        """
        Registered session keys, including details (expiry, scope, IP whitelist)

        A session key is simply an Ethereum wallet.
        Account owners can give other Ethereum wallets temporary access to their accounts via session keys.
        """

        params = SessionKeysRequest(wallet=self.address)
        result = self._private_api.rpc.session_keys(params)
        return result

    def edit_session_key(
        self,
        *,
        public_session_key: str,
        ip_whitelist: Optional[list[str]] = None,
        label: Optional[str] = None,
    ) -> SessionKey:
        """Edits session key parameters such as label and IP whitelist."""

        params = EditSessionKeyRequest(
            wallet=self.address,
            public_session_key=public_session_key,
            ip_whitelist=ip_whitelist,
            label=label,
        )
        result = self._private_api.rpc.edit_session_key(params)
        return result

    def get_all_portfolios(self) -> list[Subaccount]:
        """Get all subaccount portfolios of a wallet"""

        params = GetAllPortfoliosRequest(wallet=self.address)
        result = self._private_api.rpc.get_all_portfolios(params)
        return result

    def get_subaccounts(self) -> PrivateGetSubaccountsResponse:
        """Get all subaccount IDs of an account / wallet"""

        params = GetSubaccountsRequest(wallet=self.address)
        result = self._private_api.rpc.get_subaccounts(params)
        return result

    def get(self) -> PrivateGetAccountResponse:
        """Account details getter"""

        params = GetAccountRequest(wallet=self.address)
        result = self._private_api.rpc.get_account(params)
        return result

    def __repr__(self) -> str:
        return f"<{self.__class__.__qualname__}({self.address}) object at {hex(id(self))}>"
