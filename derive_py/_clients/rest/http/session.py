from __future__ import annotations

import contextlib
import time
import weakref
from contextvars import ContextVar
from typing import Iterator
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter

from derive_py.config.constants import USER_AGENT
from derive_py.data_types import HTTPSessionConfig, LoggerType
from derive_py.utils.logger import get_logger

_PUBLIC_PATH_SEGMENT = "public"

# Context-local override, set by client.timeout(). Task- and thread-scoped, so it
# cannot leak across concurrent callers of a shared session.
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


def _close_on_gc(session: requests.Session, logger: LoggerType, name: str) -> None:
    """Close a session whose owner was collected without an explicit close()."""

    logger.debug("%s was garbage collected without explicit close(); closing session automatically", name)
    try:
        session.close()
    except Exception:
        logger.exception("Error closing session in finalizer")


class HTTPSession:
    """HTTP session. Not thread-safe: use one session per thread."""

    def __init__(self, *, config: HTTPSessionConfig | None = None, logger: LoggerType | None = None):
        self._config = config if config is not None else HTTPSessionConfig()
        self._logger = logger if logger is not None else get_logger()

        self._requests_session: requests.Session | None = None
        self._finalizer: weakref.finalize | None = None

    def open(self) -> requests.Session:
        """Lazy session creation"""

        if self._requests_session is not None:
            return self._requests_session

        session = requests.Session()
        session.headers["User-Agent"] = USER_AGENT

        # Retries are handled in _send_request: urllib3 gates status retries on
        # allowed_methods, and every request here is a POST.
        adapter = HTTPAdapter(
            pool_connections=self._config.pool_connections,
            pool_maxsize=self._config.pool_maxsize,
            max_retries=0,
            pool_block=False,
        )

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        self._requests_session = session
        self._finalizer = weakref.finalize(self, _close_on_gc, session, self._logger, type(self).__name__)
        return self._requests_session

    def close(self):
        """Explicit cleanup"""

        if self._finalizer is not None:
            self._finalizer.detach()
            self._finalizer = None

        if self._requests_session is None:
            return

        self._requests_session.close()
        self._requests_session = None

    def _send_request(
        self,
        url: str,
        data: bytes,
        *,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        session = self.open()
        max_attempts = self._config.max_attempts if _is_retryable(url) else 1
        attempt = 0

        while True:
            attempt += 1
            is_last = attempt >= max_attempts

            try:
                response = session.post(url, data=data, headers=headers, timeout=self._effective_timeout())
            except (requests.ConnectionError, requests.Timeout) as e:
                if is_last:
                    self._logger.error("HTTP request failed: %s -> %s", url, e)
                    raise
                delay = self._backoff(attempt)
            else:
                if response.status_code not in self._config.retry_statuses or is_last:
                    if not response.ok:
                        self._logger.error("HTTP %d: %s -> %s", response.status_code, url, response.text[:512])
                    response.raise_for_status()
                    return response.content
                delay = self._backoff(attempt, response.headers.get("Retry-After"))

            self._logger.debug("retrying %s in %.2fs (attempt %d/%d)", url, delay, attempt, max_attempts)
            time.sleep(delay)

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

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
