from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import TypeVar

from derive_py._web3.deposits import DepositStep

T = TypeVar("T")


class _Stop:
    """Dedicated sentinel class, not object() -- isinstance narrows T | _Stop
    down to T correctly after the check below; identity-checking a bare
    object() instance doesn't narrow the same way, which is what pyright was
    actually flagging (the yield type inferred as T | object, not T)."""

    __slots__ = ()


_STOP = _Stop()


async def iterate_sync_generator_in_thread(sync_iterator: Iterator[T]) -> AsyncIterator[T]:
    # StopIteration is caught inside the threaded call itself,
    # never allowed to cross the thread boundary as a raised exception
    # letting it surface directly inside a coroutine hits PEP 479,
    # so it's translated to a sentinel and checked here instead.

    def _next() -> T | _Stop:
        try:
            return next(sync_iterator)
        except StopIteration:
            return _STOP

    while True:
        item = await asyncio.to_thread(_next)
        if isinstance(item, _Stop):
            return
        yield item


@dataclass
class AsyncDepositStep:
    _step: DepositStep

    @property
    def kind(self) -> str:
        return self._step.kind

    @property
    def description(self) -> str:
        return self._step.description

    @property
    def tx_params(self):
        return self._step.tx_params

    @property
    def tx_hash(self):
        return self._step.tx_hash

    @property
    def receipt(self):
        return self._step.receipt

    async def submit(self, private_key: str | None = None):
        return await asyncio.to_thread(self._step.submit, private_key)

    async def wait_for_finality(self, **kwargs):
        return await asyncio.to_thread(self._step.wait_for_finality, **kwargs)


async def iterate_deposit_steps_in_thread(sync_iterator: Iterator[DepositStep]) -> AsyncIterator[AsyncDepositStep]:
    async for step in iterate_sync_generator_in_thread(sync_iterator):
        yield AsyncDepositStep(_step=step)
