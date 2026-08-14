from __future__ import annotations

import gc
import logging

import pytest
import requests

from derive_client._clients.rest.http.session import HTTPSession, _is_retryable

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


def test_underlying_session_is_closed_when_garbage_collected():
    session = _session()
    underlying = session.open()
    closed: list[bool] = []
    underlying.close = lambda: closed.append(True)  # type: ignore[method-assign]

    del session
    gc.collect()

    assert closed == [True]


def test_versioned_public_path_is_retryable():
    assert _is_retryable("https://api.derive.xyz/v3/public/get_instruments")
    assert not _is_retryable("https://api.derive.xyz/v3/private/order")
