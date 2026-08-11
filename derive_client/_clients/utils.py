from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Iterator, Optional, TypeVar

import msgspec
from dotenv import load_dotenv
from eth_account.signers.local import LocalAccount
from hexbytes import HexBytes
from pydantic import BaseModel
from web3 import Web3

from derive_client._web3.action_signing import (
    ModuleData,
    SignedAction,
    get_action_nonce,
    sign_rest_auth_header,
    sign_ws_login,
)
from derive_client.data_types import (
    ChecksumAddress,
    ClientConfig,
    EnvConfig,
    Environment,
    PositionTransfer,
    RiskUniverseID,
)
from derive_client.data_types.generated_models import (
    AssetType,
    BatchStatus,
    GetAllInstrumentsResponse,
    GetTransactionResult,
    Instrument,
    LegUnpricedParams,
    PaginatedVaultRequestHistory,
    PricedLegParamsAndResponse,
    RPCError,
    VaultActionResponse,
    VaultRequestId,
)
from derive_client.exceptions import (
    DeriveJSONRPCError,
    SettlementFailed,
    SettlementTimeout,
    VaultRequestFailed,
    VaultRequestTimeout,
)

if TYPE_CHECKING:
    from websockets import Data

    from derive_client import AsyncHTTPClient, HTTPClient, WebSocketClient
    from derive_client._clients.rest.async_http.markets import MarketOperations as AsyncMarketOperations
    from derive_client._clients.rest.http.markets import MarketOperations


T = TypeVar("T")
InstrumentT = TypeVar("InstrumentT", LegUnpricedParams, PricedLegParamsAndResponse, PositionTransfer)


def sort_by_instrument_name(items: Iterable[InstrumentT]) -> list[InstrumentT]:
    """Derive API mandate: 'Legs must be sorted by instrument name'."""
    return sorted(items, key=lambda item: item.instrument_name)


def get_default_signature_expiry_sec() -> int:
    """
    Compute a conservative default signature_expiry_sec (Unix epoch seconds).

    Derive's v3 API enforces signature_expiry_sec between 300 and
    10,368,000 seconds (120 days) from now (RPC 11011: "Invalid signature
    expiry"). The previous implementation returned now + 1 year
    (31,536,000s), outside that bound — already inconsistent with this
    docstring's own stated ~330s reasoning, only surfaced once tested
    against the live v3 API.
    """
    utc_time_now_s = int(time.time())
    return utc_time_now_s + 3600  # 1 hour, safely within [300, 10_368_000]


@dataclass
class AuthContext:
    wallet: ChecksumAddress
    w3: Web3
    account: LocalAccount
    config: EnvConfig

    @property
    def signer(self) -> ChecksumAddress:
        return ChecksumAddress(self.account.address)

    @property
    def signed_headers(self):
        return sign_rest_auth_header(
            web3_client=self.w3,  # type: ignore
            derive_wallet=self.wallet,
            session_key_or_wallet_private_key=HexBytes(self.account.key).to_0x_hex(),
        )

    def sign_ws_login(self) -> dict[str, str]:
        return sign_ws_login(
            web3_client=self.w3,  # type: ignore
            derive_wallet=self.wallet,
            session_key_or_wallet_private_key=HexBytes(self.account.key).to_0x_hex(),
        )

    def sign_action(
        self,
        module_address: ChecksumAddress,
        module_data: ModuleData,
        subaccount_id: int,
        signature_expiry_sec: Optional[int] = None,
        nonce: Optional[int] = None,
    ) -> SignedAction:
        """Sign action using v2-action-signing library."""

        nonce = nonce or get_action_nonce()
        signature_expiry_sec = signature_expiry_sec or get_default_signature_expiry_sec()

        action = SignedAction(
            subaccount_id=subaccount_id,
            owner=self.wallet,
            signer=self.signer,
            signature_expiry_sec=signature_expiry_sec,
            nonce=nonce,
            module_address=module_address,
            module_data=module_data,
            DOMAIN_SEPARATOR=self.config.DOMAIN_SEPARATOR,
            ACTION_TYPEHASH=self.config.ACTION_TYPEHASH,
        )
        action.sign(HexBytes(self.account.key).to_0x_hex())
        return action


