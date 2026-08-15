from __future__ import annotations

import gc
import logging
import threading
import time

import pytest
import requests

from derive_py._clients.rest.http.session import USER_AGENT, HTTPSession, _is_retryable, request_timeout_override
from derive_py.data_types import HTTPSessionConfig, LoggerType

_LOGGER = logging.getLogger("derive_test")


def _session(logger: LoggerType = _LOGGER, **kwargs) -> HTTPSession:
    return HTTPSession(config=HTTPSessionConfig(**kwargs), logger=logger)


def _isolated_logger(suffix: str) -> logging.Logger:
    """Child logger so sessions leaked by other tests, swept by our gc.collect(), stay out of caplog."""

    return logging.getLogger(f"{_LOGGER.name}.{suffix}")


def test_public_request_retries_on_retryable_status(http_server):
    path = "/public/get_instruments"
    http_server.route(path, statuses=[503, 200])
    session = _session(backoff_factor=0.0)
    assert session._send_request(http_server.url(path), b"{}") == b"{}"
    assert http_server.hits[path] == 2


def test_private_request_is_never_retried(http_server):
    path = "/private/order"
    http_server.route(path, statuses=[503, 200])
    session = _session()
    with pytest.raises(requests.HTTPError):
        session._send_request(http_server.url(path), b"{}")
    assert http_server.hits[path] == 1


def test_non_retryable_status_is_not_retried(http_server):
    path = "/public/get_instruments"
    http_server.route(path, statuses=[400, 200])
    session = _session(backoff_factor=0.0)
    with pytest.raises(requests.HTTPError):
        session._send_request(http_server.url(path), b"{}")
    assert http_server.hits[path] == 1


def test_request_timeout_is_enforced(http_server):
    path = "/public/slow"
    http_server.route(path, delay=1.0)
    session = _session(request_timeout=0.1)
    with pytest.raises(requests.Timeout):
        session._send_request(http_server.url(path), b"{}")


def test_retry_after_is_honoured_and_capped(http_server):
    path = "/public/get_instruments"
    http_server.route(path, statuses=[429, 200], headers={"Retry-After": "600"})
    session = _session(backoff_max=0.05)

    started = time.monotonic()
    assert session._send_request(http_server.url(path), b"{}") == b"{}"

    assert time.monotonic() - started < 1.0
    assert http_server.hits[path] == 2


def test_underlying_session_is_closed_when_garbage_collected(caplog):
    logger = _isolated_logger("gc")
    session = _session(logger=logger)
    session.open()

    with caplog.at_level(logging.DEBUG, logger=logger.name):
        del session
        gc.collect()

    assert len(caplog.records) == 1


def test_explicit_close_detaches_the_finalizer(caplog):
    logger = _isolated_logger("detach")
    session = _session(logger=logger)
    session.open()
    session.close()

    with caplog.at_level(logging.DEBUG, logger=logger.name):
        del session
        gc.collect()

    assert not caplog.records


def test_versioned_public_path_is_retryable():
    assert _is_retryable("https://api.derive.xyz/v3/public/get_instruments")
    assert not _is_retryable("https://api.derive.xyz/v3/private/order")


def test_timeout_override_applies_only_within_the_block(http_server):
    path = "/public/slow"
    http_server.route(path, delay=0.3)
    session = _session(request_timeout=0.1)

    with request_timeout_override(2.0):
        assert session._send_request(http_server.url(path), b"{}") == b"{}"

    with pytest.raises(requests.Timeout):
        session._send_request(http_server.url(path), b"{}")


def test_timeout_override_does_not_leak_across_threads():
    session = _session(request_timeout=0.1)
    seen: list[float] = []

    with request_timeout_override(2.0):
        assert session._effective_timeout() == 2.0
        thread = threading.Thread(target=lambda: seen.append(session._effective_timeout()))
        thread.start()
        thread.join()

    assert seen == [0.1]


def test_retries_are_bounded_by_max_attempts(http_server):
    path = "/public/get_instruments"
    http_server.route(path, statuses=[503])
    session = _session(max_attempts=2, backoff_factor=0.0)

    with pytest.raises(requests.HTTPError):
        session._send_request(http_server.url(path), b"{}")

    assert http_server.hits[path] == 2


def test_user_agent_reports_a_resolved_version():
    assert "unknown" not in USER_AGENT
