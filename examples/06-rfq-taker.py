"""
RFQ taker: request quotes for a package, execute the best one.

Uses WebSocketClient, same reasoning as 05-place-order.py: RFQ is another
signed-action-plus-wait-for-a-response flow (poll for maker quotes over
several seconds here, instead of waiting for a fill), so the same
persistent-connection benefit applies.

The RFQ mental model:
  1. The taker sends an UNPRICED RFQ -- legs with instrument/amount/direction
     stated from the taker's own point of view. Nothing is signed yet.
  2. Makers respond with signed quotes. A quote with direction=sell offers
     to sell the package exactly as the taker stated it (i.e. lets a
     buying taker buy); direction=buy offers the reverse.
  3. The taker executes ONE quote -- this is the taker's only signature:
     an EIP-712 commitment to the maker's exact legs and prices, in the
     OPPOSITE direction of the quote.

Prerequisites: a funded subaccount, and active makers quoting RFQs on
testnet -- quotes may take a few seconds, or never arrive (handled below
by cancelling the RFQ).

Run:
    python examples/06-rfq-taker.py
"""

import asyncio
from decimal import Decimal
from pathlib import Path

from derive_client import WebSocketClient
from derive_client.data_types.generated_models import Direction, LegUnpricedParams

INSTRUMENT = "ETH-PERP"
SIZE = Decimal("0.1")
MAX_POLL_ATTEMPTS = 10
POLL_INTERVAL_SEC = 2


async def main():
    env_file = Path(__file__).parent.parent / ".env.template"
    client = WebSocketClient.from_env(env_file=env_file)
    await client.connect()

    try:
        subaccount = client.active_subaccount

        # Mark price gives us a reference to judge quotes against.
        ticker = await client.markets.get_ticker(instrument_name=INSTRUMENT)
        mark = Decimal(ticker.mark_price)
        print(f"{INSTRUMENT} mark price: ${mark}")

        # 1. Request quotes: one leg, buying SIZE contracts. Amounts are
        # always positive -- direction carries the sign.
        rfq = await subaccount.rfq.send_rfq(
            legs=[LegUnpricedParams(instrument_name=INSTRUMENT, amount=SIZE, direction=Direction.buy)],
            max_total_cost=mark * SIZE * Decimal("1.05"),
        )
        print(f"RFQ {rfq.rfq_id} open until {rfq.valid_until}")

        # 2. Poll for maker quotes. get_best_quote() is a one-shot
        # alternative where the exchange picks the best open quote for you.
        quotes = []
        for attempt in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL_SEC)
            poll = await subaccount.rfq.poll_quotes(rfq_id=rfq.rfq_id, status="open")
            # We are buying, so only maker sell quotes are executable by us.
            quotes = [q for q in poll.quotes if q.direction == Direction.sell]
            print(f"poll {attempt + 1}: {len(quotes)} executable quote(s)")
            if quotes:
                break

        if not quotes:
            # No makers answered -- release the RFQ so it doesn't linger in their books.
            await subaccount.rfq.cancel_rfq(rfq_id=rfq.rfq_id)
            print("No quotes arrived; RFQ cancelled. Try again when makers are active.")
            return

        # 3. Pick the best quote. Single leg + buying, so best = lowest price.
        best = min(quotes, key=lambda q: q.legs[0].price)
        print(f"Best quote {best.quote_id}: {best.legs[0].price} from {best.wallet}")

        # 4. Execute it.
        fill = await subaccount.rfq.accept_quote(
            quote=best,
            max_fee=Decimal("10"),
            enable_taker_protection=True,
        )
        print(f"Executed: status={fill.status} fee=${fill.fee} filled={fill.fill_pct}")
        for leg in fill.legs:
            print(f"  {leg.direction} {leg.amount} {leg.instrument_name} @ {leg.price}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
