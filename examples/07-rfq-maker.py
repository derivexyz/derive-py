"""
07 - RFQ maker: a bounded quoting loop.

RFQ trading has two sides. A taker sends an RFQ, a package of unpriced legs;
makers answer with signed quotes; the taker executes the one it likes. This
plays the maker: poll for open RFQs and answer each with a naive two-sided
quote priced off the live mark. It is the skeleton of a market-making loop,
bounded to a few rounds so it terminates.

    Leg directions belong to the TAKER and are echoed back unchanged. A quote
    reprices the taker's exact package, it never restructures it.
    Both sides are quoted: sell offers the package as stated, buy bids for
    the reverse. The spread goes in our favour on each leg either way.
    Every quote is signed and stays executable until it expires or is
    cancelled, including after this process exits. Hence the label, and the
    cancel by that label in the finally block: it retires this example's own
    quotes without touching anything else the subaccount has resting.

Uses WebSocketClient for the same reason as 05-place-order.py: signed
actions and repeated polling over one persistent connection.

Prerequisites: a funded subaccount with RFQ-maker authorisation, which
poll_rfqs requires and no other example needs, plus someone sending RFQs.
Pair it with 06-rfq-taker.py against the same network.
Copy .env.template to .env first.

Run:
    python examples/07-rfq-maker.py
"""

import asyncio
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from derive_py import WebSocketClient
from derive_py.data_types.generated_models import Direction, LegUnpricedParams, PricedLegParamsAndResponse
from derive_py.exceptions import DeriveJSONRPCError

LABEL = "example-07"
ROUNDS = 5
POLL_INTERVAL_SEC = 3
SPREAD = Decimal("0.005")  # quote 0.5% either side of mark, on every leg
MAX_FEE_FLOOR = Decimal("10")
MAX_FEE_RATE = Decimal("0.003")  # cap scales with notional above the floor


def snap_to_tick(price: Decimal, tick_size: Decimal, *, favor_high: bool) -> Decimal:
    """Snap onto the instrument's tick grid; off-tick prices are rejected.

    Rounds away from mark, never through it: a price meant to sit above mark
    cannot be rounded below it by half a tick, and vice versa.
    """

    return price.quantize(tick_size, rounding=ROUND_CEILING if favor_high else ROUND_FLOOR)


async def price_leg(client, leg: LegUnpricedParams) -> tuple[LegUnpricedParams, Decimal, Decimal]:
    """Mark price and tick size for one leg, fetched concurrently."""

    ticker, instrument = await asyncio.gather(
        client.markets.get_ticker(instrument_name=leg.instrument_name),
        client.markets.get_instrument(instrument_name=leg.instrument_name),
    )
    return leg, Decimal(ticker.mark_price), Decimal(instrument.tick_size)


async def main() -> None:
    client = WebSocketClient.from_env()
    log = client.logger
    await client.connect()

    subaccount = client.active_subaccount
    quoted_rfq_ids: set[str] = set()  # answered already, so later polls skip them

    try:
        for round_num in range(1, ROUNDS + 1):
            # 'open' means still inside its quoting window and unfilled. Only
            # public RFQs, or ones naming this wallet, appear here.
            try:
                poll = await subaccount.rfq.poll_rfqs(status="open")
            except DeriveJSONRPCError as e:
                raise SystemExit(
                    f"poll_rfqs failed: {e}\nIt requires RFQ-maker authorisation on subaccount {subaccount.id}."
                ) from e

            fresh = [rfq for rfq in poll.rfqs if rfq.rfq_id not in quoted_rfq_ids]
            log.info(f"round {round_num}/{ROUNDS}: {len(poll.rfqs)} open RFQ(s), {len(fresh)} new")

            for rfq in fresh:
                priced = await asyncio.gather(*(price_leg(client, leg) for leg in rfq.legs))
                notional_usd = sum((leg.amount * mark for leg, mark, _ in priced), Decimal("0"))

                for direction in (Direction.sell, Direction.buy):
                    legs = []
                    for leg, mark, tick_size in priced:
                        # Selling the package means pricing over mark on legs
                        # the taker buys and under mark on legs it sells.
                        # Bidding for the package flips both.
                        favor_high = (direction == Direction.sell) == (leg.direction == Direction.buy)
                        raw_price = mark * (1 + (SPREAD if favor_high else -SPREAD))
                        legs.append(
                            PricedLegParamsAndResponse(
                                instrument_name=leg.instrument_name,
                                amount=leg.amount,
                                direction=leg.direction,
                                price=snap_to_tick(raw_price, tick_size, favor_high=favor_high),
                            )
                        )

                    quote = await subaccount.rfq.send_quote(
                        direction=direction,
                        legs=legs,
                        rfq_id=rfq.rfq_id,
                        max_fee=max(MAX_FEE_FLOOR, notional_usd * MAX_FEE_RATE),
                        label=LABEL,
                        mmp=False,  # set True once the subaccount has an MMP config
                    )
                    summary = " + ".join(f"{leg.instrument_name}@{leg.price}" for leg in legs)
                    log.info(f"  quoted {direction} on rfq {rfq.rfq_id}: quote {quote.quote_id} ({summary})")

                quoted_rfq_ids.add(rfq.rfq_id)

            if round_num < ROUNDS:
                await asyncio.sleep(POLL_INTERVAL_SEC)
    finally:
        # Filtered by label, so a real quoting process on the same subaccount
        # keeps its own quotes. Without the filter this cancels everything.
        cancelled = await subaccount.rfq.cancel_batch_quotes(label=LABEL)
        log.info(f"cancelled {len(cancelled.cancelled_ids)} quote(s) labelled '{LABEL}'")
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
