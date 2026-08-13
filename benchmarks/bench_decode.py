"""Decode costs, as a denominator for the throughput numbers.

Only two things are measured here and neither is a copy of anything: the real
``decode_envelope`` from ``_clients/utils.py``, and a bare ``msgspec`` decode of
the payload bytes into the channel's declared type. The second is a floor. No
arrangement of the receive path can beat one typed decode of the payload, so
whatever a throughput run leaves on the table is the difference between that
floor and the rate actually achieved.

Nothing in this module reaches into the client's internals, so nothing here
needs to be updated when the receive path is rewritten. That is the point: the
baseline it writes stays comparable across the refactor.
"""

from __future__ import annotations

import msgspec

from benchmarks.corpus import build_channels
from benchmarks.harness import Bench
from derive_client._clients.utils import decode_envelope


def benches(seed: int = 0) -> list[Bench]:
    channels = build_channels(seed=seed)
    out: list[Bench] = []

    for channel in channels.values():
        meta = {"channel": channel.wire, "elements": channel.elements}

        # First-pass envelope decode, exactly as the receive loop calls it.
        out.append(
            Bench(
                f"decode/envelope/{channel.name}",
                (lambda raw=channel.raw: decode_envelope(raw)),
                bytes_per_op=channel.size,
                meta=meta,
            )
        )

        # Floor: payload bytes straight into the channel's type, one pass.
        payload = channel.payload()
        decoder = msgspec.json.Decoder(channel.payload_type)
        out.append(
            Bench(
                f"decode/payload/{channel.name}",
                (lambda d=decoder, p=payload: d.decode(p)),
                bytes_per_op=len(payload),
                meta=meta,
            )
        )

        # What the receive loop pays today for calling recv() without
        # decode=False and handing msgspec a str instead of bytes.
        out.append(
            Bench(
                f"decode/utf8/{channel.name}",
                (lambda raw=channel.raw: raw.decode("utf-8")),
                bytes_per_op=channel.size,
                meta=meta,
            )
        )

    return out
