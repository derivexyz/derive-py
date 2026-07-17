# ruff: noqa: E741,E501
from __future__ import annotations

from decimal import Decimal
from enum import Enum, StrEnum
from typing import Any, TypeAlias

from msgspec import UNSET, Struct, UnsetType

from derive_client.data_types.generated_models import (
    AssetType,
    CancelAllAlgoOrdersRequest,
    DailyTradingStatistics,
    Direction,
    GetAllReferralCodesParams,
    GetCuratedVaultsRequest,
    GetCurrencyRequest,
    GetInstrumentRequest,
    LegUnpricedParams,
    LiquidityRole,
    RFQCancelReason,
    RFQStatus,
    RPCError,
)

DeriveWebsocketChannelSchemas: TypeAlias = Any


class AuctionsWatchChannelSchema(GetAllReferralCodesParams):
    pass


class MarginType(StrEnum):
    PM = 'PM'
    SM = 'SM'
    PM2 = 'PM2'


class Details(Struct):
    estimated_bid_price: Decimal
    estimated_discount_pnl: Decimal
    estimated_mtm: Decimal
    estimated_percent_bid: Decimal
    last_seen_trade_id: int
    margin_type: MarginType
    min_cash_transfer: Decimal
    min_price_limit: Decimal
    subaccount_balances: dict[str, Decimal]
    currency: str | None = None


class State(StrEnum):
    ongoing = 'ongoing'
    ended = 'ended'


class Datum(Struct):
    state: State
    subaccount_id: int
    timestamp: int
    details: Details | None = None


class Params(Struct):
    channel: str
    data: list[Datum]


class AuctionsWatchNotificationSchema(Struct):
    method: str
    params: Params


class Details1(Details):
    pass


class Datum1(Struct):
    state: State
    subaccount_id: int
    timestamp: int
    details: Details1 | None = None


class AuctionsWatchNotificationParamsSchema(Struct):
    channel: str
    data: list[Datum1]


class Details2(Details):
    pass


class AuctionResultSchema(Struct):
    state: State
    subaccount_id: int
    timestamp: int
    details: Details2 | None = None


class AuctionDetailsSchema(Details):
    pass


class Details3(Details):
    pass


class Datum2(Struct):
    state: State
    subaccount_id: int
    timestamp: int
    details: Details3 | None = None


class Params1(Struct):
    channel: str
    data: list[Datum2]


class Notification(Struct):
    method: str
    params: Params1


class AuctionsWatchPubSubSchema(Struct):
    channel_params: dict[str, Any]
    notification: Notification


class MarginWatchChannelSchema(AuctionsWatchChannelSchema):
    pass


class Collateral(Struct):
    amount: Decimal
    asset_name: str
    asset_type: AssetType
    initial_margin: Decimal
    maintenance_margin: Decimal
    mark_price: Decimal
    mark_value: Decimal


class Position(Struct):
    amount: Decimal
    delta: Decimal
    gamma: Decimal
    index_price: Decimal
    initial_margin: Decimal
    instrument_name: str
    instrument_type: AssetType
    maintenance_margin: Decimal
    mark_price: Decimal
    mark_value: Decimal
    theta: Decimal
    vega: Decimal
    liquidation_price: Decimal | None = None


class Datum3(Struct):
    collaterals: list[Collateral]
    currency: str
    initial_margin: Decimal
    maintenance_margin: Decimal
    margin_type: MarginType
    positions: list[Position]
    subaccount_id: int
    subaccount_value: Decimal
    valuation_timestamp: int


class Params2(Struct):
    channel: str
    data: list[Datum3]


class MarginWatchNotificationSchema(Struct):
    method: str
    params: Params2


class Collateral1(Collateral):
    pass


class Position1(Position):
    pass


class Datum4(Struct):
    collaterals: list[Collateral1]
    currency: str
    initial_margin: Decimal
    maintenance_margin: Decimal
    margin_type: MarginType
    positions: list[Position1]
    subaccount_id: int
    subaccount_value: Decimal
    valuation_timestamp: int


class MarginWatchNotificationParamsSchema(Struct):
    channel: str
    data: list[Datum4]


class Collateral2(Collateral):
    pass


