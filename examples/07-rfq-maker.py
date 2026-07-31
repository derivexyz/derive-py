"""
RFQ maker: a minimal bounded quoting loop.

RFQ trading has two sides: a taker sends an RFQ (a package of unpriced
legs), makers answer with signed quotes, and the taker executes the one it
likes. This plays the MAKER -- polls for open RFQs and answers each with a
naive two-sided quote priced off the live mark. It's the skeleton of a
market-making loop, deliberately bounded (5 rounds) so it terminates
instead of running forever.

Uses WebSocketClient, same reasoning as 05-place-order.py/06-rfq-taker.py:
quoting is a signed-action-plus-repeated-polling flow, same category as
order placement and RFQ taking.

poll_rfqs() needs maker authorization on the subaccount -- per its own
docstring in rfq.py, "Unauthorized as RFQ maker" is a real error it can
return. A plain funded subaccount isn't necessarily enough on its own,
unlike every other example so far -- confirm that authorization before
running this.

poll_rfqs() returns PublicRfq, not Rfq -- confirmed against the OpenAPI
spec, same pattern as poll_quotes()/PublicQuote in 06-rfq-taker.py. .legs
is LegUnpricedParams (.instrument_name/.amount/.direction) on both Rfq and
PublicRfq though, identical either way, which is all this needs.

Prerequisites: a funded subaccount with RFQ-maker authorization, and
someone sending RFQs -- pair this with 06-rfq-taker.py running against the
same network.

Run:
    python examples/07-rfq-maker.py
"""

import asyncio
from decimal import Decimal
from pathlib import Path

from derive_client import WebSocketClient
from derive_client.data_types.generated_models import Direction, PricedLegParamsAndResponse

ROUNDS = 5
POLL_INTERVAL_SEC = 3
SPREAD = Decimal("0.005")  # quote 0.5% spread around mark on every leg


def snap_to_tick(price: Decimal, tick_size: Decimal) -> Decimal:
    """Snap a raw price onto the instrument's tick grid -- the exchange
    rejects off-tick prices. Decimal.quantize does this exactly, unlike
    derive-ts's manual float round()/toFixed() dance."""

    return price.quantize(tick_size)


async def price_leg(client, leg):
    """Fetch mark price and tick size for one RFQ leg, concurrently with
    whatever else is being priced -- mirrors derive-ts's Promise.all."""

    ticker, instrument = await asyncio.gather(
        client.markets.get_ticker(instrument_name=leg.instrument_name),
        client.markets.get_instrument(instrument_name=leg.instrument_name),
    )
    return leg, Decimal(ticker.mark_price), Decimal(instrument.tick_size)


async def main():
    env_file = Path(__file__).parent.parent / ".env.template"
    client = WebSocketClient.from_env(env_file=env_file)
    await client.connect()

    subaccount = client.active_subaccount
    quoted_rfq_ids: set[str] = set()  # already answered, so later polls don't re-quote them

    try:
        for round_num in range(1, ROUNDS + 1):
            # 'open' = still inside its quoting window and unfilled. Only
            # RFQs that are public, or that name our wallet as a
            # counterparty, show up here.
            poll = await subaccount.rfq.poll_rfqs(status="open")
            fresh = [rfq for rfq in poll.rfqs if rfq.rfq_id not in quoted_rfq_ids]
            print(f"round {round_num}/{ROUNDS}: {len(poll.rfqs)} open RFQ(s), {len(fresh)} new")

            for rfq in fresh:
                # Leg directions are the TAKER's perspective and must be
                # echoed back unchanged -- a quote reprices the taker's
                # exact package, it never restructures it.
                priced = await asyncio.gather(*(price_leg(client, leg) for leg in rfq.legs))
                notional_usd = sum(Decimal(leg.amount) * mark for leg, mark, _ in priced)

                # Quote both sides: sell offers the package to a buying
                # taker, buy bids for it. The spread goes in our favor per
                # side -- selling means pricing OVER mark on legs the taker
                # buys and UNDER mark on legs the taker sells; bidding
                # flips both.
                for direction in (Direction.sell, Direction.buy):
                    legs = []
                    for leg, mark, tick_size in priced:
                        favor_high = (direction == Direction.sell) == (leg.direction == Direction.buy)
                        raw_price = mark * (1 + (SPREAD if favor_high else -SPREAD))
                        legs.append(
                            PricedLegParamsAndResponse(
                                instrument_name=leg.instrument_name,
                                amount=leg.amount,
                                direction=leg.direction,
                                price=snap_to_tick(raw_price, tick_size),
                            )
                        )

                    quote = await subaccount.rfq.send_quote(
                        direction=direction,
                        legs=legs,
                        rfq_id=rfq.rfq_id,
                        max_fee=max(Decimal("10"), notional_usd * Decimal("0.003")),
                        # Flip to True once your subaccount has an MMP config.
                        mmp=False,
                    )
                    summary = " + ".join(f"{leg.instrument_name}@{leg.price}" for leg in legs)
                    print(f"  quoted {direction} on rfq {rfq.rfq_id}: quote {quote.quote_id} ({summary})")

                quoted_rfq_ids.add(rfq.rfq_id)

            if round_num < ROUNDS:
                await asyncio.sleep(POLL_INTERVAL_SEC)
    finally:
        # Leave nothing resting: a signed quote stays executable until it
        # expires or is cancelled, even after this process exits.
        await subaccount.rfq.cancel_batch_quotes()
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
