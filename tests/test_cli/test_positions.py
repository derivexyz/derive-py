"""Tests for the `position` command group."""

import pytest

from derive_py.cli import cli as drv


def test_position_list(runner):
    """Test: `drv position list`"""

    result = runner.invoke(drv, ["position", "list"])
    assert result.exit_code == 0, f"Command failed with output:\n{result.output}"


def test_position_transfer(runner, transfer_subaccounts):
    """Test: `drv position transfer`"""

    _, to_subaccount = transfer_subaccounts
    result = runner.invoke(drv, ["position", "transfer", "ETH-PERP", "0.01", str(to_subaccount)])

    if "No ETH-PERP position" in result.output or "cannot transfer" in result.output:
        pytest.skip(f"Nothing transferable: {result.output.strip()}")

    assert result.exit_code == 0, f"Command failed with output:\n{result.output}"
    assert "filled" in result.output
