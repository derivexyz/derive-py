# ruff: noqa: E741,E501
from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any, TypeAlias

from msgspec import UNSET, Struct, UnsetType, field

from derive_py.data_types.generated_models import (
    BatchStatus,
    DailyTradingStatistics,
    Direction,
    LiquidityRole,
    OptionPricing,
    PricedLegParamsAndResponse,
    PublicQuote,
    RFQCancelReason,
    RFQStatus,
)

DeriveWebsocketChannelSchemas: TypeAlias = Any
Address: TypeAlias = str


class SubaccountBalances(Struct):
    field_key_: str | UnsetType = field(name='{key}', default=UNSET)


class AuctionDetails(Struct):
    estimated_bid_price: str
    estimated_discount_pnl: str
    estimated_mtm: str
    estimated_percent_bid: str
    last_seen_trade_id: int
    margin_type: str
    min_cash_transfer: str
    min_price_limit: str
    subaccount_balances: SubaccountBalances
    currency: str | None = None


class AuctionStateType(StrEnum):
    ongoing = 'ongoing'
    ended = 'ended'


class BalanceUpdateType(StrEnum):
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


class LoginRequest(Struct):
    signature: str | UnsetType = UNSET
    timestamp: int | UnsetType = UNSET
    wallet: str | UnsetType = UNSET


class MarginWatchResult(Struct):
    collaterals: list[Any]
    currency: str
    initial_margin: str
    maintenance_margin: str
    margin_type: str
    positions: list[Any]
    subaccount_id: int
    subaccount_value: str
    valuation_timestamp: int


OrderSnapshot: TypeAlias = tuple[str, str]


class OrderbookSnapshot(Struct):
    asks: list[OrderSnapshot]
    bids: list[OrderSnapshot]
    instrument_name: str
    publish_id: int
    timestamp: int


class PublicTrade(Struct):
    direction: Direction
    index_price: str
    instrument_name: str
    mark_price: str
    timestamp: int
    trade_amount: str
    trade_id: str
    trade_price: str
    quote_id: str | None = None
    rfq_id: str | None = None


class RPCError(Struct):
    code: int
    message: str
    data: str | None = None


class SetCancelOnDisconnectRequest(Struct):
    enabled: bool | UnsetType = UNSET
    wallet: str | UnsetType = UNSET


class SpotFeedEntry(Struct):
    confidence: str
    confidence_prev_daily: str
    price: str
    price_prev_daily: str
    timestamp_prev_daily: int


class Feeds(Struct):
    field_key_: SpotFeedEntry | UnsetType = field(name='{key}', default=UNSET)


class SpotFeedPayload(Struct):
    feeds: Feeds
    timestamp: int


class TickerSlimSnapshot(
    Struct,
    rename={
        'best_ask_price': 'A',
        'best_bid_price': 'B',
        'index_price': 'I',
        'mark_price': 'M',
        'best_ask_amount': 'a',
        'best_bid_amount': 'b',
        'max_price': 'maxp',
        'min_price': 'minp',
        'timestamp': 't',
        'funding_rate': 'f',
    },
):
    best_ask_price: str
    best_bid_price: str
    index_price: str
    mark_price: str
    best_ask_amount: str
    best_bid_amount: str
    max_price: str
    min_price: str
    stats: DailyTradingStatistics
    timestamp: int
    funding_rate: str | None = None
    option_pricing: OptionPricing | None | UnsetType = UNSET


class AuctionResult(Struct):
    state: AuctionStateType
    subaccount_id: int
    timestamp: int
    details: AuctionDetails | None | UnsetType = UNSET


class BalanceUpdate(Struct):
    name: str
    new_balance: Decimal
    previous_balance: Decimal
    update_type: BalanceUpdateType


class QuotePublishResult(Struct):
    creation_timestamp: int
    direction: Direction
    extra_fee: Decimal
    fee: Decimal
    fill_pct: Decimal
    is_transfer: bool
    label: str
    last_update_timestamp: int
    legs: list[PricedLegParamsAndResponse]
    legs_hash: str
    liquidity_role: LiquidityRole
    max_fee: Decimal
    mmp: bool
    nonce: str
    quote_id: str
    rfq_id: str
    signature: str
    signature_expiry_sec: int
    signer: str
    status: RFQStatus
    subaccount_id: int
    batch_status: BatchStatus | None | UnsetType = UNSET
    cancel_reason: RFQCancelReason | None | UnsetType = UNSET
    tx_hash: str | None = None


class RfqGetBestQuoteResponse(Struct):
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
    down_liquidation_price: Decimal | None = None
    orderbook_total_cost: Decimal | None = None
    post_liquidation_price: Decimal | None = None
    up_liquidation_price: Decimal | None = None
    best_quote: PublicQuote | None | UnsetType = UNSET
    invalid_reason: str | None = None


class TickerSlimPayload(Struct):
    instrument_ticker: TickerSlimSnapshot
    timestamp: int


class BestQuoteChannelResult(Struct):
    rfq_id: str
    error: RPCError | None | UnsetType = UNSET
    result: RfqGetBestQuoteResponse | None | UnsetType = UNSET
