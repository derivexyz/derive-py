from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

import pytest
from web3.types import RPCEndpoint, RPCResponse

from derive_py.config import SEPOLIA_CHAIN_ID


@dataclass
class Call:
    method: str
    params: Any


@dataclass
class FakeProvider:
    """Structurally an RPCProvider. No socket, no session, no web3 internals."""

    uri: str
    handler: Callable[[str, Any], Any]
    calls: list[Call] = field(default_factory=list)

    @property
    def endpoint_uri(self) -> str:
        return self.uri

    def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        self.calls.append(Call(str(method), params))
        outcome = self.handler(str(method), params)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def method_calls(self, method: str) -> list[Call]:
        return [c for c in self.calls if c.method == method]


def ok(result: Any) -> RPCResponse:
    return RPCResponse({"jsonrpc": "2.0", "id": 1, "result": result})


def rpc_error(code: int, message: str) -> RPCResponse:
    return RPCResponse({"jsonrpc": "2.0", "id": 1, "error": {"code": code, "message": message}})


def static_handler(chain_id: int = SEPOLIA_CHAIN_ID, **responses: Any) -> Callable[[str, Any], Any]:
    """chain_id is answered by default so _ensure_verified passes."""

    table: dict[str, Any] = {"eth_chainId": ok(hex(chain_id))}
    table.update(responses)

    def handler(method: str, params: Any) -> Any:
        value = table.get(method)
        if value is None:
            return rpc_error(-32601, f"the method {method} does not exist")
        return value(method, params) if callable(value) else value

    return handler


@pytest.fixture
def logger() -> logging.Logger:
    return logging.getLogger("test")