class Position2(Position):
    pass


class MarginWatchResultSchema(Struct):
    collaterals: list[Collateral2]
    currency: str
    initial_margin: Decimal
    maintenance_margin: Decimal
    margin_type: MarginType
    positions: list[Position2]
    subaccount_id: int
    subaccount_value: Decimal
    valuation_timestamp: int


class CollateralPublicResponseSchema(Collateral):
    pass


class PositionPublicResponseSchema(Position):
    pass


class Collateral3(Collateral):
    pass


class Position3(Position):
    pass


class Datum5(Struct):
    collaterals: list[Collateral3]
    currency: str
    initial_margin: Decimal
    maintenance_margin: Decimal
    margin_type: MarginType
    positions: list[Position3]
    subaccount_id: int
    subaccount_value: Decimal
    valuation_timestamp: int


class Params3(Struct):
    channel: str
    data: list[Datum5]


class Notification1(Struct):
    method: str
    params: Params3


class MarginWatchPubSubSchema(Struct):
    channel_params: dict[str, Any]
    notification: Notification1


class Depth(StrEnum):
    field_1 = '1'
    field_10 = '10'
    field_20 = '20'
    field_100 = '100'


class Group(StrEnum):
    field_1 = '1'
    field_10 = '10'
    field_100 = '100'


class OrderbookInstrumentNameGroupDepthChannelSchema(Struct):
    depth: Depth
    group: Group
    instrument_name: str


class Data(Struct):
    asks: list[list[Decimal]]
    bids: list[list[Decimal]]
    instrument_name: str
    publish_id: int
    timestamp: int


class Params4(Struct):
    channel: str
    data: Data


class OrderbookInstrumentNameGroupDepthNotificationSchema(Struct):
    method: str
    params: Params4


class OrderbookInstrumentNameGroupDepthNotificationParamsSchema(Params4):
    pass


class OrderbookInstrumentNameGroupDepthPublisherDataSchema(Data):
    pass


class ChannelParams(OrderbookInstrumentNameGroupDepthChannelSchema):
    pass


class Params5(Params4):
    pass


class Notification2(Struct):
    method: str
    params: Params5


class OrderbookInstrumentNameGroupDepthPubSubSchema(Struct):
    channel_params: ChannelParams
    notification: Notification2


class SpotFeedCurrencyChannelSchema(GetCurrencyRequest):
    pass


class Feeds(Struct):
    confidence: Decimal
    confidence_prev_daily: Decimal
    price: Decimal
    price_prev_daily: Decimal
    timestamp_prev_daily: int


class Data3(Struct):
    feeds: dict[str, Feeds]
    timestamp: int


class Params6(Struct):
    channel: str
    data: Data3


class SpotFeedCurrencyNotificationSchema(Struct):
    method: str
    params: Params6


class Data4(Data3):
    pass


class SpotFeedCurrencyNotificationParamsSchema(Struct):
    channel: str
    data: Data4


class SpotFeedCurrencyPublisherDataSchema(Data3):
    pass


class SpotFeedSnapshotSchema(Feeds):
    pass


class ChannelParams1(SpotFeedCurrencyChannelSchema):
    pass


class Data5(Data3):
    pass


class Params7(Struct):
    channel: str
    data: Data5


class Notification3(Struct):
    method: str
    params: Params7


class SpotFeedCurrencyPubSubSchema(Struct):
    channel_params: ChannelParams1
    notification: Notification3


class SubaccountIdBalancesChannelSchema(CancelAllAlgoOrdersRequest):
    pass


class UpdateType(StrEnum):
    trade = 'trade'
    asset_deposit = 'asset_deposit'
    asset_withdrawal = 'asset_withdrawal'
    transfer = 'transfer'
    subaccount_deposit = 'subaccount_deposit'
    subaccount_withdrawal = 'subaccount_withdrawal'
    liquidation = 'liquidation'
    liquidator = 'liquidator'
    onchain_drift_fix = 'onchain_drift_fix'
    perp_settlement = 'perp_settlement'
    option_settlement = 'option_settlement'
    interest_accrual = 'interest_accrual'
    onchain_revert = 'onchain_revert'
    double_revert = 'double_revert'