def try_cast_response(response: bytes, response_schema: type[T]) -> T:
    try:
        return msgspec.json.decode(response, type=response_schema)
    except msgspec.ValidationError:
        message = json.loads(response)
        rpc_error = RPCError(**message["error"])
        raise DeriveJSONRPCError(message_id=message.get("id", ""), rpc_error=rpc_error)
    raise ValueError(f"Failed to decode response data: {response}")


class RateLimitConfig(BaseModel, frozen=True):
    name: str
    matching_tps: int
    per_instrument_tps: int
    non_matching_tps: int
    connections_per_ip: int
    burst_multiplier: int
    burst_reset_seconds: int


class RateLimitProfile(StrEnum):
    TRADER = "trader"
    MARKET_MAKER = "market_maker"


RATE_LIMIT: dict[RateLimitProfile, RateLimitConfig] = {
    RateLimitProfile.TRADER: RateLimitConfig(
        name="Trader",
        matching_tps=1,
        per_instrument_tps=1,
        non_matching_tps=5,
        connections_per_ip=4,
        burst_multiplier=5,
        burst_reset_seconds=5,
    ),
    RateLimitProfile.MARKET_MAKER: RateLimitConfig(
        name="Market Maker",
        matching_tps=500,
        per_instrument_tps=10,
        non_matching_tps=500,
        connections_per_ip=64,
        burst_multiplier=5,
        burst_reset_seconds=5,
    ),
}


class JSONRPCEnvelope(msgspec.Struct, omit_defaults=True):
    """
    Minimal JSON-RPC 2.0 envelope for hot-path dispatch.
    Works for both HTTP and WebSocket transports.

    Fields use msgspec.Raw to defer nested deserialization.
    """

    # Request/response ID (absent for notifications)
    id: str | int | msgspec.UnsetType = msgspec.UNSET

    # Protocol version
    jsonrpc: str = "2.0"

    # Server->client notifications/subscriptions
    method: str | msgspec.UnsetType = msgspec.UNSET
    params: msgspec.Raw | msgspec.UnsetType = msgspec.UNSET

    # RPC response fields (mutually exclusive)
    result: msgspec.Raw | msgspec.UnsetType = msgspec.UNSET
    error: msgspec.Raw | msgspec.UnsetType = msgspec.UNSET


def decode_envelope(data: Data) -> JSONRPCEnvelope:
    """
    Fast first-pass decode of JSON-RPC envelope.

    Used in hot path to determine message routing without
    deserializing nested result/error/params fields.
    """
    return msgspec.json.decode(data, type=JSONRPCEnvelope)


def decode_result(envelope: JSONRPCEnvelope, result_schema: type[T]) -> T:
    """
    Deserialize RPC result field into typed schema.

    Should only be called after verifying envelope.result is present.
    Raises DeriveJSONRPCError if envelope contains error instead.

    Args:
        envelope: Already-decoded envelope from decode_envelope()
        result_schema: Target struct type for result field

    Returns:
        Deserialized result

    Raises:
        DeriveJSONRPCError: If envelope contains error field
        ValueError: If envelope has neither result nor error
    """

    if envelope.error is not msgspec.UNSET:
        error = msgspec.json.decode(envelope.error, type=RPCError)
        message_id = envelope.id if envelope.id is not msgspec.UNSET else ""
        raise DeriveJSONRPCError(message_id=message_id, rpc_error=error)

    if envelope.result is msgspec.UNSET:
        raise ValueError(f"Envelope has neither result nor error (id={envelope.id})")

    return msgspec.json.decode(envelope.result, type=result_schema)


