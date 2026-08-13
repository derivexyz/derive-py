"""A web3 BaseProvider that fails over across an ordered list of HTTP endpoints.

Deliberately NOT the v2 rotating-provider machinery: no health scoring, no
background probes, no weighted round-robin, no per-call rotation. That existed
to serve a six-chain bridging workflow v3 does not have. What remains is an
ordered list, a cooldown, and reset-to-head once a cooldown expires.

Failover lives here rather than at call sites for three reasons:
  - ContractRegistry._cache and Deposits.contract bind Contract objects to one
    Web3 instance, so swapping the Web3 out on failure orphans them.
  - Every helper in tx.py and erc20.py takes `w3`, so provider-level failover
    covers all of them with no call-site changes.
  - This sits BELOW sign_transaction, so a retry of eth_sendRawTransaction can
    only ever resend the identical signed payload. It is structurally incapable
    of rebuilding a transaction with a fresh nonce, which is the retry bug that
    actually loses money.
"""

from __future__ import annotations

import itertools
import threading
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Protocol, TypeAlias

from eth_typing import URI, HexStr
from requests.exceptions import ChunkedEncodingError, HTTPError, Timeout, TooManyRedirects
from requests.exceptions import ConnectionError as RequestsConnectionError
from web3 import HTTPProvider, Web3
from web3.providers.base import BaseProvider
from web3.providers.rpc.utils import ExceptionRetryConfiguration
from web3.types import RPCEndpoint, RPCError, RPCResponse

from derive_client.config import CONFIGS, resolve_rpc_endpoints
from derive_client.data_types import Environment, LoggerType
from derive_client.exceptions import AllEndpointsFailed, ChainIdMismatch

# What a JSON-RPC param actually is at this boundary. bytes is included
# deliberately: web3 formats eth_sendRawTransaction to hex before it reaches a
# provider, but nothing in the type system enforces that, and _raw_tx_hash has
# to handle both. Sequence/Mapping rather than list/dict so the alias stays
# covariant and a plain list[str] from a caller is assignable.
RPCParam: TypeAlias = "str | int | float | bool | bytes | None | Sequence[RPCParam] | Mapping[str, RPCParam]"
RPCParams: TypeAlias = "Sequence[RPCParam]"


class RPCProvider(Protocol):
    """Structural, so tests can inject fakes without a socket. Read-only
    property rather than a mutable attribute: an attribute member would be
    invariant, and neither HTTPProvider's URI nor a fake's plain str would
    satisfy it. endpoint_uri is Optional on HTTPProvider, hence `| None`."""

    @property
    def endpoint_uri(self) -> str | None: ...

    def make_request(self, method: RPCEndpoint, params: RPCParams) -> RPCResponse: ...


class _EndpointUnavailable(Exception):
    """Internal: this endpoint failed in a way another endpoint may not."""


# 400/401/403 are endpoint-level rejections, not consensus answers: a plan
# gate, a missing key, a geo-block. Observed in the wild as HTTP 400 wrapping
# {"code":35,"message":"chain is not available on free plan"}. Retrying
# elsewhere either succeeds or yields AllEndpointsFailed listing N identical
# refusals, which diagnoses a genuinely malformed request just as clearly.
_RETRYABLE_HTTP_STATUS = frozenset({400, 401, 403, 408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 529})

# Infrastructure rather than consensus. -32601 is included because a node
# lacking eth_feeHistory should hand off, not kill the call.
_RETRYABLE_RPC_CODES = frozenset({-32002, -32004, -32005, -32601, -32603})

# Allowlist, not denylist. -32000 is used by public nodes for both "execution
# reverted" and half their infra failures, so the code alone cannot classify.
# Anything unrecognised propagates to the caller.
_RETRYABLE_MESSAGES = (
    "rate limit",
    "too many requests",
    "exceeded",
    "quota",
    "capacity",
    "throttl",
    "timeout",
    "timed out",
    "temporarily unavailable",
    "service unavailable",
    "internal error",
    "try again",
    "overloaded",
    "busy",
    "header not found",
    "block not found",
    "unknown block",
    "missing trie node",
    "no state available",
    "cannot query unfinalized",
    "not synced",
    "syncing",
    "resource not found",
)

