from __future__ import annotations

import gc
import logging
import threading

import pytest
import requests

from derive_client._clients.rest.http.session import HTTPSession, _is_retryable, request_timeout_override

_LOGGER = logging.getLogger("derive_test")


def _session(**kwargs) -> HTTPSession:
    kwargs.setdefault("request_timeout", 10.0)
    return HTTPSession(logger=_LOGGER, **kwargs)


def test_public_request_retries_on_retryable_status(http_server):
    path = "/public/get_instruments"
    http_server.route(path, statuses=[503, 200])
    session = _session()
    assert session._send_request(http_server.url(path), b"{}") == b"{}"
    assert http_server.hits[path] == 2


def test_private_request_is_never_retried(http_server):
    path = "/private/order"
    http_server.route(path, statuses=[503, 200])
    session = _session()
    with pytest.raises(requests.HTTPError):
        session._send_request(http_server.url(path), b"{}")
    assert http_server.hits[path] == 1


def test_request_timeout_is_enforced(http_server):
    path = "/public/slow"
    http_server.route(path, delay=1.0)
    session = _session(request_timeout=0.1)
    with pytest.raises(requests.Timeout):
        session._send_request(http_server.url(path), b"{}")


def test_underlying_session_is_closed_when_garbage_collected(caplog):
    logger = logging.getLogger(f"{_LOGGER.name}.gc")
    session = HTTPSession(request_timeout=10.0, logger=logger)
    session.open()

    with caplog.at_level(logging.DEBUG, logger=logger.name):
        del session
        gc.collect()

    assert len(caplog.records) == 1


def test_explicit_close_detaches_the_finalizer(caplog):
    logger = logging.getLogger(f"{_LOGGER.name}.detach")
    session = HTTPSession(request_timeout=10.0, logger=logger)
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
