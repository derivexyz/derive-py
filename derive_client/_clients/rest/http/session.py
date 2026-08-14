from __future__ import annotations

import time
import weakref
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter

from derive_client.data_types import LoggerType

_PUBLIC_PATH_SEGMENT = "public"
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 4
_BACKOFF_FACTOR = 0.2
_BACKOFF_MAX = 10.0


def _is_retryable(url: str) -> bool:
    """Only public reads are safe to replay."""

    return _PUBLIC_PATH_SEGMENT in urlsplit(url).path.split("/")


def _backoff(attempt: int, retry_after: str | None = None) -> float:
    if retry_after is not None:
        try:
            return min(float(retry_after), _BACKOFF_MAX)
        except ValueError:
            pass  # HTTP-date form; fall back to exponential
    return min(_BACKOFF_FACTOR * 2 ** (attempt - 1), _BACKOFF_MAX)


def _close_on_gc(session: requests.Session, logger: LoggerType, name: str) -> None:
    """Close a session whose owner was collected without an explicit close()."""

    logger.debug("%s was garbage collected without explicit close(); closing session automatically", name)
    try:
        session.close()
    except Exception:
        logger.exception("Error closing session in finalizer")


class HTTPSession:
    """HTTP session."""

    def __init__(self, request_timeout: float, logger: LoggerType):
        self._request_timeout = request_timeout
        self._logger = logger

        self._requests_session: requests.Session | None = None
        self._finalizer: weakref.finalize | None = None

    def open(self) -> requests.Session:
        """Lazy session creation"""

        if self._requests_session is not None:
            return self._requests_session

        session = requests.Session()

        # Retries are handled in _send_request: urllib3 gates status retries on
        # allowed_methods, and every request here is a POST.
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
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
        max_attempts = _MAX_ATTEMPTS if _is_retryable(url) else 1
        attempt = 0

        while True:
            attempt += 1
            is_last = attempt >= max_attempts

            try:
                response = session.post(url, data=data, headers=headers, timeout=self._request_timeout)
            except (requests.ConnectionError, requests.Timeout) as e:
                if is_last:
                    self._logger.error("HTTP request failed: %s -> %s", url, e)
                    raise
                delay = _backoff(attempt)
            else:
                if response.status_code not in _RETRY_STATUSES or is_last:
                    if not response.ok:
                        self._logger.error("HTTP %d: %s -> %s", response.status_code, url, response.text[:512])
                    response.raise_for_status()
                    return response.content
                delay = _backoff(attempt, response.headers.get("Retry-After"))

            self._logger.debug("retrying %s in %.2fs (attempt %d/%d)", url, delay, attempt, max_attempts)
            time.sleep(delay)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
