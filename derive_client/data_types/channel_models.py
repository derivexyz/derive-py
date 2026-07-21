# ruff: noqa: E741,E501
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional

from msgspec import Struct, field

from derive_client.data_types.generated_models import (
    Direction,
    LiquidityRole,
    PricedLegParamsAndResponse,
    RFQCancelReason,
    RfqGetBestQuoteResponse,
    RFQStatus,
    RPCError,
    TickerSlimSnapshot,
    TxStatus,
)

DeriveWebsocketChannelSchemas = Any


class AuctionDetails(Struct):
    estimated_bid_price: str
    estimated_discount_pnl: str
    estimated_mtm: str
    estimated_percent_bid: str
    last_seen_trade_id: int
    margin_type: str
    min_cash_transfer: str
    min_price_limit: str
    subaccount_balances: str
    currency: Optional[str] = None


class SpotFeedEntry(Struct):
    confidence: str
    confidence_prev_daily: str
    price: str
    price_prev_daily: str
    timestamp_prev_daily: int


class MarginWatchResult(Struct):
    collaterals: List
    currency: str
    initial_margin: str
    maintenance_margin: str
    margin_type: str
    positions: List
    subaccount_id: int
    subaccount_value: str
    valuation_timestamp: int


class OrderSnapshot(Struct):
    amount: str
    price: str


class AuctionStateType(Enum):
    ongoing = 'ongoing'
    ended = 'ended'


class BalanceUpdateType(Enum):
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


class AuctionResult(Struct):
    state: AuctionStateType
    subaccount_id: int
    timestamp: int
    details: Optional[AuctionDetails] = None


class OrderbookSnapshot(Struct):
    asks: List[OrderSnapshot]
    bids: List[OrderSnapshot]
    instrument_name: str
    publish_id: int
    timestamp: int


class Feeds(Struct):
    field_key_: Optional[SpotFeedEntry] = field(name='{key}', default=None)


class SpotFeedPayload(Struct):
    feeds: Feeds
    timestamp: int


class LoginRequest(Struct):
    signature: Optional[str] = None
    timestamp: Optional[int] = None
    wallet: Optional[str] = None


class BalanceUpdate(Struct):
    name: str
    new_balance: Decimal
    previous_balance: Decimal
    update_type: BalanceUpdateType


class SetCancelOnDisconnectRequest(Struct):
    enabled: Optional[bool] = None
    wallet: Optional[str] = None


Address = str


class PublicTrade(Struct):
    direction: Direction
    index_price: str
    instrument_name: str
    mark_price: str
    timestamp: int
    trade_amount: str
    trade_id: str
    trade_price: str
    quote_id: Optional[str] = None
    rfq_id: Optional[str] = None


class QuotePublishResult(Struct):
    creation_timestamp: int
    direction: Direction
    extra_fee: Decimal
    fee: Decimal
    fill_pct: Decimal
    is_transfer: bool
    label: str
    last_update_timestamp: int
    legs: List[PricedLegParamsAndResponse]
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
    cancel_reason: Optional[RFQCancelReason] = None
    tx_hash: Optional[str] = None
    tx_status: Optional[TxStatus] = None


class TickerSlimPayload(Struct):
    instrument_ticker: TickerSlimSnapshot
    timestamp: int


class BestQuoteChannelResult(Struct):
    rfq_id: str
    error: Optional[RPCError] = None
    result: Optional[RfqGetBestQuoteResponse] = None
