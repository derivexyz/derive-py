"""
05 - Order lifecycle: place, inspect, cancel.

Places a limit BUY on ETH-PERP well below the mark so it rests on the book,
lists the open orders, then cancels it. Nothing fills.

    Orders are EIP-712 signed actions. create() encodes the trade, signs it
    locally with your key and sends the params plus the signature. The
    exchange can settle only what you signed and never holds your key.
    amount and limit_price are quantized to the instrument's amount_step and
    tick_size inside create(), so an approximate Decimal is fine here.
    max_fee is the fee cap signed into the action: the exchange charges its
    normal maker or taker fee but can never take more than this. It defaults
    to 1000, which is generous, so set it deliberately.

Uses WebSocketClient because order flow is a request and a response over a
persistent connection, with no per-request handshake. 06 and 07 do the same.

The cancel runs in a finally block: an order that rests on the book outlives
this process, so leaving one behind on an error would be a real position.

Prerequisites: a funded subaccount. See 01-deposit.py.

Run:
    python examples/05-place-order.py
"""

import asyncio
from decimal import Decimal

from derive_py import WebSocketClient
from derive_py.data_types.generated_models import Direction, OrderType, TimeInForce

INSTRUMENT = "ETH-PERP"
MARK_DISCOUNT = Decimal("0.8")  # bid 20% under the mark, so the order rests
MAX_FEE = Decimal("10")


async def main() -> None:
    client = WebSocketClient.from_env()
    log = client.logger
    await client.connect()

    subaccount = client.active_subaccount
    if not subaccount.state.collaterals:
        raise SystemExit(f"Subaccount {subaccount.id} holds no collateral. Run 01-deposit.py first.")

    order = None
    try:
        instrument = await client.markets.get_instrument(instrument_name=INSTRUMENT)
        ticker = await client.markets.get_ticker(instrument_name=INSTRUMENT)

        mark = Decimal(ticker.mark_price)
        limit_price = mark * MARK_DISCOUNT
        amount = Decimal(instrument.minimum_amount)  # smallest size the instrument allows
        log.info(f"mark ${mark}, bidding around ${limit_price} for {amount} {INSTRUMENT}")

        # post_only rejects rather than fills if the price would cross, so
        # this either rests on the book or fails outright.
        response = await subaccount.orders.create(
            amount=amount,
            direction=Direction.buy,
            instrument_name=INSTRUMENT,
            limit_price=limit_price,
            max_fee=MAX_FEE,
            order_type=OrderType.limit,
            time_in_force=TimeInForce.post_only,
        )
        order = response.order
        log.info(f"placed {order.order_id}: {order.order_status}, {order.amount} @ {order.limit_price}")

        # Every open order on the subaccount, not just the one placed above.
        open_orders = await subaccount.orders.list_open()
        listed = "\n".join(
            f"  {o.order_id} {o.direction} {o.amount} {o.instrument_name} @ {o.limit_price}" for o in open_orders
        )
        log.info(f"{len(open_orders)} open order(s):\n{listed}")
    finally:
        if order is not None:
            cancelled = await subaccount.orders.cancel(instrument_name=INSTRUMENT, order_id=order.order_id)
            log.info(f"cancelled {cancelled.order_id}: {cancelled.order_status}")
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
