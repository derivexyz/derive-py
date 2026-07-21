"""
Conftest for derive tests
"""

from contextlib import contextmanager
from unittest.mock import patch

import pytest
from pytest_asyncio import is_async_test

OWNER_TEST_WALLET = "0x5cb67F7829d01d9C75385A920De5E51060663374"
SESSION_KEY_PRIVATE_KEY = "0xf20701f7e29ce946e79a70cb53067f837950841f77edb3e685ce370db7ed7bdd"
SUBACCOUNT_ID_75723 = 75723  # Prime Universe

# Second account
ADMIN_TEST_WALLET = "0x5cb67F7829d01d9C75385A920De5E51060663374"


def pytest_collection_modifyitems(items):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@contextmanager
def assert_api_calls(client, expected: int):
    with patch.object(client._session, "_send_request", wraps=client._session._send_request) as api_requests:
        before = api_requests.call_count
        yield
        after = api_requests.call_count
    actual = after - before
    if actual != expected:
        raise AssertionError(f"Expected {expected} HTTP calls, got {actual}. (before={before}, after={after})")
