"""Column presets and ordering for CLI table display."""

CURRENCY_COLUMNS = [
    "currency",
    "instrument_types",
    "market_type",
    "spot_price",
    "spot_price_24h",
    "borrow_apy",
    "total_supply",
    "total_borrow",
    "srm_im_discount",
    "srm_mm_discount",
]

INSTRUMENT_COLUMNS = [
    "instrument_name",
    "base_currency",
    "instrument_type",
    "is_active",
    "taker_fee_rate",
    "maker_fee_rate",
    "tick_size",
    "amount_step",
    "minimum_amount",
    "maximum_amount",
]

ORDER_COLUMNS = [
    "order_id",
    "subaccount_id",
    "instrument_name",
    "direction",
    "order_type",
    "order_status",
    "time_in_force",
    "amount",
    "filled_amount",
    "limit_price",
    "trigger_price",
    "trigger_price_type",
    "order_fee",
    "max_fee",
]

POSITION_COLUMNS = [
    "subaccount_id",
    "instrument_name",
    "amount",
    "mark_price",
    "mark_value",
    "unrealized_pnl_excl_fees",
    "realized_pnl_excl_fees",
    "total_fees",
    "initial_margin",
    "maintenance_margin",
    "open_orders_margin",
    "net_settlements",
    "leverage",
    "liquidation_price",
    "cumulative_funding",
]

TICKER_COLUMNS = [
    "instrument_name",
    "best_bid_price",
    "best_bid_amount",
    "best_ask_price",
    "best_ask_amount",
    "mark_price",
    "index_price",
    "funding_rate",
]

TICKER_STATS_COLUMNS = [
    "instrument_name",
    "open_interest",
    "contract_volume_24h",
    "notional_volume_24h",
    "trade_count_24h",
    "high_24h",
    "low_24h",
    "percent_change_24h",
]

OPTION_PRICING_COLUMNS = [
    "instrument_name",
    "iv",
    "bid_iv",
    "ask_iv",
    "delta",
    "gamma",
    "vega",
    "theta",
    "rho",
]

OPEN_POSITION_COLUMNS = [
    "instrument_name",
    "instrument_type",
    "amount",
    "mark_price",
    "index_price",
    "mark_value",
    "unrealized_pnl",
    "realized_pnl",
    "leverage",
    "initial_margin",
    "maintenance_margin",
    "open_orders_margin",
    "liquidation_price",
    "total_fees",
]

TRADE_COLUMNS = [
    "trade_id",
    "instrument_name",
    "direction",
    "liquidity_role",
    "trade_amount",
    "trade_price",
    "mark_price",
    "trade_fee",
    "timestamp",
]

SUBACCOUNT_COLUMNS = [
    "subaccount_id",
    "label",
    "margin_type",
    "currency",
    "is_under_liquidation",
    "subaccount_value",
    "initial_margin",
    "maintenance_margin",
    "open_orders_margin",
    "projected_margin_change",
    "positions_value",
    "positions_initial_margin",
    "positions_maintenance_margin",
]

COLLATERAL_COLUMNS = [
    "asset_name",
    "amount",
    "initial_margin",
    "maintenance_margin",
    "open_orders_margin",
    "mark_price",
    "mark_value",
    "unrealized_pnl_excl_fees",
    "realized_pnl_excl_fees",
    "total_fees",
]

CURRENCY_COLUMNS = [
    "currency",
    "market_type",
    "spot_price",
    "spot_price_24h",
]

MANAGER_COLUMNS = [
    "currency",
    "risk_universe_id",
    "risk_universe_name",
    "pm",
    "sm",
]

SPOT_COLUMNS = [
    "currency",
    "address",
    "min_deposit_usd",
    "decimals",
    "underlying_erc20",
]

ASSET_COLUMNS = [
    "currency",
    "name",
    "address",
]

UNIVERSE_COLUMNS = [
    "risk_universe_id",
    "name",
    "description",
    "cash_currency",
    "cash_asset",
    "subaccount_id",
]

UNIVERSE_MANAGER_COLUMNS = [
    "risk_universe_id",
    "manager_id",
    "margin_type",
    "num_instruments",
    "num_collaterals",
]

UNIVERSE_COLLATERAL_COLUMNS = [
    "manager_id",
    "name",
    "address",
    "min_deposit_usd",
    "im_discount",
    "mm_discount",
    "decimals",
    "underlying_erc20",
]

SUBACCOUNT_COLLATERAL_COLUMNS = [
    "subaccount_id",
    *COLLATERAL_COLUMNS,
]

MMP_COLUMNS = [
    "subaccount_id",
    "currency",
    "is_frozen",
    "mmp_interval",
    "mmp_frozen_time",
    "mmp_unfreeze_time",
    "mmp_amount_limit",
    "mmp_delta_limit",
]

QUOTE_COLUMNS = [
    "liquidity_role",
    "subaccount_id",
    "direction",
    "status",
    "fill_pct",
    "fee",
    "max_fee",
    "quote_id",
    "rfq_id",
]