def encode_json_exclude_none(obj: msgspec.Struct | None) -> bytes:
    """
    Encode msgspec Struct omitting None and UNSET values.

    The Derive API requires optional fields to be omitted entirely
    rather than sent as null. Methods with no request parameters pass
    None (EmptyRequest); encode as an empty JSON object.
    """
    if obj is None:
        return b"{}"

    data = msgspec.structs.asdict(obj)
    filtered = {k: v for k, v in data.items() if v is not None and v is not msgspec.UNSET}
    return msgspec.json.encode(filtered)


def unset_if_none(value: T | None) -> T | msgspec.UnsetType:
    """Map None to UNSET, leaving every other value alone."""
    return msgspec.UNSET if value is None else value


async def async_fetch_all_pages_of_instrument_type(
    markets: AsyncMarketOperations,
    instrument_type: AssetType,
    expired: bool,
) -> list[Instrument]:
    """Fetch all instruments of a type, handling pagination."""

    page = 1
    page_size = 1000
    instruments = []

    while True:
        result = await markets.get_all_instruments(
            expired=expired,
            instrument_type=instrument_type,
            page=page,
            page_size=page_size,
        )
        instruments.extend(result.instruments)
        if not result.pagination or page >= result.pagination.num_pages:
            break
        page += 1

    return instruments


def infer_instrument_type(*, instrument_name: str) -> AssetType:
    """
    Infer instrument type from name pattern.

    Patterns:
    - PERP: Contains '-PERP' suffix
    - Option: Ends with '-P' or '-C' (put/call)
    - ERC20: Everything else (typically short token pairs like 'ETH-USDC')
    """
    if instrument_name.endswith("-PERP"):
        return AssetType.perp
    elif instrument_name.endswith("-P") or instrument_name.endswith("-C"):
        return AssetType.option
    else:
        return AssetType.erc20


def load_client_config(session_key_path: Optional[Path] = None, env_file: Optional[Path] = None) -> ClientConfig:
    """
    Load and validate client config from .env and optional session-key file.

    Raises:
      ValueError on missing/invalid config.
    """

    dotenv_path = env_file or Path.cwd() / ".env"
    load_dotenv(dotenv_path=dotenv_path)

    session_key = session_key_path.read_text().strip() if session_key_path else os.environ.get("DERIVE_SESSION_KEY")
    wallet_str = os.environ.get("DERIVE_WALLET")
    subaccount_id_str = os.environ.get("DERIVE_SUBACCOUNT_ID")
    env_name = os.environ.get("DERIVE_ENV", "PROD").upper()

    missing = []
    if not session_key:
        missing.append("DERIVE_SESSION_KEY")
    if not wallet_str:
        missing.append("DERIVE_WALLET")
    if not subaccount_id_str:
        missing.append("DERIVE_SUBACCOUNT_ID")

    if missing:
        msg = "Missing required configuration: " + ", ".join(missing)
        msg += f"\nSearched for .env at: {dotenv_path.absolute()}"
        raise ValueError(msg)

    assert session_key and wallet_str and subaccount_id_str, "type-checker"

    try:
        wallet_checksum = ChecksumAddress(wallet_str)
    except Exception as e:
        raise ValueError(f"Invalid wallet address: {e}")

    try:
        subaccount_id = int(subaccount_id_str)
    except Exception:
        raise ValueError(f"Invalid subaccount ID '{subaccount_id_str}': must be an integer")

    try:
        env = Environment[env_name]
    except Exception:
        raise ValueError(f"Invalid DERIVE_ENV '{env_name}': expected one of {[e.name for e in Environment]}")

    return ClientConfig(
        session_key=session_key,
        wallet=wallet_checksum,
        subaccount_id=subaccount_id,
        env=env,
    )


