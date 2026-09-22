"""
Conftest for derive tests
"""

from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from dotenv import dotenv_values
from pytest_asyncio import is_async_test

from derive_py.data_types import PositionTransfer

REPO_ROOT = Path(__file__).parent.parent
ENV_TEMPLATE = REPO_ROOT / ".env.template"

_TEMPLATE = {key: value for key, value in dotenv_values(ENV_TEMPLATE).items() if value is not None}


def env_template_value(key: str) -> str:
    """Read one value from .env.template, the single source of test credentials."""

    if (value := _TEMPLATE.get(key)) is None:
        raise RuntimeError(f"{key} is missing from {ENV_TEMPLATE}")
    return value


#: Second subaccount of the test wallet, the destination a position transfer
#: moves into. Pinned here rather than in .env.template, which carries only
#: what the client itself needs to connect. Update it when the test wallet is
#: rotated; `tests/test_action_signing/expected.py` records the pair in use.
TRANSFER_TO_SUBACCOUNT = 86286


@pytest.fixture(scope="session")
def transfer_subaccounts() -> tuple[int, int]:
    """The subaccount pair a position transfer moves between, source first.

    Both must sit in the SAME risk universe or the transfer is rejected, which
    is why they travel as a pair rather than being picked off the wallet's
    subaccount list.

    A fixture and not a module constant: read at import time in this file, a
    missing DERIVE_SUBACCOUNT_ID fails collection for the WHOLE suite, not just
    for the two tests that transfer anything.
    """

    return int(env_template_value("DERIVE_SUBACCOUNT_ID")), TRANSFER_TO_SUBACCOUNT


def pytest_collection_modifyitems(items):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
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


def _min_position_transfer(position) -> PositionTransfer:
    """The smallest transferable slice of a position as a transfer object."""

    step = Decimal(position.amount_step)
    full = Decimal(position.amount)
    magnitude = min(step, abs(full))
    return PositionTransfer(position.instrument_name, -magnitude if full < 0 else magnitude)


@pytest.fixture
def min_position_transfer():
    """Smallest transferable slice of a position. Sync, usable from async tests."""

    return _min_position_transfer
