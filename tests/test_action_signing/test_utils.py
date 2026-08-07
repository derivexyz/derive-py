"""Unit tests for the action-signing helpers.

Pure functions: no network, no credentials, no fixtures.
"""

import time
from decimal import Decimal

import pytest

from derive_client._web3.action_signing.utils import (
    MAX_INT_256,
    decimal_to_big_int,
    get_action_nonce,
    scale_amount,
)

ADDRESS = "0x8772185a1516f0d61fC1c2524926BfC69F95d698"


class TestGetActionNonce:
    def test_is_nanosecond_scale(self):
        """v3 rejects millisecond- and microsecond-scale nonces."""
        nonce = get_action_nonce()
        assert len(str(nonce)) == 19
        assert abs(nonce - time.time_ns()) < 10**9

    def test_does_not_decrease(self):
        """Withdraw, transfer, session key and whitelist require increasing nonces."""
        nonces = [get_action_nonce() for _ in range(1000)]
        assert nonces == sorted(nonces)


class TestDecimalToBigInt:
    """e18 scaling for trade and RFQ prices and amounts."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (Decimal("1"), 10**18),
            (Decimal("0.1"), 10**17),
            (Decimal("0"), 0),
            (Decimal("-1"), -(10**18)),  # negative legs are valid
            (Decimal("1000"), 1000 * 10**18),
        ],
    )
    def test_scales(self, value, expected):
        assert decimal_to_big_int(value) == expected

    def test_rejects_out_of_range(self):
        with pytest.raises(ValueError):
            decimal_to_big_int(Decimal(MAX_INT_256))


class TestScaleAmount:
    """Native-decimal scaling for withdrawals and spot transfers."""

    @pytest.mark.parametrize(
        ("value", "decimals", "expected"),
        [
            (Decimal("1"), 18, 10**18),
            (Decimal("0.1"), 18, 10**17),
            (Decimal("1"), 6, 10**6),
            (Decimal("1.5"), 6, 1_500_000),
            (Decimal("0.000001"), 6, 1),
        ],
    )
    def test_scales(self, value, decimals, expected):
        assert scale_amount(value, decimals) == expected

    def test_defaults_to_e18(self):
        assert scale_amount(Decimal("1")) == 10**18

    def test_rejects_excess_precision(self):
        """Truncating here would silently underpay by a fraction of a unit."""
        with pytest.raises(ValueError):
            scale_amount(Decimal("1.5000005"), 6)

    def test_allows_zero(self):
        """max_fee_usd is legitimately 0 on internal transfers."""
        assert scale_amount(Decimal("0")) == 0

    def test_rejects_negative(self):
        with pytest.raises(ValueError):
            scale_amount(Decimal("-1"))
