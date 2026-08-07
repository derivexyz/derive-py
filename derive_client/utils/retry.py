import functools
from logging import Logger
from typing import Sequence

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from derive_client.utils.logger import get_logger


@functools.lru_cache
def get_retry_session(
    total_retries: int = 5,
    backoff_factor: float = 1.0,
    status_forcelist: Sequence[int] = (429, 500, 502, 503, 504),
    allowed_methods: Sequence[str] = (
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "HEAD",
        "OPTIONS",
    ),
    raise_on_status: bool = False,
    logger: Logger | None = None,
) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        read=total_retries,
        connect=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=list(status_forcelist),
        allowed_methods=list(allowed_methods),
        respect_retry_after_header=True,
        raise_on_status=raise_on_status,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    logger = logger or get_logger()

    def log_response(r, *args, **kwargs):
        logger.info(f"Response {r.request.method} {r.url} (status {r.status_code})")

    session.hooks["response"] = [log_response]
    return session