# Checked FIRST, so a substring collision cannot promote a consensus error
# into a retryable one.
_NEVER_RETRY_MESSAGES = (
    "execution reverted",
    "nonce too low",
    "nonce too high",
    "replacement transaction underpriced",
    "transaction underpriced",
    "insufficient funds",
    "intrinsic gas too low",
    "gas required exceeds",
    "max fee per gas less than block base fee",
    "invalid sender",
    "oversized data",
    "exceeds block gas limit",
)

_ALREADY_KNOWN_MESSAGES = ("already known", "known transaction", "already exists")

_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    RequestsConnectionError,
    Timeout,
    HTTPError,
    TooManyRedirects,
    ChunkedEncodingError,
    # A proxy or captive portal returning an HTML error page decodes as a JSON
    # failure, not an HTTP one.
    ValueError,
)


def _uri(provider: RPCProvider) -> str:
    """endpoint_uri is Optional on HTTPProvider. These strings are only ever
    log text and failure-map keys, so a placeholder beats propagating None."""

    return provider.endpoint_uri or "<unset>"


def _error_message(error: RPCError | str) -> str:
    return (error if isinstance(error, str) else error.get("message", "")).lower()


def _is_retryable_exception(exc: BaseException) -> bool:
    if isinstance(exc, _EndpointUnavailable):
        return True
    if isinstance(exc, HTTPError):
        return exc.response is not None and exc.response.status_code in _RETRYABLE_HTTP_STATUS
    return isinstance(exc, _RETRYABLE_EXCEPTIONS)


def _is_retryable_rpc_error(error: RPCError | str) -> bool:
    message = _error_message(error)
    if any(fragment in message for fragment in _NEVER_RETRY_MESSAGES):
        return False
    if any(fragment in message for fragment in _RETRYABLE_MESSAGES):
        return True
    # A bare string error carries no code, so the message was its only signal.
    return not isinstance(error, str) and error.get("code") in _RETRYABLE_RPC_CODES


def _is_already_known(error: RPCError | str) -> bool:
    message = _error_message(error)
    return any(fragment in message for fragment in _ALREADY_KNOWN_MESSAGES)


def _raw_tx_hash(params: RPCParams) -> HexStr:
    """keccak of the raw signed payload, which IS the transaction hash."""

    if not params:
        raise ValueError("eth_sendRawTransaction called without params")

    raw = params[0]
    if isinstance(raw, (bytes, bytearray)):
        return Web3.to_hex(Web3.keccak(bytes(raw)))
    if isinstance(raw, str):
        return Web3.to_hex(Web3.keccak(hexstr=HexStr(raw)))
    raise TypeError(f"eth_sendRawTransaction payload is {type(raw).__name__}, expected hex string or bytes")


def _describe(exc: BaseException) -> str:
    """HTTPError's repr is just the status line. Gateways put the actual
    reason in the body, and raise_for_status() fires before anything parses
    it, so the useful half is lost unless we reach for it here."""

    if isinstance(exc, HTTPError) and exc.response is not None:
        body = exc.response.text.strip()[:200]
        return f"{exc!r} body={body}" if body else repr(exc)
    return repr(exc)


def _build_http_providers(endpoints: Sequence[str], timeout: float) -> list[HTTPProvider]:
    # errors= must be passed explicitly: ExceptionRetryConfiguration defaults it
    # to None and then hands it to a non-optional pydantic field, so the
    # zero-argument construction raises.
    #
    # retries=1 means one attempt, no same-endpoint retry. web3's default of 5
    # with backoff is ~25s of stall against a hanging node before failover can
    # even begin, which is the exact symptom this class exists to fix. The loop
    # lives in HTTPProvider._make_request, below make_request, so it applies to
    # the calls this class makes directly.
    retry = ExceptionRetryConfiguration(
        errors=(RequestsConnectionError, HTTPError, Timeout, TooManyRedirects),
        retries=1,
        backoff_factor=0.1,
    )
    return [
        HTTPProvider(
            URI(uri),
            request_kwargs={"timeout": timeout},
            exception_retry_configuration=retry,
        )
        for uri in endpoints
    ]


