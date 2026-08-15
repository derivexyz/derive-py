"""The channels the benchmarks run against.

One definition per channel, carrying everything the rest of the suite needs:
the wire channel name, the payload type the client decodes into, the
pre-encoded notification frame, and the ``api.py`` method a user would actually
call to subscribe. Nothing here reimplements a payload shape. The types come
from ``channel_models``, so a spec regeneration that changes a payload changes
the benchmark, which is the correct failure mode.

Channel coverage is deliberately narrow: orderbook first, then ticker_slim and
the two public trade tapes. Those are the channels that carry volume. A
benchmark across all twenty channels would take longer to run and tell you
less.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import msgspec

from benchmarks.synth import Synth, SynthConfig
from derive_py._clients.websockets.api import PublicChannels
from derive_py.data_types.channel_models import OrderbookSnapshot, PublicTrade, TickerSlimPayload
from derive_py.data_types.generated_models import AssetType, Quote, SendQuoteRequest

ENCODER = msgspec.json.Encoder()

#: The ``api.py`` subscribe call for a channel, with its channel parameters
#: already bound. Taking the real method rather than a channel string means the
#: benchmark exercises the surface users call, and breaks loudly if a channel's
#: parameters change.
Subscriber = Callable[[PublicChannels, Any], Awaitable[Any]]

INSTRUMENT = "BTC-PERP"


@dataclass(frozen=True)
class Channel:
    """One benchmarkable channel."""

    name: str
    #: Wire channel, e.g. ``orderbook.BTC-PERP.1.20``. Must match what the bound
    #: subscriber produces, or notifications will not route to the handler.
    wire: str
    payload_type: Any
    #: Elements in the payload's dominant collection, for the report.
    elements: int
    raw: bytes
    subscribe: Subscriber

    @property
    def size(self) -> int:
        return len(self.raw)

    def payload(self) -> bytes:
        """The ``data`` member on its own, for the decode floor."""
        envelope = msgspec.json.decode(self.raw)
        return ENCODER.encode(envelope["params"]["data"])


def _notification(wire: str, data: Any) -> bytes:
    return ENCODER.encode({"jsonrpc": "2.0", "method": "subscription", "params": {"channel": wire, "data": data}})


def build_channels(seed: int = 0) -> dict[str, Channel]:
    """The benchmark corpus.

    Orderbook depths span the four the API accepts, so per-frame fixed cost and
    per-level cost can be told apart. Price levels are synthesised
    independently rather than as a monotone ladder: decode cost depends on how
    many strings there are and how long they are, not on their order.
    """
    specs: list[tuple[str, str, Any, int, Subscriber]] = []

    for depth in (1, 10, 20, 100):
        specs.append(
            (
                f"orderbook_d{depth}",
                f"orderbook.{INSTRUMENT}.1.{depth}",
                OrderbookSnapshot,
                depth,
                (
                    lambda channels, handler, d=depth: channels.orderbook_group_depth_by_instrument_name(
                        instrument_name=INSTRUMENT, group=1, depth=d, callback=handler
                    )
                ),
            )
        )

    specs.append(
        (
            "ticker_slim",
            f"ticker_slim.{INSTRUMENT}.100",
            TickerSlimPayload,
            1,
            (
                lambda channels, handler: channels.ticker_slim_interval_by_instrument_name(
                    instrument_name=INSTRUMENT, interval=100, callback=handler
                )
            ),
        )
    )

    for count in (1, 20):
        specs.append(
            (
                f"trades_x{count}",
                f"trades.{INSTRUMENT}",
                list[PublicTrade],
                count,
                (
                    lambda channels, handler: channels.trades_by_instrument_name(
                        instrument_name=INSTRUMENT, callback=handler
                    )
                ),
            )
        )

    specs.append(
        (
            "trades_by_type_x20",
            "trades.perp.BTC",
            list[PublicTrade],
            20,
            (
                lambda channels, handler: channels.trades_by_instrument_type(
                    instrument_type=AssetType.perp, currency="BTC", callback=handler
                )
            ),
        )
    )

    channels: dict[str, Channel] = {}
    for name, wire, payload_type, elements, subscribe in specs:
        data = Synth(SynthConfig(seed=seed, list_len=elements)).build(payload_type)
        channels[name] = Channel(
            name=name,
            wire=wire,
            payload_type=payload_type,
            elements=elements,
            raw=_notification(wire, data),
            subscribe=subscribe,
        )
    return channels


#: Default set for a throughput run: the highest-rate channel at a realistic
#: depth, plus one small and one large frame to bracket it.
DEFAULT_THROUGHPUT_CHANNELS = ("orderbook_d20", "ticker_slim", "trades_x20")


# -- RPC cases -------------------------------------------------------------


@dataclass(frozen=True)
class RPCCase:
    """One request/response pair, driven through the real ``api.py`` method.

    ``result`` is the JSON the feeder echoes back with the client's request id.
    It has to decode into the method's declared return type, so it is built from
    that type rather than hand-written.
    """

    name: str
    params: Any
    result: bytes
    #: ``lambda api, params: api.rpc.<method>(params)``.
    call: Callable[[Any, Any], Awaitable[Any]]

    @property
    def request_size(self) -> int:
        return len(ENCODER.encode(self.params)) if self.params is not None else 2


def build_rpc_cases(seed: int = 0) -> dict[str, RPCCase]:
    """Two shapes: an empty request, and one carrying nested structs.

    ``get_time`` is the floor, a request with no params at all, so it measures
    the fixed cost of a round trip. ``send_quote`` carries a list of nested
    structs, which is the shape where the encoder's handling of unset and null
    fields actually matters.
    """
    synth = Synth(SynthConfig(seed=seed, list_len=4))

    return {
        "get_time": RPCCase(
            name="get_time",
            params=None,
            result=b"1755000000000",
            call=(lambda api, params: api.rpc.get_time(params)),
        ),
        "send_quote": RPCCase(
            name="send_quote",
            params=synth.build(SendQuoteRequest),
            result=ENCODER.encode(synth.build(Quote)),
            call=(lambda api, params: api.rpc.send_quote(params)),
        ),
    }
