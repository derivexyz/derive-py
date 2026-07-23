from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import TypeVar

from derive_client._web3.deposits import DepositStep

T = TypeVar("T")

_STOP = object()


async def iterate_sync_generator_in_thread(sync_iterator: Iterator[T]) -> AsyncIterator[T]:
    # StopIteration is caught inside the threaded call itself,
    # never allowed to cross the thread boundary as a raised exception
    # letting it surface directly inside a coroutine hits PEP 479,
    # so it's translated to a sentinel and checked here instead.

    def _next():
        try:
            return next(sync_iterator)
        except StopIteration:
            return _STOP

    while True:
        item = await asyncio.to_thread(_next)
        if item is _STOP:
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
