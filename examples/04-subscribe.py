"""
04 - Websocket subscriptions: two public channels over one socket.

Subscriptions are callback-based. You hand each channel a handler, and the
client decodes every message into a typed payload before calling it.

    ticker_slim  the same TickerSlimSnapshot 03-market-data.py fetched once
                 over REST, pushed at a fixed interval instead
    orderbook    aggregated bids and asks, each level a (price, amount) pair
                 of decimal strings, with group and depth controlling price
                 aggregation and how many levels come back

Both run over one connection: the client multiplexes them and routes each
message to its own handler. If the socket drops, the client reconnects and
resubscribes every channel, so a handler keeps receiving without help.

Two things about handlers that the code cannot show you:

    They run on the receive loop, in arrival order per channel. A slow
    handler applies backpressure to the socket instead of racing the next
    message, so blocking work in one callback stalls every channel. Hand
    anything slow to a queue or a task.
    Exceptions raised inside a handler are caught and logged, never
    propagated. A bug in your callback fails quietly rather than stopping
    the process.

There is no per-channel unsubscribe() on the public API yet. disconnect()
ends every subscription on the socket, which is all this needs.

Prerequisites: none beyond network access. Copy .env.template to .env first.

Run:
    python examples/04-subscribe.py
"""

import asyncio

from derive_py import WebSocketClient
from derive_py.data_types.channel_models import OrderbookSnapshot, TickerSlimPayload

INSTRUMENT = "ETH-PERP"
UPDATES_TO_SHOW = 5
TIMEOUT_SEC = 30


async def main() -> None:
    client = WebSocketClient.from_env()
    log = client.logger
    await client.connect()

    updates = 0
    done = asyncio.Event()

    def on_ticker(payload: TickerSlimPayload) -> None:
        nonlocal updates
        ticker = payload.instrument_ticker
        log.info(f"ticker index=${ticker.index_price} mark=${ticker.mark_price} t={payload.timestamp}")
        updates += 1
        if updates >= UPDATES_TO_SHOW:
            done.set()

    def on_book(book: OrderbookSnapshot) -> None:
        bid_price, bid_amount = book.bids[0] if book.bids else ("-", "-")
        ask_price, ask_amount = book.asks[0] if book.asks else ("-", "-")
        log.info(
            f"book   {bid_amount} @ ${bid_price} | {ask_amount} @ ${ask_price}"
            f" ({len(book.bids)} bid / {len(book.asks)} ask levels)"
        )

    try:
        ticker_subscription = await client.public_channels.ticker_slim_interval_by_instrument_name(
            instrument_name=INSTRUMENT,
            interval=1000,
            callback=on_ticker,
        )
        book_subscription = await client.public_channels.orderbook_group_depth_by_instrument_name(
            instrument_name=INSTRUMENT,
            group=1,
            depth=10,
            callback=on_book,
        )
        log.info(f"subscribed: {ticker_subscription.status | book_subscription.status}")

        try:
            await asyncio.wait_for(done.wait(), timeout=TIMEOUT_SEC)
        except asyncio.TimeoutError:
            log.warning(f"Only {updates} ticker updates in {TIMEOUT_SEC}s. Quiet market, moving on.")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