def wait_for_settlement(
    client: HTTPClient, op_uuid: str, timeout: int = 300, poll_interval: float = 2.0
) -> GetTransactionResult:
    """Poll until BatchStatus.Settled or a terminal *Error status."""

    tx_hash = None
    start = time.monotonic()
    while True:
        tx_result = client.system.get_transaction(op_uuid=op_uuid)
        if tx_result.transaction_hash != tx_hash:
            tx_hash = tx_result.transaction_hash
            client.logger.info(f"Transaction hash for {op_uuid}: {tx_hash}")

        if tx_result.status is not None and tx_result.status.value.endswith("Error"):
            raise SettlementFailed(f"Operation {op_uuid} failed: {tx_result.status}", tx_result)

        if tx_result.status == BatchStatus.Settled:
            return tx_result

        if time.monotonic() - start > timeout:
            raise SettlementTimeout(f"Operation {op_uuid} still {tx_result.status} after {timeout}s", tx_result)

        time.sleep(poll_interval)


async def async_wait_for_settlement(
    client: AsyncHTTPClient | WebSocketClient,
    op_uuid: str,
    timeout: int = 300,
    poll_interval: float = 2.0,
) -> GetTransactionResult:
    """Poll until BatchStatus.Settled or a terminal *Error status."""

    tx_hash = None
    start = time.monotonic()
    while True:
        tx_result = await client.system.get_transaction(op_uuid=op_uuid)

        if tx_result.transaction_hash != tx_hash:
            tx_hash = tx_result.transaction_hash
            client.logger.info(f"Transaction hash for {op_uuid}: {tx_hash}")

        if tx_result.status is not None and tx_result.status.value.endswith("Error"):
            raise SettlementFailed(f"Operation {op_uuid} failed: {tx_result.status}", tx_result)

        if tx_result.status == BatchStatus.Settled:
            return tx_result

        if time.monotonic() - start > timeout:
            raise SettlementTimeout(f"Operation {op_uuid} still {tx_result.status} after {timeout}s", tx_result)

        await asyncio.sleep(poll_interval)


#: Statuses a vault request can still move on from. Everything else is treated
#: as terminal, deliberately: the API reference and the vaults guide document
#: two different vocabularies for this field ("applied/cancelled/rejected"
#: versus "sequencer_applied/user_cancel/curator_reject/protocol_reject"), the
#: generated model types it as a bare str, and an unknown status should stop the
#: poll rather than hang it.
VAULT_REQUEST_PENDING_STATUSES = frozenset({"enqueued", "requested"})

#: Terminal statuses that are not a successful settlement. user_cancel is
#: absent: cancelling is something the caller asked for, not a failure.
VAULT_REQUEST_FAILURE_STATUSES = frozenset({"curator_reject", "protocol_reject", "rejected", "expired"})


def _match_vault_request(history: PaginatedVaultRequestHistory, request_id: VaultRequestId):
    """Find one request in the wallet's history by its composite id.

    A vault request has no op_uuid until a curator settles it, so there is
    nothing for wait_for_settlement to poll; the history row is the only handle
    on a queued intent's outcome.
    """

    for action in history.actions:
        if (
            action.vault_nonce == request_id.vault_nonce
            and action.vault_subaccount_id == request_id.vault_subaccount_id
            and action.wallet.lower() == request_id.wallet.lower()
        ):
            return action
    return None


def wait_for_vault_request(
    client: HTTPClient,
    request_id: VaultRequestId,
    timeout: int = 900,
    poll_interval: float = 5.0,
    page_size: int = 50,
) -> "VaultActionResponse":
    """Poll until a queued vault intent reaches a terminal status.

    Settlement is at the curator's discretion, within a 14-day SLA, so the
    default timeout is a convenience for tests and examples rather than a bound
    on the protocol: a request that outlives it is still queued, not lost.

    Raises VaultRequestFailed on a rejection or an expiry, and returns the row
    for a settled or cancelled request.
    """

    action = None
    start = time.monotonic()
    while True:
        history = client.vaults.request_history(page=1, page_size=page_size)
        found = _match_vault_request(history, request_id)
        if found is not None:
            if found.status != getattr(action, "status", None):
                client.logger.info(f"Vault request {request_id.vault_nonce}: {found.status}")
            action = found
            if action.status not in VAULT_REQUEST_PENDING_STATUSES:
                if action.status in VAULT_REQUEST_FAILURE_STATUSES:
                    reason = action.error_reason or action.status
                    raise VaultRequestFailed(f"Vault request {request_id.vault_nonce} failed: {reason}", action)
                return action

        if time.monotonic() - start > timeout:
            status = action.status if action else "not yet in history"
            raise VaultRequestTimeout(f"Vault request {request_id.vault_nonce} still {status} after {timeout}s", action)

        time.sleep(poll_interval)


