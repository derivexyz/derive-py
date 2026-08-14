"""
Public market data.

Everything here hits a public/* endpoint -- no session key, no signed
action, no client.connect(). MarketOperations never touches subaccount
state, so skipping connect() is correct, same as derive-ts never calling
it in this example.

One real gap versus derive-ts worth knowing about: their DeriveClient
supports genuinely keyless construction (`new DeriveClient({ network })`,
no wallet at all) for exactly this public-data-only case. HTTPClient
doesn't have that path yet -- wallet/session_key/subaccount_id are all
required by __init__ today, even though nothing below actually needs
them. Worth a follow-up if a pure market-data client (no wallet
configured anywhere) is something you want to support; this example
still goes through from_env() only because that's what currently works.

Shown here:
  get_all_currencies  -- every listed currency, spot price, and 24h move
  get_all_instruments -- paginated, filtered instrument listings
  get_ticker           -- index vs mark price, top of book, 24h stats

Run:
    python examples/03-market-data.py
"""

from datetime import datetime, timezone
from pathlib import Path

import msgspec

from derive_py import HTTPClient
from derive_py.data_types.generated_models import AssetType

env_file = Path(__file__).parent.parent / ".env.template"
client = HTTPClient.from_env(env_file=env_file)
# No client.connect() -- nothing below needs a session; see module docstring.

# -- Currencies ------------------------------------------------------------
currencies = client.markets.get_all_currencies()
print(f"{len(currencies)} currencies listed. First five by spot price:")
for c in currencies[:5]:
    spot = float(c.spot_price)
    change = ""
    if c.spot_price_24h is not msgspec.UNSET and c.spot_price_24h is not None:
        pct = (spot - float(c.spot_price_24h)) / float(c.spot_price_24h) * 100
        change = f" ({pct:+.2f}% 24h)"
    print(f"  {c.currency:<8} spot=${spot}{change}")

# -- Instruments ---------------------------------------------------------
eth_options = client.markets.get_all_instruments(
    expired=False,
    instrument_type=AssetType.option,
    currency="ETH",
    page_size=3,
)
print(f"\n{eth_options.pagination.count} live ETH options. A sample:")
for inst in eth_options.instruments:
    status = "active" if inst.is_active else "not yet active"
    print(f"  {inst.instrument_name} [{status}]")
    print(f"    tick={inst.tick_size} step={inst.amount_step} size=[{inst.minimum_amount}, {inst.maximum_amount}]")
    print(f"    fees: maker={inst.maker_fee_rate} taker={inst.taker_fee_rate} base={inst.base_fee}")

eth_perps = client.markets.get_all_instruments(expired=False, instrument_type=AssetType.perp, currency="ETH")
# One perp per currency; on every Derive network it's ETH-PERP.
perp_name = eth_perps.instruments[0].instrument_name if eth_perps.instruments else "ETH-PERP"

# -- Ticker --------------------------------------------------------------
ticker = client.markets.get_ticker(instrument_name=perp_name)
ts = datetime.fromtimestamp(ticker.timestamp / 1000, tz=timezone.utc)
print(f"\n{perp_name} @ {ts.isoformat()}")
print(f"  index price: ${ticker.index_price}")
print(f"  mark price:  ${ticker.mark_price}")
print(
    f"  book: {ticker.best_bid_amount} @ ${ticker.best_bid_price} | {ticker.best_ask_amount} @ ${ticker.best_ask_price}"
)
print(f"  spread: ${float(ticker.best_ask_price) - float(ticker.best_bid_price):.2f}")
print(
    f"  24h change: {ticker.stats.percent_change_24h}%  (high ${ticker.stats.high_24h} / low ${ticker.stats.low_24h})"
)
print(f"  24h volume: {ticker.stats.notional_volume_24h} notional, {ticker.stats.trade_count_24h} trades")
print(f"  open interest: {ticker.stats.open_interest}")
if ticker.funding_rate:
    print(f"  funding rate: {ticker.funding_rate}")
