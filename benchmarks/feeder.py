"""A deliberately dumb WebSocket feeder.

A ``websockets`` server cannot saturate a ``websockets`` client: per-message
send overhead on the server side lands in the same order of magnitude as the
client's whole decode path, so both ends measure the server. Measured on the
first cut of this harness, a server-side ``await ws.send(frame)`` loop topped
out around 9k messages/second while the client's own decode benchmarks said it
could handle ten times that.

So the feeder does not speak WebSocket properly. It performs the opening
handshake, reads exactly one client frame (the subscribe RPC, so it can echo
the id back), and from then on writes a pre-computed frame header plus payload
straight to the socket, batched. Server to client frames are unmasked and the
payload never changes, so the bytes for message N are byte-identical to message
1 and can be built once.

Consequence to keep in mind when reading results: this measures the client
against a feeder that is faster than any real exchange. That is the point. It
is a ceiling on the client, not a simulation of Derive.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import struct

GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OP_TEXT = 0x1
OP_BINARY = 0x2
OP_CLOSE = 0x8

#: Frames written per drain. Large enough that the write syscall dominates,
#: small enough that a slow client cannot make the feeder buffer without bound.
BATCH = 64


def _frame(payload: bytes, opcode: int = 0x1) -> bytes:
    """Build one unmasked server frame. FIN set, no extensions."""
    n = len(payload)
    if n <= 125:
        header = struct.pack("!BB", 0x80 | opcode, n)
    elif n <= 0xFFFF:
        header = struct.pack("!BBH", 0x80 | opcode, 126, n)
    else:
        header = struct.pack("!BBQ", 0x80 | opcode, 127, n)
    return header + payload


async def _read_exactly(reader: asyncio.StreamReader, n: int) -> bytes:
    return await reader.readexactly(n)


def _unmask(payload: bytes, mask: bytes) -> bytes:
    """XOR a client payload with its 4-byte mask.

    Done as one big-integer XOR rather than a per-byte loop: the RPC mode reads
    a frame per request, and a Python-level loop over a kilobyte of request
    body would make the feeder the bottleneck in the thing it exists to
    saturate.
    """
    n = len(payload)
    if not n:
        return payload
    padded = mask * (n // 4 + 1)
    key = int.from_bytes(padded, "big") >> (8 * (len(padded) - n))
    return (int.from_bytes(payload, "big") ^ key).to_bytes(n, "big")


async def _read_client_frame(reader: asyncio.StreamReader) -> tuple[int, bytes]:
    """Read one masked client frame, returning its opcode and payload."""
    b0, b1 = await _read_exactly(reader, 2)
    masked = bool(b1 & 0x80)
    length = b1 & 0x7F
    if length == 126:
        (length,) = struct.unpack("!H", await _read_exactly(reader, 2))
    elif length == 127:
        (length,) = struct.unpack("!Q", await _read_exactly(reader, 8))
    mask = await _read_exactly(reader, 4) if masked else b""
    payload = await _read_exactly(reader, length)
    return b0 & 0x0F, (_unmask(payload, mask) if masked else payload)


async def _read_data_frame(reader: asyncio.StreamReader) -> bytes | None:
    """Next text or binary frame, or None once the client closes.

    Control frames are not answered. A ping goes unanswered and a close is not
    echoed, because the parent terminates this process the moment the burst is
    over and a correct closing handshake would only add latency to the thing
    being measured.
    """
    while True:
        opcode, payload = await _read_client_frame(reader)
        if opcode == OP_CLOSE:
            return None
        if opcode in (OP_TEXT, OP_BINARY):
            return payload


async def _handshake(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    key = None
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
        name, _, value = line.decode("latin-1").partition(":")
        if name.strip().lower() == "sec-websocket-key":
            key = value.strip().encode()
    if key is None:
        raise RuntimeError("client sent no Sec-WebSocket-Key")
    accept = base64.b64encode(hashlib.sha1(key + GUID).digest()).decode()
    writer.write(
        b"HTTP/1.1 101 Switching Protocols\r\n"
        b"Upgrade: websocket\r\n"
        b"Connection: Upgrade\r\n"
        b"Sec-WebSocket-Accept: " + accept.encode() + b"\r\n\r\n"
    )
    await writer.drain()


def subscribe_reply(request: dict) -> bytes:
    """A JSON-RPC result the session's ``subscribe`` will accept."""
    channel = "bench"
    params = request.get("params") or {}
    channels = params.get("channels") or []
    if channels:
        channel = channels[0]
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {"status": {channel: "ok"}, "current_subscriptions": [channel]},
        }
    ).encode()


def rpc_reply(request_id, result: bytes) -> bytes:
    """Echo a canned result back under the client's request id."""
    return b'{"jsonrpc":"2.0","id":' + json.dumps(request_id).encode() + b',"result":' + result + b"}"


async def _serve_rpc(reader, writer, result: bytes, ready: asyncio.Event) -> None:
    """Answer every request with the same canned result until the client goes.

    Only the id is parsed. The request body is read and discarded: the point is
    to measure the client encoding and sending it, not a server understanding
    it.
    """
    await _handshake(reader, writer)
    while not ready.is_set():
        body = await _read_data_frame(reader)
        if body is None:
            return
        writer.write(_frame(rpc_reply(json.loads(body).get("id"), result)))
        await writer.drain()


async def _serve_one(reader, writer, payload: bytes, count: int, warmup: int, ready: asyncio.Event) -> None:
    await _handshake(reader, writer)

    body = await _read_data_frame(reader)
    if body is None:
        return
    writer.write(_frame(subscribe_reply(json.loads(body))))
    await writer.drain()

    frame = _frame(payload)
    batch = frame * BATCH

    async def blast(n: int) -> None:
        full, rest = divmod(n, BATCH)
        for _ in range(full):
            writer.write(batch)
            await writer.drain()
        if rest:
            writer.write(frame * rest)
            await writer.drain()

    await blast(warmup)
    # Let the client finish the warmup before the measured burst begins, so the
    # first measured frame is not queued behind warmup backlog.
    await asyncio.sleep(0.25)
    await blast(count)

    # Hold the connection open; the parent terminates this process.
    await ready.wait()


def feeder_main(conn, payload: bytes, count: int, warmup: int, mode: str = "notify") -> None:
    """Process entry point. Sends the bound port back over ``conn``.

    In ``notify`` mode ``payload`` is the notification frame to blast. In
    ``rpc`` mode it is the canned result body echoed under each request id.
    """

    async def main() -> None:
        forever = asyncio.Event()

        async def on_client(reader, writer):
            try:
                if mode == "rpc":
                    await _serve_rpc(reader, writer, payload, forever)
                else:
                    await _serve_one(reader, writer, payload, count, warmup, forever)
            except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError):
                pass
            finally:
                writer.close()

        server = await asyncio.start_server(on_client, "127.0.0.1", 0)
        conn.send(server.sockets[0].getsockname()[1])
        async with server:
            await forever.wait()

    asyncio.run(main())