async def async_wait_for_vault_request(
    client: AsyncHTTPClient | WebSocketClient,
    request_id: VaultRequestId,
    timeout: int = 900,
    poll_interval: float = 5.0,
    page_size: int = 50,
) -> "VaultActionResponse":
    """Poll until a queued vault intent reaches a terminal status."""

    action = None
    start = time.monotonic()
    while True:
        history = await client.vaults.request_history(page=1, page_size=page_size)
        found = _match_vault_request(history, request_id)
        if found is not None:
            if found.status != getattr(action, "status", None):
                client.logger.info(f"Vault request {request_id.vault_nonce}: {found.status}")
            action = found
            if action.status not in VAULT_REQUEST_PENDING_STATUSES:
                if action.status in VAULT_REQUEST_FAILURE_STATUSES:
                    reason = action.error_reason or action.status
                    raise VaultRequestFailed(f"Vault request {request_id.vault_nonce} failed: {reason}", action)
                return action

        if time.monotonic() - start > timeout:
            status = action.status if action else "not yet in history"
            raise VaultRequestTimeout(f"Vault request {request_id.vault_nonce} still {status} after {timeout}s", action)

        await asyncio.sleep(poll_interval)


def wait_for_new_curated_vault(
    client: HTTPClient,
    known_vault_ids: set[int],
    timeout: int = 300,
    poll_interval: float = 5.0,
) -> int:
    """Resolve the subaccount id of a vault this wallet just created.

    create_vault returns an op_uuid but not the new subaccount id, so the id is
    recovered by diffing the curated set. Call wait_for_settlement on the
    op_uuid first; this only bridges the gap between the operation settling and
    the vault appearing in the curated list.

    Racy if the wallet creates two vaults concurrently. It should not.
    """

    start = time.monotonic()
    while True:
        curated = set(client.vaults.list_curated().subaccount_ids)
        if new := sorted(curated - known_vault_ids):
            return new[0]
        if time.monotonic() - start > timeout:
            raise SettlementTimeout(f"No new curated vault appeared within {timeout}s", None)
        time.sleep(poll_interval)


def iter_instrument_pages(
    *,
    markets: MarketOperations,
    instrument_type: AssetType,
    expired: bool = False,
    currency: Optional[str] = None,
    risk_universe_id: Optional[RiskUniverseID] | None = None,
    page_size: int = 1000,
) -> Iterator[GetAllInstrumentsResponse]:
    """Lazily yield pages of instruments.

    No request is issued until a page is pulled, so a caller that stops early
    pays for only the pages it consumed. Pages are yielded whole to keep
    `pagination.count` reachable.
    """

    page = 1
    while True:
        result = markets.get_all_instruments(
            expired=expired,
            instrument_type=instrument_type,
            currency=currency,
            page=page,
            page_size=page_size,
            risk_universe_id=risk_universe_id,
        )
        yield result

        if not result.instruments or page >= result.pagination.num_pages:
            return
        page += 1


def fetch_all_pages_of_instrument_type(
    markets: MarketOperations,
    instrument_type: AssetType,
    expired: bool,
) -> list[Instrument]:
    """Fetch all instruments of a type, handling pagination."""

    return [
        instrument
        for page in iter_instrument_pages(markets=markets, instrument_type=instrument_type, expired=expired)
        for instrument in page.instruments
    ]