class Datum6(Struct):
    name: str
    new_balance: Decimal
    previous_balance: Decimal
    update_type: UpdateType


class Params8(Struct):
    channel: str
    data: list[Datum6]


class SubaccountIdBalancesNotificationSchema(Struct):
    method: str
    params: Params8


class Datum7(Datum6):
    pass


class SubaccountIdBalancesNotificationParamsSchema(Struct):
    channel: str
    data: list[Datum7]


class BalanceUpdateSchema(Datum6):
    pass


class ChannelParams2(SubaccountIdBalancesChannelSchema):
    pass


class Datum8(Datum6):
    pass


class Params9(Struct):
    channel: str
    data: list[Datum8]


class Notification4(Struct):
    method: str
    params: Params9


class SubaccountIdBalancesPubSubSchema(Struct):
    channel_params: ChannelParams2
    notification: Notification4


class SubaccountIdBestQuotesChannelSchema(SubaccountIdBalancesChannelSchema):
    pass


class Error(RPCError):
    pass


class TxStatus(Enum):
    requested = 'requested'
    pending = 'pending'
    settled = 'settled'
    reverted = 'reverted'
    ignored = 'ignored'
    timed_out = 'timed_out'


class BestQuote(Struct):
    cancel_reason: RFQCancelReason
    creation_timestamp: int
    direction: Direction
    fill_pct: Decimal
    last_update_timestamp: int
    legs: list[dict[str, Any]]
    legs_hash: str
    liquidity_role: LiquidityRole
    quote_id: str
    rfq_id: str
    status: RFQStatus
    subaccount_id: int
    tx_status: TxStatus
    wallet: str
    tx_hash: str | None = None


class InvalidReason(Enum):
    Account_is_currently_under_maintenance_margin_requirements__trading_is_frozen_ = (
        'Account is currently under maintenance margin requirements, trading is frozen.'
    )
    This_order_would_cause_account_to_fall_under_maintenance_margin_requirements_ = (
        'This order would cause account to fall under maintenance margin requirements.'
    )
    Insufficient_buying_power__only_a_single_risk_reducing_open_order_is_allowed_ = (
        'Insufficient buying power, only a single risk-reducing open order is allowed.'
    )
    Insufficient_buying_power__consider_reducing_order_size_ = (
        'Insufficient buying power, consider reducing order size.'
    )
    Insufficient_buying_power__consider_reducing_order_size_or_canceling_other_orders_ = (
        'Insufficient buying power, consider reducing order size or canceling other orders.'
    )
    Consider_canceling_other_limit_orders_or_using_IOC__FOK__or_market_orders__This_order_is_risk_reducing__but_if_filled_with_other_open_orders__buying_power_might_be_insufficient_ = 'Consider canceling other limit orders or using IOC, FOK, or market orders. This order is risk-reducing, but if filled with other open orders, buying power might be insufficient.'
    Insufficient_buying_power_ = 'Insufficient buying power.'


class Result(Struct):
    direction: Direction
    estimated_fee: Decimal
    estimated_realized_pnl: Decimal
    estimated_realized_pnl_excl_fees: Decimal
    estimated_total_cost: Decimal
    filled_pct: Decimal
    is_valid: bool
    post_initial_margin: Decimal
    pre_initial_margin: Decimal
    suggested_max_fee: Decimal
    best_quote: BestQuote | None = None
    down_liquidation_price: Decimal | None = None
    invalid_reason: InvalidReason | None = None
    orderbook_total_cost: Decimal | None = None
    post_liquidation_price: Decimal | None = None
    up_liquidation_price: Decimal | None = None


class Datum9(Struct):
    rfq_id: str
    error: Error | None | UnsetType = UNSET
    result: Result | None | UnsetType = UNSET


class Params10(Struct):
    channel: str
    data: list[Datum9]


class SubaccountIdBestQuotesNotificationSchema(Struct):
    method: str
    params: Params10


class BestQuote1(BestQuote):
    pass


