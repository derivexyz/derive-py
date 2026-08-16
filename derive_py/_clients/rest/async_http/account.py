"""Account management operations."""

from __future__ import annotations

from typing import Optional

import msgspec

from derive_py._clients.rest.async_http.api import AsyncPrivateAPI, AsyncPublicAPI
from derive_py._clients.rest.async_http.history import HistoryOperations
from derive_py._clients.utils import AuthContext, log_session_key_status, unset_if_none
from derive_py._web3.action_signing import SessionKeyModuleData, WhitelistedRecipientModuleData
from derive_py.data_types import ChainConfig, ChecksumAddress, LoggerType, OffchainScope, ProtocolScope
from derive_py.data_types.generated_models import (
    EditSessionKeyRequest,
    GetAccountRequest,
    GetAllPortfoliosRequest,
    GetSubaccountsRequest,
    PrivateGetAccountResponse,
    PrivateGetSubaccountsResponse,
    PrivateSessionKeysResponse,
    PrivateSetSessionKeyResponse,
    SessionKey,
    SessionKeysRequest,
    SetSessionKeyRequest,
    Subaccount,
    UpdateWhitelistedRecipientsRequest,
    UpdateWhitelistedRecipientsResponse,
)


class LightAccount:
    """LightAccount smart contract wallet operations."""

    def __init__(
        self,
        *,
        auth: AuthContext,
        config: ChainConfig,
        logger: LoggerType,
        public_api: AsyncPublicAPI,
        private_api: AsyncPrivateAPI,
        _state: PrivateGetAccountResponse | None = None,
    ):
        """
        Initialize LightAccount (internal use - use from_api() instead).

        Args:
            auth: Authentication context for signing operations
            config: Chain configuration
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
        self._history = HistoryOperations.for_wallet(self)

    @classmethod
    async def from_api(
        cls,
        *,
        auth: AuthContext,
        config: ChainConfig,
        logger: LoggerType,
        public_api: AsyncPublicAPI,
        private_api: AsyncPrivateAPI,
    ) -> LightAccount:
        """
        Validate LightAccount by fetching its state from the API.

        This performs a network call to verify the wallet exists and that
        the provided session key is registered and valid.

        Args:
            auth: Authentication context for signing operations
            config: Chain configuration
            public_api: Public API interface
            private_api: Private API interface for authenticated requests

        Returns:
            Initialized LightAccount instance

        Raises:
            APIError: If wallet does not exist
        """

        params = GetAccountRequest(wallet=auth.wallet)
        state = await private_api.rpc.get_account(params)
        logger.debug(f"LightAccount validated: {state.wallet}")

        signer = auth.account.address
        if signer == auth.wallet:  # v3 does not require registration for the owner.
            logger.debug(f"Signing as wallet owner {auth.wallet}")
        else:
            session_keys_params = SessionKeysRequest(wallet=auth.wallet)
            session_keys_response = await private_api.rpc.session_keys(session_keys_params)
            registered = {key.public_session_key: key for key in session_keys_response.public_session_keys}
            log_session_key_status(registered.get(signer), signer=signer, wallet=auth.wallet, logger=logger)

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

    async def refresh(self) -> LightAccount:
        """Refresh mutable state from API."""
        params = GetAccountRequest(wallet=self._auth.wallet)
        response = await self._private_api.rpc.get_account(params)
        self._state = response
        return self

    async def session_keys(self) -> PrivateSessionKeysResponse:
        """Registered session keys, including details (expiry, scope, IP whitelist)."""

        params = SessionKeysRequest(wallet=self.address)
        result = await self._private_api.rpc.session_keys(params)
        return result

    async def set_session_key(
        self,
        *,
        expiry_sec: int,
        public_session_key: str,
        offchain_scopes: list[OffchainScope],
        protocol_scopes: list[ProtocolScope],
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
        ip_whitelist: list[str] | None = None,
        label: str | None = None,
        subaccount_ids: list[int] | None = None,
    ) -> PrivateSetSessionKeyResponse:
        """Authorizes a new session key for a wallet from a signed action."""

        wallet = self._auth.wallet

        module_data = SessionKeyModuleData(
            session_key=public_session_key,
            expiry_sec=expiry_sec,
            protocol_scopes=protocol_scopes,
            subaccount_ids=subaccount_ids or [],
        )

        module_address = self._config.contracts.CREATE_SESSION_KEY_MODULE
        signed_action = self._auth.sign_action(
            subaccount_id=0,
            nonce=nonce,
            module_address=module_address,
            module_data=module_data,
            signature_expiry_sec=signature_expiry_sec,
        )

        params = SetSessionKeyRequest(
            expiry_sec=expiry_sec,
            nonce=str(signed_action.nonce),
            offchain_scopes=list(map(str, offchain_scopes)),
            protocol_scopes=list(map(str, protocol_scopes)),
            public_session_key=public_session_key,
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
            wallet=wallet,
            ip_whitelist=unset_if_none(ip_whitelist),
            label=unset_if_none(label),
            subaccount_ids=unset_if_none(subaccount_ids),
        )

        result = await self._private_api.rpc.set_session_key(params)
        return result

    async def edit_session_key(
        self,
        *,
        public_session_key: str,
        ip_whitelist: Optional[list[str]] = None,
        label: Optional[str] = None,
        offchain_scopes: Optional[list[OffchainScope]] = None,
    ) -> SessionKey:
        """Edits session key parameters such as label and IP whitelist."""

        params = EditSessionKeyRequest(
            wallet=self.address,
            public_session_key=public_session_key,
            ip_whitelist=unset_if_none(ip_whitelist),
            label=unset_if_none(label),
            offchain_scopes=list(map(str, offchain_scopes)) if offchain_scopes is not None else msgspec.UNSET,
        )
        result = await self._private_api.rpc.edit_session_key(params)
        return result

    async def update_whitelisted_recipients(
        self,
        *,
        add: list[str],
        remove: list[str],
        nonce: Optional[int] = None,
        signature_expiry_sec: Optional[int] = None,
    ) -> UpdateWhitelistedRecipientsResponse:
        """Adds and/or removes recipient wallet addresses on an account's
        transfer whitelist. Resulting list is (current UNION add) MINUS remove."""

        wallet = self._auth.wallet

        module_data = WhitelistedRecipientModuleData(add=add, remove=remove)

        module_address = self._config.contracts.WHITELISTED_RECIPIENT_MODULE
        signed_action = self._auth.sign_action(
            subaccount_id=0,
            nonce=nonce,
            module_address=module_address,
            module_data=module_data,
            signature_expiry_sec=signature_expiry_sec,
        )

        params = UpdateWhitelistedRecipientsRequest(
            add=add,
            remove=remove,
            nonce=signed_action.nonce,
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
            wallet=wallet,
        )

        result = await self._private_api.rpc.update_whitelisted_recipients(params)
        return result

    async def get_all_portfolios(self) -> list[Subaccount]:
        """Get all subaccount portfolios of a wallet"""

        params = GetAllPortfoliosRequest(wallet=self.address)
        result = await self._private_api.rpc.get_all_portfolios(params)
        return result

    async def get_subaccounts(self) -> PrivateGetSubaccountsResponse:
        """Get all subaccount IDs of an account / wallet"""

        params = GetSubaccountsRequest(wallet=self.address)
        result = await self._private_api.rpc.get_subaccounts(params)
        return result

    async def get(self) -> PrivateGetAccountResponse:
        """Account details getter"""

        params = GetAccountRequest(wallet=self.address)
        result = await self._private_api.rpc.get_account(params)
        return result

    @property
    def history(self) -> HistoryOperations:
        """Historical records across every subaccount of this wallet."""

        return self._history

    def __repr__(self) -> str:
        return f"<{self.__class__.__qualname__}({self.address}) object at {hex(id(self))}>"
