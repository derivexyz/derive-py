"""Tests for the `market` command group."""

import pytest

from derive_client.cli import cli as drv


@pytest.mark.parametrize(
    "args",
    [
        ("--all",),
        ("USDC",),
        ("ETH",),
    ],
)
def test_market_currency(runner, args):
    """Test: `drv market currency`"""

    result = runner.invoke(drv, ["market", "currency", *args])
    assert result.exit_code == 0, f"Command failed with output:\n{result.output}"


@pytest.mark.parametrize(
    "args",
    [
        ("ETH-USDC",),  # spot
        ("ETH-PERP",),  # perp
        ("--universe", "PRIME"),
        ("--type", "perp"),
        ("--currency", "ETH", "--type", "option", "--limit", "5"),
    ],
)
def test_market_instrument(runner, args):
    """Test: `drv market instrument`"""

    result = runner.invoke(drv, ["market", "instrument", *args])
    assert result.exit_code == 0, f"Command failed with output:\n{result.output}"


@pytest.mark.parametrize(
    "args",
    [
        ("BTC-PERP",),
        ("--type", "erc20"),
        ("--type", "perp", "--limit", "5"),
        # ("--type", "option", "--currency", "ETH", "--limit", "5"),
    ],
)
def test_market_ticker(runner, args):
    """Test: `drv market ticker`"""

    result = runner.invoke(drv, ["market", "ticker", *args])
    assert result.exit_code == 0, f"Command failed with output:\n{result.output}"
    assert "No tickers found" not in result.output, "Empty response, command paths not exercised"


def test_market_ticker_empty(runner):
    """Test: `drv market ticker` handles an expiry with no live options."""

    args = ["--type", "option", "--currency", "ETH", "--expiry-date", "20251226"]
    result = runner.invoke(drv, ["market", "ticker", *args])
    assert result.exit_code == 0, f"Command failed with output:\n{result.output}"
    assert "No tickers found" in result.output


@pytest.mark.parametrize(
    "args",
    [
        ("currency",),  # neither name nor --all
        ("instrument", "ETH-PERP", "--type", "perp"),  # name plus filter
        ("instrument", "--universe", "NOPE"),  # unknown universe
        ("ticker",),  # no name, no --type
        ("ticker", "--type", "option"),  # options need --currency
        ("ticker", "--type", "perp", "--expiry-date", "20251226"),
    ],
)
def test_market_usage_errors(runner, args):
    """Test: `drv market` argument validation."""

    result = runner.invoke(drv, ["market", *args])
    assert result.exit_code != 0, f"Expected failure, got:\n{result.output}"


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("PRIME",),
    ],
)
def test_market_universe(runner, args):
    """Test: `drv market universe`"""

    result = runner.invoke(drv, ["market", "universe", *args])
    assert result.exit_code == 0, f"Command failed with output:\n{result.output}"
