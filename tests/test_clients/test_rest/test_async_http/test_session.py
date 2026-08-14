from __future__ import annotations

import asyncio
import logging
import time

import aiohttp
import pytest
import pytest_asyncio

from derive_client._clients.rest.async_http.session import (
    AsyncHTTPSession,
    _is_retryable,
    request_timeout_override,
)
from derive_client.data_types import AsyncHTTPSessionConfig

_LOGGER = logging.getLogger("derive_test")


@pytest_asyncio.fixture
async def make_session():
    sessions: list[AsyncHTTPSession] = []

    def _make(**kwargs) -> AsyncHTTPSession:
        session = AsyncHTTPSession(config=AsyncHTTPSessionConfig(**kwargs), logger=_LOGGER)
        sessions.append(session)
        return session

    yield _make

    for session in sessions:
        await session.close()


@pytest.mark.asyncio
async def test_public_request_retries_on_retryable_status(http_server, make_session):
    path = "/public/get_instruments"
    http_server.route(path, statuses=[503, 200])
    session = make_session(backoff_factor=0.0)
    assert await session._send_request(http_server.url(path), b"{}") == b"{}"
    assert http_server.hits[path] == 2


@pytest.mark.asyncio
async def test_private_request_is_never_retried(http_server, make_session):
    path = "/private/order"
    http_server.route(path, statuses=[503, 200])
    session = make_session()
    with pytest.raises(aiohttp.ClientResponseError):
        await session._send_request(http_server.url(path), b"{}")
    assert http_server.hits[path] == 1


@pytest.mark.asyncio
async def test_non_retryable_status_is_not_retried(http_server, make_session):
    path = "/public/get_instruments"
    http_server.route(path, statuses=[400, 200])
    session = make_session(backoff_factor=0.0)
    with pytest.raises(aiohttp.ClientResponseError):
        await session._send_request(http_server.url(path), b"{}")
    assert http_server.hits[path] == 1


@pytest.mark.asyncio
async def test_request_timeout_is_enforced(http_server, make_session):
    path = "/public/slow"
    http_server.route(path, delay=1.0)
    session = make_session(request_timeout=0.1, max_attempts=1)
    with pytest.raises(asyncio.TimeoutError):
        await session._send_request(http_server.url(path), b"{}")


@pytest.mark.asyncio
async def test_retry_after_is_honoured_and_capped(http_server, make_session):
    path = "/public/get_instruments"
    http_server.route(path, statuses=[429, 200], headers={"Retry-After": "600"})
    session = make_session(backoff_max=0.05)

    started = time.monotonic()
    assert await session._send_request(http_server.url(path), b"{}") == b"{}"

    assert time.monotonic() - started < 1.0
    assert http_server.hits[path] == 2


@pytest.mark.asyncio
async def test_retries_are_bounded_by_max_attempts(http_server, make_session):
    path = "/public/get_instruments"
    http_server.route(path, statuses=[503])
    session = make_session(max_attempts=2, backoff_factor=0.0)

    with pytest.raises(aiohttp.ClientResponseError):
        await session._send_request(http_server.url(path), b"{}")

    assert http_server.hits[path] == 2


@pytest.mark.asyncio
async def test_timeout_override_applies_only_within_the_block(http_server, make_session):
    path = "/public/slow"
    http_server.route(path, delay=0.3)
    session = make_session(request_timeout=0.1, max_attempts=1)

    with request_timeout_override(2.0):
        assert await session._send_request(http_server.url(path), b"{}") == b"{}"

    with pytest.raises(asyncio.TimeoutError):
        await session._send_request(http_server.url(path), b"{}")


@pytest.mark.asyncio
async def test_timeout_override_is_inherited_only_by_tasks_spawned_inside(make_session):
    session = make_session(request_timeout=0.1)

    async def effective() -> float:
        return session._effective_timeout()

    with request_timeout_override(2.0):
        assert session._effective_timeout() == 2.0
        inside = asyncio.create_task(effective())

    outside = asyncio.create_task(effective())

    assert await inside == 2.0
    assert await outside == 0.1


@pytest.mark.asyncio
async def test_closing_twice_is_idempotent(make_session):
    session = make_session()
    await session.open()
    await session.close()
    await session.close()


def test_versioned_public_path_is_retryable():
    assert _is_retryable("https://api.derive.xyz/v3/public/get_instruments")
    assert not _is_retryable("https://api.derive.xyz/v3/private/order")
