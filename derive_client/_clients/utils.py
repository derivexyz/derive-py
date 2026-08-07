from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional, TypeVar

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
from derive_client.data_types import ChecksumAddress, ClientConfig, EnvConfig, Environment, PositionTransfer
from derive_client.data_types.generated_models import (
    AssetType,
    BatchStatus,
    GetTransactionResult,
    Instrument,
    LegUnpricedParams,
    PricedLegParamsAndResponse,
    RPCError,
)
from derive_client.exceptions import WithdrawalFailed, WithdrawalTimeout

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
            smart_contract_wallet=self.wallet,
            session_key_or_wallet_private_key=HexBytes(self.account.key).to_0x_hex(),
        )

    def sign_ws_login(self) -> dict[str, str]:
        return sign_ws_login(
            web3_client=self.w3,  # type: ignore
            smart_contract_wallet=self.wallet,
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


class DeriveJSONRPCError(Exception):
    """Raised when a Derive JSON-RPC error payload is returned."""

    def __init__(self, message_id: str | int, rpc_error: RPCError):
        super().__init__(f"{rpc_error.code}: {rpc_error.message} (message_id={message_id})")
        self.message_id = message_id
        self.rpc_error = rpc_error

    def __str__(self):
        base = f"Derive RPC {self.rpc_error.code}: {self.rpc_error.message}"
        return f"{base}  [data={self.rpc_error.data!r}]" if self.rpc_error.data is not None else base


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


def fetch_all_pages_of_instrument_type(
    markets: MarketOperations,
    instrument_type: AssetType,
    expired: bool,
) -> list[Instrument]:
    """Fetch all instruments of a type, handling pagination."""

    page = 1
    page_size = 1000
    instruments = []

    while True:
        result = markets.get_all_instruments(
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
        tx_result = client.transactions.get(op_uuid=op_uuid)
        if tx_result.transaction_hash != tx_hash:
            tx_hash = tx_result.transaction_hash
            client.logger.info(f"Transaction hash for {op_uuid}: {tx_hash}")

        if tx_result.status is not None and tx_result.status.value.endswith("Error"):
            raise WithdrawalFailed(f"Withdrawal {op_uuid} failed: {tx_result.status}:\n{tx_result}")

        if tx_result.status == BatchStatus.Settled:
            return tx_result

        if time.monotonic() - start > timeout:
            raise WithdrawalTimeout(f"Withdrawal {op_uuid} still {tx_result.status} after {timeout}s:\n{tx_result}")

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
        tx_result = await client.transactions.get(op_uuid=op_uuid)

        if tx_result.transaction_hash != tx_hash:
            tx_hash = tx_result.transaction_hash
            client.logger.info(f"Transaction hash for {op_uuid}: {tx_hash}")

        if tx_result.status is not None and tx_result.status.value.endswith("Error"):
            raise WithdrawalFailed(f"Withdrawal {op_uuid} failed: {tx_result.status}:\n{tx_result}")

        if tx_result.status == BatchStatus.Settled:
            return tx_result

        if time.monotonic() - start > timeout:
            raise WithdrawalTimeout(f"Withdrawal {op_uuid} still {tx_result.status} after {timeout}s:\n{tx_result}")

        await asyncio.sleep(poll_interval)
