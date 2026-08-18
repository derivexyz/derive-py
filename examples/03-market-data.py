"""
03 - Public market data: currencies, instruments, tickers.

Every call here is a public/* endpoint: no session key, no signed action,
no connect(). MarketOperations never touches subaccount state.

    get_all_currencies   every listed currency, spot price and 24h move
    get_all_instruments  paginated, filtered instrument listings
    get_ticker           index and mark price, top of book, 24h stats, and
                         greeks plus implied vols when the instrument is an option

get_ticker returns a TickerSlimSnapshot, which is the same type the
ticker_slim websocket channel pushes in 04-subscribe.py: one snapshot here,
a stream of them there.

TODO: from_env() still requires a wallet, a session key and a subaccount id,
none of which this file uses. A public-data client should be constructible
without them.

Prerequisites: none beyond network access. Copy .env.template to .env first.

Run:
    python examples/03-market-data.py
"""

from datetime import datetime, timezone
from decimal import Decimal

from msgspec import UNSET

from derive_py import HTTPClient
from derive_py.data_types.generated_models import AssetType

CURRENCY = "ETH"
CURRENCIES_TO_SHOW = 5
OPTIONS_TO_SHOW = 3

client = HTTPClient.from_env()
log = client.logger


# -- Currencies ------------------------------------------------------------

currencies = client.markets.get_all_currencies()

lines = [f"{len(currencies)} currencies listed, first {CURRENCIES_TO_SHOW} as returned:"]
for currency in currencies[:CURRENCIES_TO_SHOW]:
    spot = Decimal(currency.spot_price)
    move = ""
    # Unset, None or zero until the currency has a usable 24h reference.
    reference = currency.spot_price_24h
    if reference is not UNSET and reference is not None and (previous := Decimal(reference)):
        move = f" ({(spot - previous) / previous * 100:+.2f}% 24h)"
    lines.append(f"  {currency.currency:<8} spot=${spot}{move}")
log.info("\n".join(lines))


# -- Instruments -----------------------------------------------------------

options = client.markets.get_all_instruments(
    expired=False,
    instrument_type=AssetType.option,
    currency=CURRENCY,
    page_size=OPTIONS_TO_SHOW,
)

lines = [f"{options.pagination.count} live {CURRENCY} options, showing {len(options.instruments)}:"]
for instrument in options.instruments:
    lines.append(f"  {instrument.instrument_name} [{'active' if instrument.is_active else 'not yet active'}]")
    lines.append(
        f"    tick={instrument.tick_size} step={instrument.amount_step}"
        f" size=[{instrument.minimum_amount}, {instrument.maximum_amount}]"
    )
    lines.append(
        f"    fees: maker={instrument.maker_fee_rate} taker={instrument.taker_fee_rate} base={instrument.base_fee}"
    )
log.info("\n".join(lines))


# -- Ticker ----------------------------------------------------------------

# One perp per currency, so this filter returns exactly one instrument.
perps = client.markets.get_all_instruments(expired=False, instrument_type=AssetType.perp, currency=CURRENCY)
perp_name = perps.instruments[0].instrument_name

ticker = client.markets.get_ticker(instrument_name=perp_name)
spread = Decimal(ticker.best_ask_price) - Decimal(ticker.best_bid_price)
stats = ticker.stats

lines = [
    f"{perp_name} at {datetime.fromtimestamp(ticker.timestamp / 1000, tz=timezone.utc).isoformat()}:",
    f"  index price: ${ticker.index_price}",
    f"  mark price:  ${ticker.mark_price}",
    f"  book: {ticker.best_bid_amount} @ ${ticker.best_bid_price}"
    f" | {ticker.best_ask_amount} @ ${ticker.best_ask_price}",
    f"  spread: ${spread:.2f}",
    f"  24h change: {stats.percent_change_24h}% (high ${stats.high_24h} / low ${stats.low_24h})",
    f"  24h volume: {stats.notional_volume_24h} notional over {stats.trade_count_24h} trades",
    f"  open interest: {stats.open_interest}",
]
if ticker.funding_rate:
    lines.append(f"  funding rate: {ticker.funding_rate}")
log.info("\n".join(lines))


# -- Option pricing --------------------------------------------------------

# The same get_ticker call, but an option's ticker also carries greeks and
# implied vols. Only an ACTIVE instrument has a ticker at all, and the listing
# runs from the furthest expiry to the nearest, so the live ones are on the
# last page rather than in the sample above.
last_page = client.markets.get_all_instruments(
    expired=False,
    instrument_type=AssetType.option,
    currency=CURRENCY,
    page=options.pagination.num_pages,
    page_size=OPTIONS_TO_SHOW,
)
option = next((i for i in reversed(last_page.instruments) if i.is_active), None)

if option is None:
    log.warning("No active option on the last page, so no greeks to show.")
else:
    option_ticker = client.markets.get_ticker(instrument_name=option.instrument_name)
    pricing = option_ticker.option_pricing
    if pricing is UNSET or pricing is None:
        log.warning(f"{option.instrument_name} cannot be priced right now.")
    else:
        log.info(
            f"{option.instrument_name}:\n"
            f"  mark ${option_ticker.mark_price}, forward ${pricing.forward_price}\n"
            f"  iv {pricing.iv} (bid {pricing.bid_iv} / ask {pricing.ask_iv})\n"
            f"  delta={pricing.delta} gamma={pricing.gamma} vega={pricing.vega}"
            f" theta={pricing.theta} rho={pricing.rho}"
        )
