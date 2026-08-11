"""How many WebSocket messages per second the client sustains.

This is the headline number and the reason the rest of the suite exists.
Everything runs through the surface a user touches: ``WebSocketSession``, and
subscription methods on the generated ``PublicChannels``. Nothing reaches into
the client's internals, so the measurement stays valid across a rewrite of the
receive path.

A feeder in a separate process supplies the traffic. Separate process because
in-process it would contend for the same GIL as the client and the result would
measure the benchmark. Synthetic traffic because a live feed cannot answer the
question: subscription rates are bounded by the exchange's publish intervals
and by whatever the market happens to be doing, so a live run measures Derive,
not the client. The feeder is faster than any exchange on purpose.

What the number means
---------------------
Messages per second the client pulls off a socket, decodes into the channel's
typed payload, and hands to a handler that does nothing. A handler that does
work is the user's workload, not ours, and belongs in their measurement rather
than this one.

The clock is stopped by the *handler* count, not by the receive loop. That
matters while dispatch is fire-and-forget: a loop that drains the socket while
handler tasks accumulate is fast in the wrong sense. Peak RSS is reported next
to the rate for the same reason.
"""

from __future__ import annotations

import asyncio
import logging
import multiprocessing as mp
import resource
import statistics
import sys
import time
from dataclasses import dataclass

from websockets.asyncio.client import connect

from benchmarks.corpus import ENCODER, Channel, RPCCase, build_channels, build_rpc_cases
from benchmarks.feeder import feeder_main
from benchmarks.harness import Result, _git_rev
from derive_client._clients.websockets.api import PrivateAPI, PublicAPI
from derive_client._clients.websockets.session import WebSocketSession


def _quiet_logger() -> logging.Logger:
    """Errors only, on an isolated logger.

    A burst logs a connect, a subscribe and a close, which is a page of noise
    between the numbers at thirty bursts a run. Not a NullHandler: a handler
    that raises is reported through this same logger, and swallowing that would
    turn a broken run into a 300 second timeout with no explanation.
    """
    logger = logging.getLogger("benchmarks.session")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.propagate = False
        logger.setLevel(logging.ERROR)
    return logger


@dataclass
class Burst:
    messages: int
    bytes_total: int
    elapsed_s: float
    peak_rss_kib: int

    @property
    def ns_per_message(self) -> float:
        return self.elapsed_s / self.messages * 1e9


def _peak_rss_kib() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


# -- notification throughput ----------------------------------------------


async def _client_burst(port: int, channel: Channel, count: int, warmup: int, async_handler: bool) -> Burst:
    state = {"n": 0, "t0": 0.0, "t1": 0.0}
    finished = asyncio.Event()

    # Warmup frames arrive on the same channel through the same handler, so the
    # clock starts on the first frame after them. An in-band start marker would
    # need its own subscription and would perturb what is being measured.
    first, last = warmup + 1, warmup + count

    def on_message(_payload) -> None:
        state["n"] += 1
        if state["n"] == first:
            state["t0"] = time.perf_counter()
        elif state["n"] == last:
            state["t1"] = time.perf_counter()
            finished.set()

    async def on_message_async(payload) -> None:
        on_message(payload)

    session = WebSocketSession(
        url=f"ws://127.0.0.1:{port}", request_timeout=10.0, reconnect=False, logger=_quiet_logger()
    )
    await session.open()
    try:
        api = PublicAPI(session)
        await channel.subscribe(api.channels, on_message_async if async_handler else on_message)
        await asyncio.wait_for(finished.wait(), timeout=300.0)
    finally:
        await session.close()

    # The clock spans arrival of frame (warmup + 1) to arrival of frame
    # (warmup + count): count - 1 inter-arrival intervals.
    measured = count - 1
    return Burst(
        messages=measured,
        bytes_total=measured * channel.size,
        elapsed_s=state["t1"] - state["t0"],
        peak_rss_kib=_peak_rss_kib(),
    )


async def _control_burst(port: int, channel: Channel, count: int, warmup: int) -> Burst:
    """Ceiling: recv and discard. No session, no decode, no handler."""
    async with connect(f"ws://127.0.0.1:{port}", max_size=16 * 1024 * 1024) as ws:
        await ws.send('{"jsonrpc":"2.0","method":"subscribe","params":{"channels":["' + channel.wire + '"]},"id":1}')
        await ws.recv()  # subscribe result

        # Drain the warmup and the first measured frame before starting the
        # clock: the feeder idles briefly between the two phases, and billing
        # that idle to the client would make the ceiling look slower than the
        # thing it bounds.
        for _ in range(warmup + 1):
            await ws.recv(decode=False)
        t0 = time.perf_counter()
        for _ in range(count - 1):
            await ws.recv(decode=False)
        elapsed = time.perf_counter() - t0

    measured = count - 1
    return Burst(
        messages=measured,
        bytes_total=measured * channel.size,
        elapsed_s=elapsed,
        peak_rss_kib=_peak_rss_kib(),
    )


# -- RPC throughput --------------------------------------------------------


