from __future__ import annotations

import asyncio
import contextlib
from contextvars import ContextVar
from typing import Iterator
from urllib.parse import urlsplit

import aiohttp

from derive_py.config.constants import USER_AGENT
from derive_py.data_types import AsyncHTTPSessionConfig, LoggerType
from derive_py.utils.logger import get_logger

_PUBLIC_PATH_SEGMENT = "public"

# Context-local override, set by client.timeout(). Task-scoped, so it cannot
# leak across concurrent callers of a shared session.
_request_timeout_override: ContextVar[float | None] = ContextVar("_request_timeout_override", default=None)


@contextlib.contextmanager
def request_timeout_override(seconds: float) -> Iterator[None]:
    """Override the request timeout for the current context."""

    if seconds <= 0:
        raise ValueError("timeout must be positive")

    token = _request_timeout_override.set(float(seconds))
    try:
        yield
    finally:
        _request_timeout_override.reset(token)


def _is_retryable(url: str) -> bool:
    """Only public reads are safe to replay."""

    return _PUBLIC_PATH_SEGMENT in urlsplit(url).path.split("/")


class AsyncHTTPSession:
    """Asynchronous HTTP session. Safe for concurrent tasks on one loop, not across threads."""

    def __init__(self, *, config: AsyncHTTPSessionConfig | None = None, logger: LoggerType | None = None):
        self._config = config if config is not None else AsyncHTTPSessionConfig()
        self._logger = logger if logger is not None else get_logger()

        self._connector: aiohttp.TCPConnector | None = None
        self._aiohttp_session: aiohttp.ClientSession | None = None

    async def open(self) -> aiohttp.ClientSession:
        """Lazy session creation."""

        # No lock: both constructors are synchronous, so nothing can interleave
        # between the check and the assignment on a single event loop.
        if self._aiohttp_session is not None and not self._aiohttp_session.closed:
            return self._aiohttp_session

        self._connector = aiohttp.TCPConnector(
            limit=self._config.limit,
            limit_per_host=self._config.limit_per_host,
            keepalive_timeout=self._config.keepalive_timeout,
        )

        self._aiohttp_session = aiohttp.ClientSession(
            connector=self._connector,
            headers={"User-Agent": USER_AGENT},
        )
        return self._aiohttp_session

    async def close(self) -> None:
        """Explicit cleanup. Idempotent."""

        # Detached synchronously, before the first await: a second close()
        # arriving while this one is suspended must find nothing left to do.
        session, self._aiohttp_session = self._aiohttp_session, None
        connector, self._connector = self._connector, None

        if session is not None and not session.closed:
            try:
                await session.close()
            except Exception:
                self._logger.exception("Error closing session")

        # ClientSession owns the connector it was given and closes it above;
        # this only matters if the session was never created.
        if connector is not None and not connector.closed:
            try:
                await connector.close()
            except Exception:
                self._logger.exception("Error closing connector")

    async def _send_request(
        self,
        url: str,
        data: bytes,
        *,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        session = await self.open()
        max_attempts = self._config.max_attempts if _is_retryable(url) else 1
        attempt = 0

        while True:
            attempt += 1
            is_last = attempt >= max_attempts
            timeout = aiohttp.ClientTimeout(total=self._effective_timeout())
            retry_after: str | None = None

            try:
                async with session.post(url, data=data, headers=headers, timeout=timeout) as response:
                    # aiohttp does not buffer: the body has to be read inside the
                    # context manager, and before raise_for_status to be logged.
                    body = await response.read()
                    status = response.status
                    retry_after = response.headers.get("Retry-After")

                    if status not in self._config.retry_statuses or is_last:
                        if status >= 400:
                            self._logger.error("HTTP %d: %s -> %s", status, url, body[:512])
                        response.raise_for_status()
                        return body
            except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as e:
                # ClientTimeout raises asyncio.TimeoutError, which is not a ClientError.
                if is_last:
                    self._logger.error("HTTP request failed: %s -> %s", url, e)
                    raise
                delay = self._backoff(attempt)
            else:
                delay = self._backoff(attempt, retry_after)

            self._logger.debug("retrying %s in %.2fs (attempt %d/%d)", url, delay, attempt, max_attempts)
            await asyncio.sleep(delay)

    def _backoff(self, attempt: int, retry_after: str | None = None) -> float:
        if retry_after is not None:
            try:
                return min(float(retry_after), self._config.backoff_max)
            except ValueError:
                # HTTP-date form. Logged rather than parsed until we know the venue sends it.
                self._logger.warning("Unhandled Retry-After format, falling back to backoff: %s", retry_after)
        return min(self._config.backoff_factor * 2 ** (attempt - 1), self._config.backoff_max)

    def _effective_timeout(self) -> float:
        override = _request_timeout_override.get()
        return self._config.request_timeout if override is None else override

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
