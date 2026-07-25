"""
Order lifecycle: place, inspect, cancel.

Places a limit BUY on ETH-PERP priced well below the mark so it rests on
the book (nothing fills), lists it, then cancels it.

The mental model to take away:
  - Orders are EIP-712 signed actions: create() encodes the trade, signs it
    locally with your key, and sends params + signature. The exchange can
    only settle exactly what you signed, it never holds your key.
  - amount/limit_price are auto-quantized to the instrument's amount_step/
    tick_size inside create()/replace(); you can pass an approximate
    Decimal price here; the client snaps it, not you.
  - max_fee is the fee cap baked into the signature -- the exchange still
    charges its normal maker/taker fee, but can never take more than you
    signed for.

Prerequisites: a wallet with a funded subaccount -- see 01-deposit.py.

Run:
    python examples/05-place-order.py
"""

import asyncio
from decimal import Decimal
from pathlib import Path

from derive_client import WebSocketClient
from derive_client.data_types.generated_models import Direction, OrderType, TimeInForce

INSTRUMENT = "ETH-PERP"


async def main():
    env_file = Path(__file__).parent.parent / ".env.template"
    client = WebSocketClient.from_env(env_file=env_file)
    await client.connect()

    try:
        instrument = await client.markets.get_instrument(instrument_name=INSTRUMENT)
        ticker = await client.markets.get_ticker(instrument_name=INSTRUMENT)

        # Bid 20% under the mark so the order rests instead of filling.
        # No manual tick-snapping needed; create() quantizes for us.
        mark = Decimal(ticker.mark_price)
        limit_price = mark * Decimal("0.8")
        amount = Decimal(instrument.minimum_amount)  # smallest size the instrument allows

        print(f"mark ${mark} -> bidding ~${limit_price} for {amount} {INSTRUMENT}")

        response = await client.active_subaccount.orders.create(
            amount=amount,
            direction=Direction.buy,
            instrument_name=INSTRUMENT,
            limit_price=limit_price,
            order_type=OrderType.limit,
            time_in_force=TimeInForce.post_only,
        )
        order = response.order
        print(f"placed {order.order_id}: {order.order_status}, {order.amount} @ {order.limit_price}")
        if response.trades:
            print(f"  filled: {len(response.trades)} trade(s) -- shouldn't happen with post_only, worth investigating")
        else:
            print("  resting on the book, guaranteed by post_only (would reject, not fill, if crossed)")

        open_orders = await client.active_subaccount.orders.list_open()
        for o in open_orders:
            print(f"open: {o.order_id} {o.direction} {o.amount} {o.instrument_name} @ {o.limit_price}")

        # Cancelling the order
        cancelled = await client.active_subaccount.orders.cancel(
            instrument_name=INSTRUMENT,
            order_id=order.order_id,
        )
        print(f"cancelled {cancelled.order_id}: {cancelled.order_status}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