async def _rpc_burst(port: int, case: RPCCase, count: int, warmup: int, concurrency: int) -> Burst:
    """Round trips per second through the real generated RPC method.

    At concurrency 1 this is latency and loopback dominates it. Raise it to put
    the client's encode and decode on the critical path instead, which is what
    a market maker with several requests in flight actually sees.
    """
    session = WebSocketSession(
        url=f"ws://127.0.0.1:{port}", request_timeout=30.0, reconnect=False, logger=_quiet_logger()
    )
    await session.open()
    try:
        api = PrivateAPI(session) if case.name == "send_quote" else PublicAPI(session)

        async def batch(n: int) -> None:
            for _ in range(0, n, concurrency):
                await asyncio.gather(*(case.call(api, case.params) for _ in range(concurrency)))

        await batch(warmup)
        t0 = time.perf_counter()
        await batch(count)
        elapsed = time.perf_counter() - t0
    finally:
        await session.close()

    return Burst(
        messages=count,
        bytes_total=count * case.request_size,
        elapsed_s=elapsed,
        peak_rss_kib=_peak_rss_kib(),
    )


async def _rpc_control_burst(port: int, case: RPCCase, count: int, warmup: int, concurrency: int) -> Burst:
    """Ceiling for the RPC path: hand-rolled frames, no session, no structs.

    Without this the RPC numbers are unreadable, because a serialised feeder
    and a slow client look identical from the client's side.
    """
    body = ENCODER.encode(case.params) if case.params is not None else b"{}"
    prefix = b'{"jsonrpc":"2.0","method":"bench","params":' + body + b',"id":'

    async with connect(f"ws://127.0.0.1:{port}", max_size=16 * 1024 * 1024) as ws:
        n = 0

        async def batch(count_: int) -> None:
            nonlocal n
            for _ in range(0, count_, concurrency):
                for _ in range(concurrency):
                    n += 1
                    await ws.send(prefix + str(n).encode() + b"}")
                for _ in range(concurrency):
                    await ws.recv(decode=False)

        await batch(warmup)
        t0 = time.perf_counter()
        await batch(count)
        elapsed = time.perf_counter() - t0

    return Burst(
        messages=count,
        bytes_total=count * case.request_size,
        elapsed_s=elapsed,
        peak_rss_kib=_peak_rss_kib(),
    )


# -- process orchestration -------------------------------------------------


def _with_feeder(payload: bytes, count: int, warmup: int, mode: str, run):
    ctx = mp.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe()
    proc = ctx.Process(target=feeder_main, args=(child_conn, payload, count, warmup, mode), daemon=True)
    proc.start()
    try:
        if not parent_conn.poll(30):
            raise RuntimeError("feeder process did not report a port")
        return asyncio.run(run(parent_conn.recv()))
    finally:
        proc.terminate()
        proc.join(timeout=5)


def _result(name: str, bursts: list[Burst], bytes_per_op: int, meta: dict) -> Result:
    per_msg = sorted(b.ns_per_message for b in bursts)
    quantiles = statistics.quantiles(per_msg, n=4) if len(per_msg) >= 4 else [per_msg[0], per_msg[0], per_msg[-1]]
    return Result(
        name=name,
        median_ns=statistics.median(per_msg),
        q1_ns=quantiles[0],
        q3_ns=quantiles[2],
        min_ns=per_msg[0],
        samples=len(bursts),
        iters_per_sample=bursts[0].messages,
        bytes_per_op=bytes_per_op,
        git=_git_rev(),
        meta={**meta, "peak_rss_mib": round(max(b.peak_rss_kib for b in bursts) / 1024, 1)},
    )


def run_notifications(
    channel: Channel,
    *,
    messages: int = 20_000,
    warmup: int = 2_000,
    repeats: int = 5,
    mode: str = "async",
) -> Result:
    """``mode`` is ``async``, ``sync`` or ``control``."""

    def run(port):
        if mode == "control":
            return _control_burst(port, channel, messages, warmup)
        return _client_burst(port, channel, messages, warmup, mode == "async")

    bursts = [_with_feeder(channel.raw, messages, warmup, "notify", run) for _ in range(repeats)]
    return _result(
        f"ws/notify/{channel.name}/{mode}",
        bursts,
        channel.size,
        {"channel": channel.wire, "frame_bytes": channel.size, "elements": channel.elements, "handler": mode},
    )


def run_rpc(
    case: RPCCase,
    *,
    requests: int = 2_000,
    warmup: int = 200,
    repeats: int = 5,
    concurrency: int = 1,
    control: bool = False,
) -> Result:
    """Round trips per second. ``control`` measures the feeder's ceiling."""

    def run(port):
        if control:
            return _rpc_control_burst(port, case, requests, warmup, concurrency)
        return _rpc_burst(port, case, requests, warmup, concurrency)

    bursts = [_with_feeder(case.result, requests, warmup, "rpc", run) for _ in range(repeats)]
    suffix = f"control_c{concurrency}" if control else f"c{concurrency}"
    return _result(
        f"ws/rpc/{case.name}/{suffix}",
        bursts,
        case.request_size if case.params is not None else 0,
        {"request_bytes": case.request_size, "concurrency": concurrency},
    )


def channels(seed: int = 0) -> dict[str, Channel]:
    return build_channels(seed=seed)


def rpc_cases(seed: int = 0) -> dict[str, RPCCase]:
    return build_rpc_cases(seed=seed)
