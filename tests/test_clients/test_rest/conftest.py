from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import cast

import pytest


@dataclass
class Route:
    statuses: list[int] = field(default_factory=lambda: [200])
    delay: float = 0.0
    body: bytes = b"{}"
    headers: dict[str, str] = field(default_factory=dict)


class ServerState:
    def __init__(self, port: int):
        self.port = port
        self.routes: dict[str, Route] = {}
        self.hits: dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def route(self, path: str, **kwargs) -> None:
        self.routes[path] = Route(**kwargs)

    def next_status(self, path: str) -> int:
        with self._lock:
            self.hits[path] += 1
            n = self.hits[path]
        route = self.routes.get(path, Route())
        return route.statuses[min(n - 1, len(route.statuses) - 1)]


class _Server(ThreadingHTTPServer):
    state: ServerState


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        state = cast(_Server, self.server).state
        # Drain the body first, or the next keep-alive request on this
        # connection desynchronises and surfaces as a spurious retry failure.
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        route = state.routes.get(self.path, Route())
        status = state.next_status(self.path)
        if route.delay:
            time.sleep(route.delay)
        self.send_response(status)
        for name, value in route.headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(route.body)))
        self.end_headers()
        self.wfile.write(route.body)

    def log_message(self, *args):
        pass


@pytest.fixture
def http_server():
    server = _Server(("127.0.0.1", 0), _Handler)
    server.state = ServerState(server.server_address[1])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield server.state
    finally:
        server.shutdown()
        server.server_close()
