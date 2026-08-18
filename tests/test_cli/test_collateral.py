"""Tests for the `collateral` command group."""

from derive_py.cli import cli as drv


def test_collateral_get(runner):
    """Test: `drv collateral get`"""

    result = runner.invoke(drv, ["collateral", "get"])
    assert result.exit_code == 0, f"Command failed with output:\n{result.output}"