class Result1(Struct):
    direction: Direction
    estimated_fee: Decimal
    estimated_realized_pnl: Decimal
    estimated_realized_pnl_excl_fees: Decimal
    estimated_total_cost: Decimal
    filled_pct: Decimal
    is_valid: bool
    post_initial_margin: Decimal
    pre_initial_margin: Decimal
    suggested_max_fee: Decimal
    best_quote: BestQuote1 | None = None
    down_liquidation_price: Decimal | None = None
    invalid_reason: InvalidReason | None = None
    orderbook_total_cost: Decimal | None = None
    post_liquidation_price: Decimal | None = None
    up_liquidation_price: Decimal | None = None


class Datum10(Struct):
    rfq_id: str
    error: Error | None | UnsetType = UNSET
    result: Result1 | None | UnsetType = UNSET


class SubaccountIdBestQuotesNotificationParamsSchema(Struct):
    channel: str
    data: list[Datum10]


class BestQuote2(BestQuote):
    pass


class Result2(Struct):
    direction: Direction
    estimated_fee: Decimal
    estimated_realized_pnl: Decimal
    estimated_realized_pnl_excl_fees: Decimal
    estimated_total_cost: Decimal
    filled_pct: Decimal
    is_valid: bool
    post_initial_margin: Decimal
    pre_initial_margin: Decimal
    suggested_max_fee: Decimal
    best_quote: BestQuote2 | None = None
    down_liquidation_price: Decimal | None = None
    invalid_reason: InvalidReason | None = None
    orderbook_total_cost: Decimal | None = None
    post_liquidation_price: Decimal | None = None
    up_liquidation_price: Decimal | None = None


class BestQuoteChannelResultSchema(Struct):
    rfq_id: str
    error: Error | None | UnsetType = UNSET
    result: Result2 | None | UnsetType = UNSET


class RPCErrorFormatSchema(Error):
    pass


class BestQuote3(BestQuote):
    pass


class RFQGetBestQuoteResultSchema(Struct):
    direction: Direction
    estimated_fee: Decimal
    estimated_realized_pnl: Decimal
    estimated_realized_pnl_excl_fees: Decimal
    estimated_total_cost: Decimal
    filled_pct: Decimal
    is_valid: bool
    post_initial_margin: Decimal
    pre_initial_margin: Decimal
    suggested_max_fee: Decimal
    best_quote: BestQuote3 | None = None
    down_liquidation_price: Decimal | None = None
    invalid_reason: InvalidReason | None = None
    orderbook_total_cost: Decimal | None = None
    post_liquidation_price: Decimal | None = None
    up_liquidation_price: Decimal | None = None


class QuoteResultPublicSchema(BestQuote):
    pass


LegPricedSchema: TypeAlias = Any


class BestQuote4(BestQuote):
    pass


class Result3(Struct):
    direction: Direction
    estimated_fee: Decimal
    estimated_realized_pnl: Decimal
    estimated_realized_pnl_excl_fees: Decimal
    estimated_total_cost: Decimal
    filled_pct: Decimal
    is_valid: bool
    post_initial_margin: Decimal
    pre_initial_margin: Decimal
    suggested_max_fee: Decimal
    best_quote: BestQuote4 | None = None
    down_liquidation_price: Decimal | None = None
    invalid_reason: InvalidReason | None = None
    orderbook_total_cost: Decimal | None = None
    post_liquidation_price: Decimal | None = None
    up_liquidation_price: Decimal | None = None


class Datum11(Struct):
    rfq_id: str
    error: Error | None | UnsetType = UNSET
    result: Result3 | None | UnsetType = UNSET


class Params11(Struct):
    channel: str
    data: list[Datum11]


class Notification5(Struct):
    method: str
    params: Params11


class SubaccountIdBestQuotesPubSubSchema(Struct):
    channel_params: ChannelParams2
    notification: Notification5


class SubaccountIdOrdersChannelSchema(SubaccountIdBalancesChannelSchema):
    pass


class Params12(Struct):
    channel: str
    data: list[dict[str, Any]]


class SubaccountIdOrdersNotificationSchema(Struct):
    method: str
    params: Params12


class SubaccountIdOrdersNotificationParamsSchema(Params12):
    pass


OrderResponseSchema: TypeAlias = LegPricedSchema


class Notification6(SubaccountIdOrdersNotificationSchema):
    pass


class SubaccountIdOrdersPubSubSchema(Struct):
    channel_params: ChannelParams2
    notification: Notification6