class FailoverProvider(BaseProvider):
    def __init__(
        self,
        endpoints: Sequence[str] = (),
        *,
        chain_id: int,
        logger: LoggerType,
        timeout: float = 5.0,
        cooldown: float = 60.0,
        providers: Sequence[RPCProvider] | None = None,
    ) -> None:
        super().__init__()
        if providers is None:
            if not endpoints:
                raise ValueError("FailoverProvider requires at least one endpoint.")
            providers = _build_http_providers(endpoints, timeout)

        self._providers: list[RPCProvider] = list(providers)
        self._chain_id = chain_id
        self._logger = logger
        self._cooldown = cooldown

        # RLock, not Lock: asyncio.to_thread in async_utils runs make_request on
        # worker threads, and _candidates() is reached from inside pin().
        self._lock = threading.RLock()
        self._counter = itertools.count(1)
        self._cooldown_until: dict[int, float] = {}
        self._verified: set[int] = set()
        self._disabled: dict[int, str] = {}
        self._active: int | None = None
        self._generation = 0
        self._pinning = 0

    @property
    def generation(self) -> int:
        """Increments whenever the serving endpoint changes. wait_for_finality
        reads this to avoid classifying a broadcast as dropped when the only
        thing that happened is that a different node, which never saw it,
        started answering."""

        return self._generation

    @property
    def endpoint_uri(self) -> str | None:
        with self._lock:
            if self._active is None:
                return None
            return _uri(self._providers[self._active])

    @contextmanager
    def pin(self) -> Iterator[None]:
        """Suppress reset-to-head for the duration. Failover on genuine failure
        still happens. Use around any group of calls that must see a coherent
        view of chain state: nonce plus fee history plus eth_call in one build."""

        with self._lock:
            self._pinning += 1
        try:
            yield
        finally:
            with self._lock:
                self._pinning -= 1

    def _candidates(self) -> list[int]:
        now = time.monotonic()
        with self._lock:
            live = [i for i in range(len(self._providers)) if i not in self._disabled]
            ready = [i for i in live if self._cooldown_until.get(i, 0.0) <= now]
            cooling = sorted(
                (i for i in live if self._cooldown_until.get(i, 0.0) > now),
                key=lambda i: self._cooldown_until[i],
            )
            order = ready + cooling
            if self._pinning and self._active is not None and self._active in order:
                active = self._active
                order = [active] + [i for i in order if i != active]
            return order

    def _mark_ok(self, index: int) -> None:
        with self._lock:
            self._cooldown_until.pop(index, None)
            if self._active != index:
                if self._active is not None:
                    self._generation += 1
                    self._logger.info("RPC endpoint switched to %s", _uri(self._providers[index]))
                self._active = index

    def _mark_failed(self, index: int, reason: str) -> None:
        with self._lock:
            self._cooldown_until[index] = time.monotonic() + self._cooldown
        self._logger.warning(
            "RPC endpoint %s failed (%s), cooling down %.0fs",
            _uri(self._providers[index]),
            reason,
            self._cooldown,
        )

    def _local_response(self, result: str) -> RPCResponse:
        return RPCResponse(jsonrpc="2.0", id=next(self._counter), result=result)

    def _ensure_verified(self, index: int) -> None:
        """One eth_chainId probe per endpoint, ever. A mismatch permanently
        disables that endpoint rather than only raising: one bad entry should
        not kill an otherwise working set, and the endpoint is barred from
        serving anything afterwards. Call verify_all() to fail fast instead."""

        with self._lock:
            if index in self._verified:
                return

        provider = self._providers[index]
        response = provider.make_request(RPCEndpoint("eth_chainId"), [])
        if (error := response.get("error")) is not None:
            raise _EndpointUnavailable(f"eth_chainId probe failed: {error}")

        # RPCResponse.result is declared Any; narrow it here rather than
        # letting an untyped value reach int().
        result = response.get("result")
        if not isinstance(result, str):
            raise _EndpointUnavailable(f"eth_chainId returned {result!r}, expected a hex string")
        try:
            actual = int(result, 16)
        except ValueError as exc:
            raise _EndpointUnavailable(f"eth_chainId returned unparsable {result!r}") from exc

        if actual != self._chain_id:
            message = f"{_uri(provider)} reports chain id {actual}, expected {self._chain_id}. Endpoint disabled."
            with self._lock:
                self._disabled[index] = message
            self._logger.error(message)
            raise ChainIdMismatch(message, endpoint=_uri(provider), expected=self._chain_id, actual=actual)

        with self._lock:
            self._verified.add(index)

    def verify_all(self) -> None:
        """Eagerly probe every endpoint. Not called from __init__ on purpose:
        client construction stays network-free."""

        for index in range(len(self._providers)):
            self._ensure_verified(index)

    def make_request(self, method: RPCEndpoint, params: RPCParams) -> RPCResponse:
        # Served locally. Every endpoint we route to has been verified against
        # this value, so a node cannot tell us anything we do not already know,
        # and prepare_transaction reads it once per build.
        if method == "eth_chainId":
            return self._local_response(hex(self._chain_id))

        failures: dict[str, str] = {}

        for index in self._candidates():
            provider = self._providers[index]
            uri = _uri(provider)
            try:
                self._ensure_verified(index)
                response = provider.make_request(method, params)
            except ChainIdMismatch as exc:
                failures[uri] = str(exc)
                continue
            except Exception as exc:
                if not _is_retryable_exception(exc):
                    raise
                self._mark_failed(index, repr(exc))
                failures[uri] = repr(exc)
                continue

            error = response.get("error")
            if error is None:
                self._mark_ok(index)
                return response

            # Identical payload means identical hash, so a second node saying
            # "already known" means the transaction IS in the mempool. Returning
            # the error would push the caller towards resubmitting with a fresh
            # nonce against a transaction that is about to mine.
            if method == "eth_sendRawTransaction" and _is_already_known(error):
                self._mark_ok(index)
                try:
                    tx_hash = _raw_tx_hash(params)
                except (ValueError, TypeError) as exc:
                    self._logger.warning("Could not derive tx hash from params (%s), returning node error", exc)
                    return response
                self._logger.info("Transaction already known to %s, returning its hash", uri)
                return self._local_response(tx_hash)

            if not _is_retryable_rpc_error(error):
                self._mark_ok(index)
                return response

            self._mark_failed(index, str(error))
            failures[uri] = str(error)

        with self._lock:
            failures.update({_uri(self._providers[i]): reason for i, reason in self._disabled.items()})
        raise AllEndpointsFailed(
            f"All {len(self._providers)} RPC endpoints failed for {method}: {failures}",
            method=str(method),
            failures=failures,
        )

    def is_connected(self, show_traceback: bool = False) -> bool:
        try:
            self.make_request(RPCEndpoint("eth_blockNumber"), [])
        except Exception:  # noqa: BLE001 - a probe reports False, it does not raise
            return False
        return True


def make_web3(
    env: Environment,
    *,
    rpc_endpoints: str | Sequence[str] | None = None,
    logger: LoggerType,
    timeout: float = 5.0,
) -> Web3:
    """The single construction site for a Web3 instance. All clients call this."""

    endpoints = resolve_rpc_endpoints(env, rpc_endpoints)
    provider = FailoverProvider(endpoints, chain_id=CONFIGS[env].chain_id, logger=logger, timeout=timeout)
    return Web3(provider)


@contextmanager
def pinned_provider(w3: Web3) -> Iterator[None]:
    """No-op unless the Web3 is backed by a FailoverProvider."""

    provider = w3.provider
    if not isinstance(provider, FailoverProvider):
        yield
        return
    with provider.pin():
        yield


def provider_generation(w3: Web3) -> int | None:
    """None when there is nothing that can fail over, which callers read as
    'endpoint changes are not a thing here'."""

    provider = w3.provider
    return provider.generation if isinstance(provider, FailoverProvider) else None
