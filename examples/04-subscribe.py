"""
Websocket subscriptions: callback handler over one socket.

Callback-only, on purpose -- derive-ts's version also demonstrates an
async-iterator style (stream()) as a second consumption pattern. This
client doesn't have that, deliberately: it existed as an early pass, but
was dropped in favor of callback-only after feedback that request/callback
matches how traders actually think about subscriptions more than iterating
a stream does. It could be added later as a purely ADDITIVE method
alongside this one if there's real demand -- not urgent, and not something
that needs to ride this migration's breaking-changes window, since it
wouldn't be a breaking change either way.

Uses ticker_slim rather than derive-ts's orderbook channel -- the orderbook
one is marked skipped in this client's own tests right now
("v3 migration: OrderSnapshot bids and asks are array instead of object"),
so it's not something to build an example around yet. ticker_slim also
continues naturally from 03-market-data.py: there you fetched a ticker
snapshot once over REST, here the same data gets pushed to you over time.

No unsubscribe() call here -- not because the shape is unconfirmed, but
because it genuinely isn't user-facing yet. It exists on the internal
websocket session (derive_py/_clients/websockets/session.py), not on
client.public_channels/private_channels. disconnect() below tears down
the whole socket, which ends every subscription on it implicitly, so this
example doesn't need it regardless -- but a real per-channel unsubscribe()
on the public API is a gap worth closing in its own PR, alongside a
broader look at the channel-method naming (verbose, explicit names like
ticker_slim_interval_by_instrument_name work, but something like a
per-channel SubscriptionSpec might be worth considering instead of one
method per channel shape). Not attempting either here.

Run:
    python examples/04-subscribe.py
"""

import asyncio
from pathlib import Path

from derive_py import WebSocketClient

INSTRUMENT = "ETH-PERP"
UPDATES_TO_SHOW = 10
TIMEOUT_SEC = 30


async def main():
    env_file = Path(__file__).parent.parent / ".env.template"
    client = WebSocketClient.from_env(env_file=env_file)
    await client.connect()

    updates = 0
    done = asyncio.Event()

    def on_ticker(payload):
        nonlocal updates
        ticker = payload.instrument_ticker
        print(f"  index=${ticker.index_price} mark=${ticker.mark_price} t={payload.timestamp}")
        updates += 1
        if updates >= UPDATES_TO_SHOW:
            done.set()

    subscription_result = await client.public_channels.ticker_slim_interval_by_instrument_name(
        instrument_name=INSTRUMENT,
        interval=1000,
        callback=on_ticker,
    )
    print(f"Subscribed: {subscription_result.status}")

    try:
        await asyncio.wait_for(done.wait(), timeout=TIMEOUT_SEC)
    except asyncio.TimeoutError:
        print(f"No {UPDATES_TO_SHOW} updates within {TIMEOUT_SEC}s -- quiet market, moving on.")

    # No unsubscribe() yet.
    # disconnect() ends the subscription along with everything else on this socket.
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