class SubaccountIdQuotesChannelSchema(SubaccountIdBalancesChannelSchema):
    pass


class SubaccountIdQuotesNotificationSchema(SubaccountIdOrdersNotificationSchema):
    pass


class SubaccountIdQuotesNotificationParamsSchema(Params12):
    pass


QuoteResultSchema: TypeAlias = LegPricedSchema


class Notification7(SubaccountIdOrdersNotificationSchema):
    pass


class SubaccountIdQuotesPubSubSchema(Struct):
    channel_params: ChannelParams2
    notification: Notification7


class SubaccountIdTradesChannelSchema(SubaccountIdBalancesChannelSchema):
    pass


class SubaccountIdTradesNotificationSchema(SubaccountIdOrdersNotificationSchema):
    pass


class SubaccountIdTradesNotificationParamsSchema(Params12):
    pass


TradeResponseSchema: TypeAlias = LegPricedSchema


class Notification8(SubaccountIdOrdersNotificationSchema):
    pass


class SubaccountIdTradesPubSubSchema(Struct):
    channel_params: ChannelParams2
    notification: Notification8


class TxStatus6(StrEnum):
    settled = 'settled'
    reverted = 'reverted'
    timed_out = 'timed_out'


class SubaccountIdTradesTxStatusChannelSchema(Struct):
    subaccount_id: int
    tx_status: TxStatus6


class SubaccountIdTradesTxStatusNotificationSchema(SubaccountIdOrdersNotificationSchema):
    pass


class SubaccountIdTradesTxStatusNotificationParamsSchema(Params12):
    pass


class ChannelParams7(SubaccountIdTradesTxStatusChannelSchema):
    pass


class Notification9(SubaccountIdOrdersNotificationSchema):
    pass


class SubaccountIdTradesTxStatusPubSubSchema(Struct):
    channel_params: ChannelParams7
    notification: Notification9


class Interval(StrEnum):
    field_100 = '100'
    field_1000 = '1000'


class TickerSlimInstrumentNameIntervalChannelSchema(Struct):
    instrument_name: str
    interval: Interval


class OptionPricing(Struct):
    ai: Decimal
    bi: Decimal
    d: Decimal
    df: Decimal
    f: Decimal
    g: Decimal
    i: Decimal
    m: Decimal
    r: Decimal
    t: Decimal
    v: Decimal


class Stats(DailyTradingStatistics):
    pass


class InstrumentTicker(Struct):
    A: Decimal
    B: Decimal
    I: Decimal
    M: Decimal
    a: Decimal
    b: Decimal
    maxp: Decimal
    minp: Decimal
    stats: Stats
    t: int
    f: Decimal | None = None
    option_pricing: OptionPricing | None = None


class Data6(Struct):
    instrument_ticker: InstrumentTicker
    timestamp: int


class Params20(Struct):
    channel: str
    data: Data6


class TickerSlimInstrumentNameIntervalNotificationSchema(Struct):
    method: str
    params: Params20


class InstrumentTicker1(InstrumentTicker):
    pass


class Data7(Struct):
    instrument_ticker: InstrumentTicker1
    timestamp: int


class TickerSlimInstrumentNameIntervalNotificationParamsSchema(Struct):
    channel: str
    data: Data7


class InstrumentTicker2(InstrumentTicker):
    pass


class TickerSlimInstrumentNameIntervalPublisherDataSchema(Struct):
    instrument_ticker: InstrumentTicker2
    timestamp: int


class TickerSlimSchema(InstrumentTicker):
    pass


class OptionPricingSlimSchema(OptionPricing):
    pass


class AggregateTradingStatsSlimSchema(Stats):
    pass


class ChannelParams8(TickerSlimInstrumentNameIntervalChannelSchema):
    pass


class InstrumentTicker3(InstrumentTicker):
    pass


class Data8(Struct):
    instrument_ticker: InstrumentTicker3
    timestamp: int


class Params21(Struct):
    channel: str
    data: Data8


class Notification10(Struct):
    method: str
    params: Params21


class TickerSlimInstrumentNameIntervalPubSubSchema(Struct):
    channel_params: ChannelParams8
    notification: Notification10


