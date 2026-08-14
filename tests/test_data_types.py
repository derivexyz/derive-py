"""
The TickerSlimSnapshot wire keys are single letters whose case does not encode
their meaning: A and B are amounts, a and b are prices, while I and M are also
prices. The mapping lives in scripts/generate_models.py by hand, so nothing in
codegen catches an inverted pair. These tests do, offline.

The same struct is generated twice, once for REST and once for the channel, so
both are checked.
"""

from decimal import Decimal

import msgspec
import pytest

from derive_py.data_types.channel_models import TickerSlimSnapshot as ChannelTicker
from derive_py.data_types.generated_models import TickerSlimSnapshot as RestTicker

MODELS = pytest.mark.parametrize("model", [RestTicker, ChannelTicker], ids=["rest", "channel"])

# A book straddling the mark, with a size that could not be a price.
PAYLOAD = msgspec.json.encode(
    {
        "A": "0.4",
        "B": "0.3",
        "I": "1876.20",
        "M": "1876.20",
        "a": "1876.41",
        "b": "1876.01",
        "maxp": "2000",
        "minp": "1700",
        "t": 1,
        "stats": {"c": "0", "h": "0", "l": "0", "n": 0, "oi": "0", "p": "0", "pr": "0", "v": "0"},
    }
)

EXPECTED_WIRE_KEYS = {
    "best_ask_amount": "A",
    "best_bid_amount": "B",
    "index_price": "I",
    "mark_price": "M",
    "best_ask_price": "a",
    "best_bid_price": "b",
}


@MODELS
def test_wire_keys_are_not_transposed(model):
    """Guards the exact pairing, so a swap fails here rather than in a trade."""

    mapping = dict(zip(model.__struct_fields__, model.__struct_encode_fields__))
    for name, wire_key in EXPECTED_WIRE_KEYS.items():
        assert mapping[name] == wire_key, f"{name} decodes {mapping[name]!r}, expected {wire_key!r}"


@MODELS
def test_the_book_straddles_the_mark(model):
    """The property a transposed mapping cannot satisfy."""

    ticker = msgspec.json.decode(PAYLOAD, type=model)

    assert Decimal(ticker.best_bid_price) < Decimal(ticker.mark_price) < Decimal(ticker.best_ask_price)
    assert Decimal(ticker.best_bid_amount) == Decimal("0.3")
    assert Decimal(ticker.best_ask_amount) == Decimal("0.4")
