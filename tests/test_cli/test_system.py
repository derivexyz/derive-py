"""Tests for the `system` command group."""

from derive_client.cli import cli as drv


def test_system_time(runner):
    """Test: `drv system time`"""

    result = runner.invoke(drv, ["system", "time"])
    assert result.exit_code == 0, f"Command failed with output:\n{result.output}"


def test_system_rate_limits(runner):
    """Test: `drv system rate-limits`"""

    result = runner.invoke(drv, ["system", "rate-limits"])
    assert result.exit_code == 0, f"Command failed with output:\n{result.output}"


def test_system_transaction(runner):
    """Test: `drv system transaction`"""

    result = runner.invoke(drv, ["system", "transaction", "514aea9b-c86b-49e5-ba89-620b38477cdd"])
    assert result.exit_code == 0, f"Command failed with output:\n{result.output}"