class TradesInstrumentNameChannelSchema(GetInstrumentRequest):
    pass


class Datum12(Struct):
    direction: Direction
    index_price: Decimal
    instrument_name: str
    mark_price: Decimal
    timestamp: int
    trade_amount: Decimal
    trade_id: str
    trade_price: Decimal
    quote_id: str | None = None


class Params22(Struct):
    channel: str
    data: list[Datum12]


class TradesInstrumentNameNotificationSchema(Struct):
    method: str
    params: Params22


class Datum13(Datum12):
    pass


class TradesInstrumentNameNotificationParamsSchema(Struct):
    channel: str
    data: list[Datum13]


class TradePublicResponseSchema(Datum12):
    pass


class ChannelParams9(TradesInstrumentNameChannelSchema):
    pass


class Datum14(Datum12):
    pass


class Params23(Struct):
    channel: str
    data: list[Datum14]


class Notification11(Struct):
    method: str
    params: Params23


class TradesInstrumentNamePubSubSchema(Struct):
    channel_params: ChannelParams9
    notification: Notification11


class TradesInstrumentTypeCurrencyChannelSchema(Struct):
    currency: str
    instrument_type: AssetType


class Datum15(Datum12):
    pass


class Params24(Struct):
    channel: str
    data: list[Datum15]


class TradesInstrumentTypeCurrencyNotificationSchema(Struct):
    method: str
    params: Params24


class Datum16(Datum12):
    pass


class TradesInstrumentTypeCurrencyNotificationParamsSchema(Struct):
    channel: str
    data: list[Datum16]


class ChannelParams10(TradesInstrumentTypeCurrencyChannelSchema):
    pass


class Datum17(Datum12):
    pass


class Params25(Struct):
    channel: str
    data: list[Datum17]


class Notification12(Struct):
    method: str
    params: Params25


class TradesInstrumentTypeCurrencyPubSubSchema(Struct):
    channel_params: ChannelParams10
    notification: Notification12


class TradesInstrumentTypeCurrencyTxStatusChannelSchema(Struct):
    currency: str
    instrument_type: AssetType
    tx_status: TxStatus6


class Datum18(Struct):
    direction: Direction
    expected_rebate: Decimal
    index_price: Decimal
    instrument_name: str
    liquidity_role: LiquidityRole
    mark_price: Decimal
    realized_pnl: Decimal
    realized_pnl_excl_fees: Decimal
    subaccount_id: int
    timestamp: int
    trade_amount: Decimal
    trade_fee: Decimal
    trade_id: str
    trade_price: Decimal
    tx_hash: str
    tx_status: TxStatus6
    wallet: str
    quote_id: str | None = None


class Params26(Struct):
    channel: str
    data: list[Datum18]


class TradesInstrumentTypeCurrencyTxStatusNotificationSchema(Struct):
    method: str
    params: Params26


class Datum19(Datum18):
    pass


class TradesInstrumentTypeCurrencyTxStatusNotificationParamsSchema(Struct):
    channel: str
    data: list[Datum19]


class TradeSettledPublicResponseSchema(Datum18):
    pass


class ChannelParams11(TradesInstrumentTypeCurrencyTxStatusChannelSchema):
    pass


class Datum20(Datum18):
    pass


class Params27(Struct):
    channel: str
    data: list[Datum20]


class Notification13(Struct):
    method: str
    params: Params27


class TradesInstrumentTypeCurrencyTxStatusPubSubSchema(Struct):
    channel_params: ChannelParams11
    notification: Notification13


class WalletRfqsChannelSchema(GetCuratedVaultsRequest):
    pass


class Params28(Params12):
    pass


class WalletRfqsNotificationSchema(Struct):
    method: str
    params: Params28


class WalletRfqsNotificationParamsSchema(Params12):
    pass


RFQResultPublicSchema: TypeAlias = LegPricedSchema


class LegUnpricedSchema(LegUnpricedParams):
    pass


class ChannelParams12(WalletRfqsChannelSchema):
    pass


class Notification14(WalletRfqsNotificationSchema):
    pass


class WalletRfqsPubSubSchema(Struct):
    channel_params: ChannelParams12
    notification: Notification14
