"""
06 - RFQ taker: request quotes for a package, execute the best one.

    1. The taker sends an UNPRICED RFQ: legs with instrument, amount and
       direction, stated from the taker's own point of view. Nothing is
       signed yet, and amounts are always positive, since direction carries
       the sign.
    2. Makers answer with signed quotes. A quote with direction=sell offers
       to sell the package exactly as the taker stated it, so a buying taker
       can execute it; direction=buy offers the reverse.
    3. The taker executes ONE quote. That is the taker's only signature: an
       EIP-712 commitment to the maker's exact legs and prices, in the
       opposite direction to the quote. accept_quote() flips the direction
       for you.

max_total_cost caps what the package may cost across all legs, and is set
here from the mark plus a slippage allowance. An RFQ left open sits in the
makers' books, so the finally block cancels it unless it was executed.

Uses WebSocketClient for the same reason as 05-place-order.py: signed
actions and repeated polling over one persistent connection.

Prerequisites: a funded subaccount, and makers actively quoting on the
network. Quotes may take seconds or never arrive. Pair it with
07-rfq-maker.py. Copy .env.template to .env first.

Run:
    python examples/06-rfq-taker.py
"""

import asyncio
from decimal import Decimal

from derive_py import WebSocketClient
from derive_py.data_types.generated_models import Direction, LegUnpricedParams

INSTRUMENT = "ETH-PERP"
SIZE = Decimal("0.1")
MAX_SLIPPAGE = Decimal("0.05")  # accept up to 5% over mark for the whole package
MAX_POLL_ATTEMPTS = 10
POLL_INTERVAL_SEC = 2
MAX_FEE_FLOOR = Decimal("10")
MAX_FEE_RATE = Decimal("0.003")  # cap scales with notional above the floor


async def main() -> None:
    client = WebSocketClient.from_env()
    log = client.logger
    await client.connect()

    subaccount = client.active_subaccount
    if not subaccount.state.collaterals:
        raise SystemExit(f"Subaccount {subaccount.id} holds no collateral. Run 01-deposit.py first.")

    rfq = None
    executed = False
    try:
        # The mark is the reference the quotes are judged against.
        ticker = await client.markets.get_ticker(instrument_name=INSTRUMENT)
        mark = Decimal(ticker.mark_price)
        notional = mark * SIZE
        log.info(f"{INSTRUMENT} mark ${mark}, requesting quotes for {SIZE} ({notional:.2f} notional)")

        rfq = await subaccount.rfq.send_rfq(
            legs=[LegUnpricedParams(instrument_name=INSTRUMENT, amount=SIZE, direction=Direction.buy)],
            max_total_cost=notional * (1 + MAX_SLIPPAGE),
        )
        log.info(f"rfq {rfq.rfq_id} open until {rfq.valid_until}")

        # get_best_quote() is the one-shot alternative, where the exchange
        # picks the best open quote instead of you polling and choosing.
        quotes = []
        for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
            await asyncio.sleep(POLL_INTERVAL_SEC)
            poll = await subaccount.rfq.poll_quotes(rfq_id=rfq.rfq_id, status="open")
            # Buying, so only maker sell quotes are executable here.
            quotes = [q for q in poll.quotes if q.direction == Direction.sell]
            log.info(f"poll {attempt}/{MAX_POLL_ATTEMPTS}: {len(quotes)} executable quote(s)")
            if quotes:
                break

        if not quotes:
            log.warning("No quotes arrived. Try again when makers are active.")
            return

        # One leg and buying, so the best quote is simply the cheapest.
        best = min(quotes, key=lambda q: q.legs[0].price)
        log.info(f"best quote {best.quote_id} at {best.legs[0].price} from {best.wallet}")

        fill = await subaccount.rfq.accept_quote(
            quote=best,
            max_fee=max(MAX_FEE_FLOOR, notional * MAX_FEE_RATE),
            enable_taker_protection=True,  # exchange-side execution guard, see the API docs
        )
        executed = True

        legs = "\n".join(f"  {leg.direction} {leg.amount} {leg.instrument_name} @ {leg.price}" for leg in fill.legs)
        log.info(f"executed {fill.status}, fee ${fill.fee}, filled {fill.fill_pct}:\n{legs}")
    finally:
        if rfq is not None and not executed:
            # An open RFQ lingers in the makers' books until it expires.
            await subaccount.rfq.cancel_rfq(rfq_id=rfq.rfq_id)
            log.info(f"cancelled rfq {rfq.rfq_id}")
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
