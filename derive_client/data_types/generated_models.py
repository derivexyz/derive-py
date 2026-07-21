# ruff: noqa: E741,E501
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, TypeAlias

from msgspec import Struct, field


class AccountFeeInfo(Struct):
    base_fee_discount: str
    rfq_maker_discount: str
    rfq_taker_discount: str
    option_maker_fee: Optional[str] = None
    option_taker_fee: Optional[str] = None
    perp_maker_fee: Optional[str] = None
    perp_taker_fee: Optional[str] = None
    spot_maker_fee: Optional[str] = None
    spot_taker_fee: Optional[str] = None


Address = str


class AlgoType(Enum):
    twap = 'twap'


class AssetType(Enum):
    option = 'option'
    perp = 'perp'
    erc20 = 'erc20'


class BatchStatus(Enum):
    Batching = 'Batching'
    Executing = 'Executing'
    Proving = 'Proving'
    Settling = 'Settling'
    Settled = 'Settled'
    BatchingError = 'BatchingError'
    ExecutingError = 'ExecutingError'
    ProvingError = 'ProvingError'
    SettlingError = 'SettlingError'
    SettledError = 'SettledError'


class CancelAlgoOrderRequest(Struct):
    order_id: str
    subaccount_id: int


class CancelAllAlgoOrdersRequest(Struct):
    subaccount_id: int


class CancelAllAlgoOrdersResponse(Enum):
    ok = 'ok'


class CancelAllRequest(Struct):
    subaccount_id: int
    cancel_algo_orders: Optional[bool] = None
    cancel_trigger_orders: Optional[bool] = None


class CancelAllTriggerOrdersRequest(CancelAllAlgoOrdersRequest):
    pass


class CancelBatchQuotesRequest(Struct):
    subaccount_id: int
    label: Optional[Any] = None
    nonce: Optional[Any] = None
    quote_id: Optional[str] = None
    rfq_id: Optional[str] = None


class CancelBatchResult(Struct):
    cancelled_ids: List[str]


class CancelBatchRfqsRequest(Struct):
    subaccount_id: int
    label: Optional[Any] = None
    nonce: Optional[Any] = None
    rfq_id: Optional[str] = None


class CancelBatchRfqsResponse(CancelBatchResult):
    pass


class CancelByInstrumentRequest(Struct):
    instrument_name: str
    subaccount_id: int


class CancelByInstrumentResponse(Struct):
    cancelled_orders: int


class CancelByLabelRequest(Struct):
    label: str
    subaccount_id: int
    instrument_name: Optional[str] = None


class CancelByLabelResponse(CancelByInstrumentResponse):
    pass


class CancelByNonceRequest(Struct):
    instrument_name: str
    nonce: int
    subaccount_id: int


class CancelByNonceResponse(CancelByInstrumentResponse):
    pass


class CancelOrderRequest(Struct):
    instrument_name: str
    order_id: str
    subaccount_id: int


class CancelQuoteRequest(Struct):
    quote_id: str
    subaccount_id: int
    label: Optional[Any] = None
    nonce: Optional[Any] = None
    rfq_id: Optional[str] = None


class CancelReason(Enum):
    field_ = ''
    user_request = 'user_request'
    mmp_trigger = 'mmp_trigger'
    insufficient_margin = 'insufficient_margin'
    signed_max_fee_too_low = 'signed_max_fee_too_low'
    cancel_on_disconnect = 'cancel_on_disconnect'
    ioc_or_market_partial_fill = 'ioc_or_market_partial_fill'
    session_key_deregistered = 'session_key_deregistered'
    subaccount_withdrawn = 'subaccount_withdrawn'
    compliance = 'compliance'
    trigger_failed = 'trigger_failed'
    validation_failed = 'validation_failed'
    algo_completed = 'algo_completed'


class CancelRfqRequest(Struct):
    rfq_id: str
    subaccount_id: int


class CancelTriggerOrderRequest(CancelAlgoOrderRequest):
    pass


class CancelVaultRequestRequest(Struct):
    nonce: int
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int
    vault_subaccount_id: int


class ChangeSubaccountLabelRequest(Struct):
    label: str
    subaccount_id: int


class Collateral(Struct):
    amount: str
    amount_step: str
    asset_name: str
    asset_type: str
    average_price: str
    average_price_excl_fees: str
    creation_timestamp: int
    cumulative_interest: str
    currency: str
    delta: str
    delta_currency: str
    initial_margin: str
    maintenance_margin: str
    mark_price: str
    mark_value: str
    open_orders_margin: str
    pending_interest: str
    realized_pnl: str
    realized_pnl_excl_fees: str
    total_fees: str
    unrealized_pnl: str
    unrealized_pnl_excl_fees: str


class CreateSessionKeyRequest(Struct):
    expiry_sec: int
    nonce: str
    offchain_scopes: List[str]
    protocol_scopes: List[str]
    public_session_key: str
    signature: str
    signature_expiry_sec: int
    signer: str
    wallet: str
    ip_whitelist: Optional[List[str]] = None
    label: Optional[str] = None
    subaccount_ids: Optional[List[int]] = None


class CreateVaultRequest(Struct):
    cooldown_sec: int
    deposit_spot_asset: Address
    initial_deposit: Decimal
    initial_share_price_usd: Decimal
    management_fee_bps: int
    manager_id: int
    max_fee_usd: Decimal
    max_slippage_bps: int
    nonce: int
    performance_fee_bps: int
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int
    benchmark_asset: Optional[Address] = None


class DailyTradingStatistics(Struct):
    c: Decimal
    h: Decimal
    l: Decimal
    n: int
    oi: Decimal
    p: Decimal
    pr: Decimal
    v: Decimal


class DepositEntry(Struct):
    amount: Decimal
    asset: str
    batch_status: BatchStatus
    batch_uuid: str
    fee: Decimal
    new_subaccount: bool
    operation_id: str
    subaccount_id: int
    timestamp: int
    wallet: str
    action_id: Optional[int] = None
    tx_hash: Optional[str] = None


class DepositHistoryResult(Struct):
    deposits: List[DepositEntry]


class DepositType(Enum):
    standard = 'standard'
    instant = 'instant'
    direct = 'direct'


class Direction(Enum):
    buy = 'buy'
    sell = 'sell'


class ERC20Details(Struct):
    borrow_index: str
    decimals: int
    supply_index: str
    underlying_erc20_address: str


class EditSessionKeyRequest(Struct):
    public_session_key: str
    wallet: str
    ip_whitelist: Optional[List[str]] = None
    label: Optional[str] = None
    offchain_scopes: Optional[List[str]] = None


EmptyRequest: TypeAlias = None


class Erc20Details(Struct):
    decimals: int
    underlying_erc20: Optional[str] = None


class ExecuteQuoteRequest(Struct):
    direction: Any
    legs: Any
    max_fee: Decimal
    nonce: Any
    quote_id: str
    rfq_id: str
    signature: Any
    signature_expiry_sec: Any
    signer: Any
    subaccount_id: int
    client: str = '8baller-python-sdk'
    enable_taker_protection: bool = False
    label: str = ''
    referral_code: str = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'


class ExpirySettlementPrice(Struct):
    expiry_date: str
    utc_expiry_sec: int
    price: Optional[str] = None


class ForceBurnRequest(Struct):
    holder: Address
    subaccount_id: int


class FundingRateCandle(Struct):
    close: str
    currency: str
    funding_rate: str
    high: str
    low: str
    open: str
    risk_universe_id: int
    timestamp: int


class FundingRateHistoryResult(Struct):
    funding_rate_history: List[FundingRateCandle]


class GetAccountRequest(Struct):
    wallet: Address


class GetAlgoOrdersRequest(CancelAllAlgoOrdersRequest):
    pass


class GetAllInstrumentsRequest(Struct):
    expired: bool
    instrument_type: AssetType
    currency: Optional[str] = None
    page: Optional[int] = None
    page_size: Optional[int] = None
    risk_universe_id: Optional[int] = None


class GetAllPortfoliosRequest(GetAccountRequest):
    pass


class GetAllReferralCodesParams(Struct):
    pass


class GetAssetsRequest(Struct):
    asset_type: AssetType
    currency: str
    expired: bool


class GetCollateralsRequest(CancelAllAlgoOrdersRequest):
    pass


class GetCuratedVaultsRequest(Struct):
    wallet: str


class GetCurrencyRequest(Struct):
    currency: str


class GetDepositHistoryRequest(Struct):
    end_timestamp: Optional[int] = None
    start_timestamp: Optional[int] = None
    subaccount_id: Optional[int] = None
    wallet: Optional[str] = None


class GetErc20TransferHistoryRequest(GetDepositHistoryRequest):
    pass


class GetFundingHistoryRequest(Struct):
    end_timestamp: Optional[int] = None
    instrument_name: Optional[str] = None
    page: Optional[int] = None
    page_size: Optional[int] = None
    start_timestamp: Optional[int] = None
    subaccount_id: Optional[int] = None
    wallet: Optional[str] = None


class GetFundingRateHistoryRequest(Struct):
    instrument_name: str
    end_timestamp: Optional[int] = None
    period: Optional[int] = None
    start_timestamp: Optional[int] = None


class GetIndexChartDataRequest(Struct):
    currency: str
    end_timestamp: int
    period: int
    start_timestamp: int


class GetInstrumentRequest(Struct):
    instrument_name: str


class GetInterestHistoryRequest(GetDepositHistoryRequest):
    pass


class GetInterestRateHistoryRequest(Struct):
    currency: str
    end_timestamp: Optional[int] = None
    period: Optional[int] = None
    risk_universe_id: Optional[int] = None
    start_timestamp: Optional[int] = None


class GetLatestSignedFeedsRequest(Struct):
    currency: Optional[str] = None
    expiry: Optional[int] = None


class GetLiveBurnRequestsRequest(Struct):
    limit: int
    subaccount_id: int


class GetLiveMintRequestsRequest(GetLiveBurnRequestsRequest):
    pass


class GetLiveVaultRequestsRequest(GetCuratedVaultsRequest):
    pass


class GetOnchainActionHistoryParams(Struct):
    action_type: Optional[int] = None
    end_timestamp: Optional[int] = None
    page: Optional[int] = None
    page_size: Optional[int] = None
    start_timestamp: Optional[int] = None
    wallet: Optional[str] = None


class GetOpenOrdersRequest(CancelAllAlgoOrdersRequest):
    pass


class GetOptionSettlementHistoryParams(Struct):
    subaccount_id: Optional[int] = None
    wallet: Optional[str] = None


class GetOptionSettlementPricesRequest(GetCurrencyRequest):
    pass


class GetOrderHistoryRequest(Struct):
    from_timestamp: Optional[int] = None
    page: Optional[int] = None
    page_size: Optional[int] = None
    subaccount_id: Optional[int] = None
    to_timestamp: Optional[int] = None
    wallet: Optional[str] = None


class GetOrderRequest(CancelAlgoOrderRequest):
    pass


class GetPendingDepositsParams(GetCuratedVaultsRequest):
    pass


class GetPositionsRequest(CancelAllAlgoOrdersRequest):
    pass


class GetPublicTradeHistoryRequest(Struct):
    currency: Optional[str] = None
    from_timestamp: Optional[int] = None
    instrument_name: Optional[str] = None
    instrument_type: Optional[str] = None
    page: Optional[int] = None
    page_size: Optional[int] = None
    subaccount_id: Optional[int] = None
    to_timestamp: Optional[int] = None
    trade_id: Optional[str] = None
    tx_status: Optional[str] = None


class GetQuotesRequest(Struct):
    subaccount_id: int
    from_timestamp: int = 0
    page: int = 1
    page_size: int = 20
    quote_id: Optional[str] = None
    rfq_id: Optional[str] = None
    status: Optional[str] = None
    to_timestamp: int = 9223372036854775807


class GetReferralPerformanceParams(Struct):
    end_ms: int
    start_ms: int
    referral_code: Optional[str] = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'
    wallet: Optional[str] = None


class GetRfqsRequest(Struct):
    subaccount_id: int
    from_timestamp: int = 0
    page: int = 1
    page_size: int = 20
    rfq_id: Optional[str] = None
    status: Optional[str] = None
    to_timestamp: int = 9223372036854775807


class GetShareholderVaultsRequest(GetCuratedVaultsRequest):
    pass


class GetSubaccountRequest(CancelAllAlgoOrdersRequest):
    pass


class GetSubaccountsRequest(GetAccountRequest):
    pass


class GetTickerRequest(GetInstrumentRequest):
    pass


class GetTickersRequest(Struct):
    instrument_type: AssetType
    currency: Optional[str] = None
    expiry_date: Optional[Any] = None


class GetTickersResponse(Struct):
    tickers: Dict[str, Any]


class GetTradeHistoryRequest(Struct):
    from_timestamp: Optional[int] = None
    instrument_name: Optional[str] = None
    order_id: Optional[str] = None
    page: Optional[int] = None
    page_size: Optional[int] = None
    quote_id: Optional[str] = None
    subaccount_id: Optional[int] = None
    to_timestamp: Optional[int] = None
    wallet: Optional[str] = None


class GetTradingviewChartDataRequest(Struct):
    end_timestamp: int
    instrument_name: str
    period: int
    start_timestamp: int


class GetTransactionParams(Struct):
    op_uuid: str


class GetTransactionResult(Struct):
    data: str
    error_log: Optional[str] = None
    status: Optional[BatchStatus] = None
    transaction_hash: Optional[str] = None


class GetTriggerOrdersRequest(CancelAllAlgoOrdersRequest):
    pass


class GetVaultActionHistoryRequest(Struct):
    subaccount_id: int
    event_type: Optional[str] = None
    page: Optional[int] = None
    page_size: Optional[int] = None


class GetVaultRequest(CancelAllAlgoOrdersRequest):
    pass


class GetVaultRequestHistoryRequest(Struct):
    wallet: str
    page: Optional[int] = None
    page_size: Optional[int] = None


class GetVaultSharesRequest(GetCuratedVaultsRequest):
    pass


class GetVaultsRequest(Struct):
    page: int = 1
    page_size: int = 100


class GetWithdrawalHistoryRequest(GetDepositHistoryRequest):
    pass


class IndexCandle(Struct):
    close_price: str
    high_price: str
    low_price: str
    open_price: str
    price: str
    timestamp: int
    timestamp_bucket: int


class InterestPayment(Struct):
    interest: str
    subaccount_id: int
    timestamp: int


class LegUnpricedParams(Struct):
    amount: Decimal
    direction: Direction
    instrument_name: str


class LendingDetails(Struct):
    borrow_apy: str
    supply_apy: str
    total_borrow: str
    total_borrow_cap: str


class LiquidityRole(Enum):
    maker = 'maker'
    taker = 'taker'


class ManagerCollateral(Struct):
    address: str
    erc20: Erc20Details
    im_discount: str
    min_deposit_usd: str
    mm_discount: str
    name: str


class MarginType(Enum):
    SM = 'SM'
    PM2 = 'PM2'


class MarketType(Enum):
    ALL = 'ALL'
    SRM_BASE_ONLY = 'SRM_BASE_ONLY'
    SRM_OPTION_ONLY = 'SRM_OPTION_ONLY'
    SRM_PERP_ONLY = 'SRM_PERP_ONLY'
    CASH = 'CASH'


class MmpConfigResult(Struct):
    currency: str
    is_frozen: bool
    mmp_amount_limit: str
    mmp_delta_limit: str
    mmp_frozen_time: int
    mmp_interval: int
    mmp_unfreeze_time: int
    subaccount_id: int


class MmpScopeRequest(Struct):
    subaccount_id: int
    currency: Optional[str] = None


class OffchainAckResponse(Struct):
    status: str


class OffchainKeyScope(Enum):
    account_info = 'account_info'
    delete_session_key = 'delete_session_key'


class Ohlc(Struct):
    close: str
    high: str
    low: str
    open: str


class OnchainActionHistoryEntry(Struct):
    acc: str
    action_id: int
    action_type: int
    action_type_label: str
    block_number: int
    data: str
    l1_sender: str
    queue: str
    status: str
    updated_at: int
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    fallback_at: Optional[int] = None
    first_failed_at: Optional[int] = None
    last_failed_at: Optional[int] = None
    op_uuid: Optional[str] = None
    tx_hash: Optional[str] = None


class OpenInterestStats(Struct):
    current_open_interest: str
    interest_cap: str


class OptionDetails(Struct):
    expiry: int
    index: str
    option_type: str
    strike: str
    settlement_price: Optional[str] = None


class OptionPricing(Struct):
    ai: str
    bi: str
    d: str
    df: str
    f: str
    g: str
    i: str
    m: str
    r: str
    t: str
    v: str


class OptionSettlementPricesResult(Struct):
    expiries: List[ExpirySettlementPrice]


class OptionSettlementResponse(Struct):
    amount: str
    expiry: int
    instrument_name: str
    settlement_price: str
    settlement_value: str
    subaccount_id: int


class OracleSignatureDataResponse(Struct):
    signatures: List[str]
    signers: List[Address]


class OrderActionDataResponse(Struct):
    asset_address: str
    asset_sub_id: str
    desired_amount: Decimal
    is_bid: bool
    limit_price: Decimal
    recipient_id: int
    worst_fee: Decimal


class OrderActionInputData(Struct):
    data: OrderActionDataResponse
    expiry: int
    module: str
    nonce: int
    owner: str
    signer: str
    subaccount_id: int


class OrderDebugResponse(Struct):
    action_hash: str
    action_typehash: str
    domain_separator: str
    encoded_data: str
    encoded_data_hashed: str
    expected_signer: str
    input_data: OrderActionInputData
    module: str
    owner: str
    typed_data_hash: str
    recovered_signer: Optional[str] = None


class OrderStatus(Enum):
    open = 'open'
    filled = 'filled'
    rejected = 'rejected'
    cancelled = 'cancelled'
    expired = 'expired'
    untriggered = 'untriggered'
    algo_active = 'algo_active'


class OrderType(Enum):
    limit = 'limit'
    market = 'market'


class Pagination(Struct):
    count: int
    num_pages: int


class PendingDepositEntry(Struct):
    action_id: int
    action_type: str
    amount: str
    asset: str
    block_number: int
    deposit_type: str
    log_index: int
    manager_id: int
    status: str
    subaccount_id: int
    timestamp: int
    tx_hash: str
    updated_at_ms: int
    credit_nonce: Optional[str] = None


class PerformanceResolution(Enum):
    field_1h = '1h'
    field_8h = '8h'
    field_24h = '24h'
    field_1wk = '1wk'


class PerpDetails(Struct):
    aggregate_funding: str
    funding_rate: str
    index: str
    max_rate_per_hour: str
    min_rate_per_hour: str
    static_interest_rate: str


class PerpFeedDataResponse(Struct):
    confidence: str
    currency: str
    deadline: int
    signatures: OracleSignatureDataResponse
    spot_diff_value: str
    timestamp: int
    type: str


class PerpSettlementEventResponse(Struct):
    batch_status: BatchStatus
    batch_uuid: str
    funding: str
    instrument_name: str
    pnl: str
    subaccount_id: int
    timestamp: int
    tx_hash: Optional[str] = None


class PerpSettlementHistoryResponse(Struct):
    events: List[PerpSettlementEventResponse]
    pagination: Pagination


class PollQuotesRequest(GetQuotesRequest):
    pass


class PollRfqsRequest(Struct):
    subaccount_id: int
    from_timestamp: int = 0
    page: int = 1
    page_size: int = 20
    rfq_id: Optional[str] = None
    rfq_subaccount_id: Optional[int] = None
    status: Optional[str] = None
    to_timestamp: int = 9223372036854775807


class Position(Struct):
    amount: str
    amount_step: str
    average_price: str
    average_price_excl_fees: str
    creation_timestamp: int
    cumulative_funding: str
    delta: str
    gamma: str
    index_price: str
    initial_margin: str
    instrument_name: str
    instrument_type: str
    maintenance_margin: str
    mark_price: str
    mark_value: str
    net_settlements: str
    open_orders_margin: str
    pending_funding: str
    realized_pnl: str
    realized_pnl_excl_fees: str
    theta: str
    total_fees: str
    unrealized_pnl: str
    unrealized_pnl_excl_fees: str
    vega: str
    leverage: Optional[str] = None
    liquidation_price: Optional[str] = None


class PricedLegParamsAndResponse(Struct):
    amount: Decimal
    direction: Direction
    instrument_name: str
    price: Decimal


class PrivateChangeSubaccountLabelResponse(ChangeSubaccountLabelRequest):
    pass


class PrivateCreateSessionKeyResponse(Struct):
    expiry_sec: int
    ip_whitelist: List[str]
    offchain_scopes: List[str]
    protocol_scopes: List[str]
    public_session_key: str
    subaccount_ids: List[int]
    label: Optional[str] = None


class PrivateGetAccountResponse(Struct):
    cancel_on_disconnect: bool
    fee_info: AccountFeeInfo
    is_rfq_maker: bool
    per_endpoint_tps: Dict[str, int]
    subaccount_ids: List[int]
    wallet: str
    websocket_matching_tps: int
    websocket_non_matching_tps: int
    websocket_option_tps: int
    websocket_perp_tps: int
    creation_timestamp_sec: Optional[int] = None
    referral_code: Optional[str] = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'


class PrivateGetCollateralsResponse(Struct):
    collaterals: List[Collateral]
    subaccount_id: int


class PrivateGetPositionsResponse(Struct):
    positions: List[Position]
    subaccount_id: int


class PrivateGetSubaccountsResponse(Struct):
    subaccount_ids: List[int]
    wallet: str


class PrivateTransferSpotExternalRequest(Struct):
    amount: Decimal
    asset_name: str
    max_fee_usd: Decimal
    new_subaccount_manager: int
    nonce: int
    recipient_address: str
    signature: str
    signature_expiry_sec: int
    signer: str
    sub_id: int
    subaccount_id: int
    to_subaccount_id: int


class PrivateTransferSpotExternalResponse(Struct):
    op_uuid: str
    operation_id: int


class PrivateTransferSpotRequest(Struct):
    amount: Decimal
    asset_name: str
    max_fee_usd: Decimal
    new_subaccount_manager: int
    nonce: int
    signature: str
    signature_expiry_sec: int
    signer: str
    sub_id: int
    subaccount_id: int
    to_subaccount_id: int


class PrivateTransferSpotResponse(PrivateTransferSpotExternalResponse):
    pass


class PrivateWithdrawRequest(Struct):
    amount_in_underlying: str
    asset_name: str
    force_batch: bool
    max_fee_usd: Decimal
    nonce: int
    signature: str
    signature_expiry_sec: int
    signer: str
    subaccount_id: int


class PrivateWithdrawResponse(PrivateTransferSpotExternalResponse):
    pass


class PublicExecuteQuoteDebugRequest(Struct):
    direction: Direction
    legs: List[PricedLegParamsAndResponse]
    max_fee: Decimal
    nonce: int
    quote_id: str
    rfq_id: str
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int


class PublicGetWalletsFromSessionKeyResponse(Struct):
    wallets: List[str]


class PublicSendQuoteDebugRequest(Struct):
    direction: Direction
    legs: List[PricedLegParamsAndResponse]
    max_fee: Decimal
    nonce: int
    rfq_id: str
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int


class PublicVaultActionResponse(Struct):
    curator_shares_minted: Decimal
    event_ts: int
    event_type: str
    holder: str
    management_shares_minted: Decimal
    nav: Decimal
    new_high_water_mark: Decimal
    old_high_water_mark: Decimal
    operation_uuid: str
    performance_shares_minted: Decimal
    protocol_shares_minted: Decimal
    share_price: Decimal
    shares_delta: Decimal
    status: str
    subaccount_id: int
    total_shares: Decimal


class PublicWithdrawDebugRequest(Struct):
    amount_in_underlying: str
    asset_name: str
    force_batch: bool
    max_fee_usd: Decimal
    nonce: int
    signature_expiry_sec: int
    signer: str
    subaccount_id: int


class QuoteExecuteDebugResult(Struct):
    action_hash: str
    encoded_data: str
    encoded_data_hashed: str
    encoded_legs: str
    legs_hash: str
    typed_data_hash: str


class QuoteSendDebugResult(Struct):
    action_hash: str
    encoded_data: str
    encoded_data_hashed: str
    typed_data_hash: str


class RFQCancelReason(Enum):
    field_ = ''
    user_request = 'user_request'
    insufficient_margin = 'insufficient_margin'
    signed_max_fee_too_low = 'signed_max_fee_too_low'
    mmp_trigger = 'mmp_trigger'
    cancel_on_disconnect = 'cancel_on_disconnect'
    session_key_deregistered = 'session_key_deregistered'
    subaccount_withdrawn = 'subaccount_withdrawn'
    rfq_no_longer_open = 'rfq_no_longer_open'
    compliance = 'compliance'


class RFQStatus(Enum):
    open = 'open'
    filled = 'filled'
    cancelled = 'cancelled'
    expired = 'expired'


class RPCError(Struct):
    code: int
    message: str
    data: Optional[str] = None


class RateFeedDataResponse(Struct):
    confidence: str
    currency: str
    deadline: int
    expiry: int
    rate: str
    signatures: OracleSignatureDataResponse
    timestamp: int


class RateLimitInfo(Struct):
    consumedPoints: int
    isFirstInDuration: bool
    msBeforeNext: int
    remainingPoints: int


class RateLimitResult(Struct):
    remaining_matching: RateLimitInfo
    remaining_non_matching: RateLimitInfo
    remaining_per_endpoint: Dict[str, RateLimitInfo]
    remaining_connections: Optional[RateLimitInfo] = None


class ReferralPerformanceByInstrumentType(Struct):
    builder_fee: str
    fee_reward: str
    notional_volume: str
    referred_fee: str
    unique_traders_referred: int


class Referrer(Struct):
    wallet: str
    referral_code: str = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'
    receiving_wallet: Optional[str] = None


class RegisterDepositAddressParams(Struct):
    deposit_type: DepositType
    wallet: str
    manager_id: Optional[int] = None
    subaccount_id: int = 0


class RegisterDepositAddressResult(Struct):
    deposit_address: str
    deposit_type: DepositType
    wallet: str
    manager_id: Optional[int] = None
    subaccount_id: Optional[int] = None


class ReplaceQuoteRequest(Struct):
    direction: Any
    legs: Any
    max_fee: Decimal
    nonce: Any
    rfq_id: str
    signature: Any
    signature_expiry_sec: Any
    signer: Any
    subaccount_id: int
    client: str = '8baller-python-sdk'
    extra_fee: Decimal = Decimal('0')
    label: str = ''
    mmp: bool = False
    nonce_to_cancel: Optional[Any] = None
    quote_id_to_cancel: Optional[str] = None
    referral_code: str = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'


class RequestVaultDepositRequest(Struct):
    amount: Decimal
    deposit_spot_asset: Address
    nonce: int
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int
    vault_subaccount_id: int


class RequestVaultWithdrawRequest(Struct):
    nonce: int
    shares_to_burn: Decimal
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int
    vault_subaccount_id: int


class Rfq(Struct):
    cancel_reason: RFQCancelReason
    creation_timestamp: int
    filled_pct: Decimal
    label: str
    last_update_timestamp: int
    legs: List[LegUnpricedParams]
    partial_fill_step: Decimal
    rfq_id: str
    status: RFQStatus
    subaccount_id: int
    valid_until: int
    wallet: Address
    ask_total_cost: Optional[Decimal] = None
    bid_total_cost: Optional[Decimal] = None
    mark_total_cost: Optional[Decimal] = None
    max_total_cost: Optional[Decimal] = None
    min_total_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    counterparties: Optional[List[Address]] = None
    filled_direction: Optional[Direction] = None


class RfqGetBestQuoteRequest(Struct):
    direction: Any
    legs: Any
    subaccount_id: int


class RiskUniverseManager(Struct):
    collaterals: List[ManagerCollateral]
    instruments: List[str]
    manager_id: int
    margin_type: MarginType


class SecurityModuleDetails(Struct):
    cash_asset: str
    cash_currency: str
    subaccount_id: int


class SendQuoteRequest(Struct):
    direction: Direction
    legs: List[PricedLegParamsAndResponse]
    max_fee: Decimal
    nonce: int
    rfq_id: str
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int
    client: str = '8baller-python-sdk'
    extra_fee: Decimal = Decimal('0')
    label: str = ''
    mmp: bool = False
    referral_code: str = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'


class SendRfqRequest(Struct):
    legs: Any
    subaccount_id: int
    client: str = '8baller-python-sdk'
    counterparties: Optional[List[str]] = None
    extra_fee: Decimal = Decimal('0')
    label: str = ''
    max_total_cost: Optional[Decimal] = None
    min_total_cost: Optional[Decimal] = None
    partial_fill_step: Decimal = Decimal('1')
    referral_code: str = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'


class SessionKey(Struct):
    expiry_sec: int
    ip_whitelist: List[str]
    label: str
    offchain_scopes: List[str]
    protocol_scopes: List[str]
    public_session_key: str
    registered_sec: int
    subaccount_ids: List[int]


class SessionKeysRequest(GetCuratedVaultsRequest):
    pass


class SetMmpConfigRequest(Struct):
    currency: str
    mmp_frozen_time: int
    mmp_interval: int
    subaccount_id: int
    mmp_amount_limit: Decimal = Decimal('0')
    mmp_delta_limit: Decimal = Decimal('0')


class SetMmpConfigResponse(Struct):
    currency: str
    mmp_amount_limit: str
    mmp_delta_limit: str
    mmp_frozen_time: int
    mmp_interval: int
    subaccount_id: int


class SettledTrade(Struct):
    direction: Direction
    expected_rebate: Decimal
    extra_fee: Decimal
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
    wallet: str
    quote_id: Optional[str] = None
    rfq_id: Optional[str] = None
    tx_status: Optional[BatchStatus] = None


class SignedTransferQuoteRequest(Struct):
    direction: Direction
    legs: List[PricedLegParamsAndResponse]
    max_fee: Decimal
    nonce: str
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int


class SpotFeedDataResponse(Struct):
    confidence: str
    currency: str
    deadline: int
    price: str
    signatures: OracleSignatureDataResponse
    timestamp: int
    feed_source_type: Optional[str] = None


class SpotUniverse(Struct):
    oi: OpenInterestStats
    pm2_im_discount: str
    pm2_mm_discount: str
    risk_universe_id: int
    srm_im_discount: str
    srm_mm_discount: str
    lending: Optional[LendingDetails] = None


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
    funding_rate: Optional[str] = None
    option_pricing: Optional[OptionPricing] = None


class TimeInForce(Enum):
    gtc = 'gtc'
    post_only = 'post_only'
    fok = 'fok'
    ioc = 'ioc'


class TradeHistoryResponse(Struct):
    direction: Direction
    expected_rebate: Decimal
    extra_fee: Decimal
    index_price: Decimal
    instrument_name: str
    is_transfer: bool
    label: str
    liquidity_role: LiquidityRole
    mark_price: Decimal
    op_uuid: str
    order_id: str
    realized_pnl: Decimal
    realized_pnl_excl_fees: Decimal
    subaccount_id: int
    timestamp: int
    trade_amount: Decimal
    trade_fee: Decimal
    trade_id: str
    trade_price: Decimal
    quote_id: Optional[str] = None
    rfq_id: Optional[str] = None
    tx_hash: Optional[str] = None
    tx_status: Optional[BatchStatus] = None


class TradingviewCandle(Struct):
    close_price: str
    high_price: str
    low_price: str
    open_price: str
    timestamp: int
    timestamp_bucket: int
    volume_contracts: str
    volume_usd: str


class TransferEntry(Struct):
    amount: Decimal
    asset: str
    batch_status: BatchStatus
    batch_uuid: str
    fee: Decimal
    from_subaccount_id: int
    from_wallet: str
    is_outgoing: bool
    operation_id: str
    timestamp: int
    to_subaccount_id: int
    to_wallet: str
    tx_hash: Optional[str] = None


class TransferHistoryResult(Struct):
    transfers: List[TransferEntry]


class TransferPositionsRequest(Struct):
    maker_params: SignedTransferQuoteRequest
    taker_params: SignedTransferQuoteRequest
    wallet: Address


class TriggerPriceType(Enum):
    mark = 'mark'
    index = 'index'  # type: ignore


class TriggerType(Enum):
    stoploss = 'stoploss'
    takeprofit = 'takeprofit'


class TxStatus(Enum):
    requested = 'requested'
    pending = 'pending'
    settled = 'settled'
    reverted = 'reverted'
    ignored = 'ignored'
    timed_out = 'timed_out'
    applied = 'applied'
    in_batch = 'in_batch'
    proving = 'proving'
    submitted = 'submitted'


class UniverseManagers(Struct):
    risk_universe_id: int
    pm: Optional[int] = None
    risk_universe_name: Optional[str] = None
    sm: Optional[int] = None


class UpdateVaultInfoRequest(Struct):
    subaccount_id: int
    description: Optional[str] = None
    mtm_cap: Optional[Decimal] = None
    name: Optional[str] = None
    whitelist_only: Optional[bool] = None


class UpdateWhitelistedRecipientsRequest(Struct):
    add: List[str]
    nonce: int
    remove: List[str]
    signature: str
    signature_expiry_sec: int
    signer: str
    wallet: str


class UpdateWhitelistedRecipientsResponse(Struct):
    op_uuid: str
    operation_id: int
    whitelisted_recipients: List[str]


class VaultActionResponse(Struct):
    after_shares: Decimal
    amount: Decimal
    before_shares: Decimal
    creation_timestamp_ms: int
    entry_price: Decimal
    error_reason: str
    event_ts: int
    event_type: str
    exit_price: Decimal
    operation_id: int
    operation_uuid: str
    share_price: Decimal
    shares_delta: Decimal
    shares_requested: Decimal
    status: str
    user_action_hash: str
    vault_nonce: str
    vault_subaccount_id: int
    wallet: str


class VaultConfig(Struct):
    cooldown_sec: int
    deposit_spot_asset: Address
    management_fee_bps: int
    max_slippage_bps: int
    performance_fee_bps: int
    benchmark_asset: Optional[Address] = None


class VaultCreateResponse(PrivateTransferSpotExternalResponse):
    pass


class VaultDepositHold(Struct):
    amount: str
    asset_name: str
    currency: str
    vault_id: int


class VaultForceBurnResponse(PrivateTransferSpotExternalResponse):
    pass


class VaultIdsResponse(Struct):
    subaccount_ids: List[int]


class VaultPerformancePointResponse(Struct):
    curator_shares: Decimal
    global_hwm: Decimal
    share_price: Decimal
    total_shares: Decimal
    ts: int
    benchmark_price: Optional[Decimal] = None
    nav: Optional[Decimal] = None
    nav_benchmark: Optional[Decimal] = None


class VaultRequestId(Struct):
    vault_nonce: str
    vault_subaccount_id: int
    wallet: Address


class VaultSettleResponse(PrivateTransferSpotExternalResponse):
    pass


class VolSVIParamDataResponse(Struct):
    SVI_a: str
    SVI_b: str
    SVI_fwd: str
    SVI_m: str
    SVI_refTau: str
    SVI_rho: str
    SVI_sigma: str


class WithdrawalEntry(Struct):
    amount: Decimal
    asset: str
    batch_status: BatchStatus
    batch_uuid: str
    erc20_address: str
    fee: Decimal
    operation_id: str
    recipient: str
    subaccount_id: int
    timestamp: int
    wallet: str
    tx_hash: Optional[str] = None


class WithdrawalHistoryResult(Struct):
    withdrawals: List[WithdrawalEntry]


class Action(Struct):
    data: List[int]
    expiry: int
    module: Address
    nonce: int
    owner: Address
    signer: Address
    subaccount_id: int


class Asset(Struct):
    address: str
    asset_id: str
    asset_name: str
    asset_type: AssetType
    currency: str
    is_collateral: bool
    is_position: bool
    sub_id: str
    erc20_details: Optional[ERC20Details] = None
    option_details: Optional[OptionDetails] = None
    perp_details: Optional[PerpDetails] = None


class AssetUniverse(Struct):
    oi: OpenInterestStats
    risk_universe_id: int
    risk_universe_name: Optional[str] = None


class BurnSharesRequest(Struct):
    nonce: int
    request_id: VaultRequestId
    share_price: Decimal
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int
    withdraw_hash: str


class CreateOrderRequest(Struct):
    amount: Decimal
    direction: Direction
    instrument_name: str
    limit_price: Decimal
    max_fee: Decimal
    nonce: str
    signature: str
    signature_expiry_sec: int
    signer: str
    subaccount_id: int
    algo_duration_sec: Optional[int] = None
    algo_num_slices: Optional[int] = None
    algo_type: Optional[AlgoType] = None
    client: Optional[str] = '8baller-python-sdk'
    extra_fee: Optional[Decimal] = None
    is_atomic_signing: Optional[bool] = None
    label: Optional[str] = None
    mmp: Optional[bool] = None
    order_type: OrderType = OrderType('limit')
    reduce_only: Optional[bool] = None
    referral_code: Optional[str] = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'
    reject_post_only: Optional[bool] = None
    reject_timestamp: Optional[int] = None
    time_in_force: TimeInForce = TimeInForce('gtc')
    trigger_price: Optional[Decimal] = None
    trigger_price_type: Optional[TriggerPriceType] = None
    trigger_type: Optional[TriggerType] = None


class ForwardFeedDataResponse(Struct):
    confidence: str
    currency: str
    deadline: int
    expiry: int
    fwd_diff: str
    signatures: OracleSignatureDataResponse
    spot_aggregate_latest: str
    spot_aggregate_start: str
    timestamp: int


class GetOnchainActionHistoryResponse(Struct):
    actions: List[OnchainActionHistoryEntry]
    pagination: Pagination


class GetPendingDepositsResult(Struct):
    pending_deposits: List[PendingDepositEntry]
    wallet: str


class GetReferralPerformanceResult(Struct):
    fee_share_percentage: str
    rewards: Dict[str, Dict[str, Dict[str, ReferralPerformanceByInstrumentType]]]
    stdrv_balance: str
    total_builder_fee_collected: str
    total_fee_rewards: str
    total_notional_volume: str
    total_referred_fees: str
    referral_code: str = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'


class GetVaultPerformanceHistoryRequest(Struct):
    resolution: PerformanceResolution
    subaccount_id: int
    from_: Optional[int] = field(name='from', default=None)
    limit: Optional[int] = None
    to: Optional[int] = None


class GetWalletsFromSessionKeyRequest(Struct):
    public_session_key: str
    scope: Optional[OffchainKeyScope] = None


class Instrument(Struct):
    amount_step: str
    base_asset_address: str
    base_asset_sub_id: str
    base_currency: str
    base_fee: str
    fifo_min_allocation: str
    instrument_name: str
    instrument_type: AssetType
    is_active: bool
    maker_fee_rate: str
    maximum_amount: str
    minimum_amount: str
    pro_rata_amount_step: str
    pro_rata_fraction: str
    quote_currency: str
    scheduled_activation: int
    scheduled_deactivation: int
    taker_fee_rate: str
    tick_size: str
    erc20_details: Optional[ERC20Details] = None
    mark_price_fee_rate_cap: Optional[str] = None
    option_details: Optional[OptionDetails] = None
    perp_details: Optional[PerpDetails] = None


class InterestHistoryResult(Struct):
    events: List[InterestPayment]


class InterestRateCandle(Struct):
    borrow_apy: Ohlc
    risk_universe_id: int
    supply_apy: Ohlc
    timestamp: int
    total_borrow: str
    total_supply: str


class InterestRateHistoryResult(Struct):
    interest_rate_history: List[InterestRateCandle]


class MintSharesRequest(Struct):
    deposit_hash: str
    nonce: int
    request_id: VaultRequestId
    share_price: Decimal
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int


class OptionSettlementHistoryResponse(Struct):
    settlements: List[OptionSettlementResponse]


class Order(Struct):
    amount: Decimal
    average_price: Decimal
    creation_timestamp: int
    direction: Direction
    extra_fee: Decimal
    filled_amount: Decimal
    instrument_name: str
    is_transfer: bool
    last_update_timestamp: int
    limit_price: Decimal
    max_fee: Decimal
    mmp: bool
    nonce: str
    order_fee: Decimal
    order_id: str
    order_status: OrderStatus
    order_type: OrderType
    signature: str
    signature_expiry_sec: int
    signer: str
    subaccount_id: int
    time_in_force: TimeInForce
    quote_id: Optional[str] = None
    replaced_order_id: Optional[str] = None
    signed_limit_price: Optional[Decimal] = None
    trigger_price: Optional[Decimal] = None
    algo_duration_sec: Optional[int] = None
    algo_num_slices: Optional[int] = None
    algo_slices_completed: Optional[int] = None
    algo_type: Optional[AlgoType] = None
    cancel_reason: CancelReason = CancelReason('')
    label: str = ''
    trigger_price_type: Optional[TriggerPriceType] = None
    trigger_reject_message: Optional[str] = None
    trigger_type: Optional[TriggerType] = None


class OrderQuoteRequest(Struct):
    amount: Decimal
    direction: Direction
    instrument_name: str
    limit_price: Decimal
    max_fee: Decimal
    nonce: str
    signature: str
    signature_expiry_sec: int
    signer: str
    subaccount_id: int
    client: str = '8baller-python-sdk'
    extra_fee: Optional[Decimal] = None
    is_atomic_signing: bool = False
    label: str = ''
    mmp: bool = False
    order_type: OrderType = OrderType('limit')
    reduce_only: bool = False
    referral_code: str = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'
    reject_post_only: bool = True
    reject_timestamp: int = 9223372036854775807
    time_in_force: TimeInForce = TimeInForce('gtc')
    trigger_price: Optional[Decimal] = None
    trigger_price_type: Optional[TriggerPriceType] = None
    trigger_type: Optional[TriggerType] = None


class OrderQuoteResponse(Struct):
    estimated_fee: str
    estimated_fill_amount: str
    estimated_fill_price: str
    estimated_order_status: OrderStatus
    estimated_realized_pnl: str
    estimated_realized_pnl_excl_fees: str
    is_valid: bool
    post_initial_margin: str
    pre_initial_margin: str
    suggested_max_fee: str
    invalid_reason: Optional[str] = None
    max_amount: Optional[str] = None
    post_liquidation_price: Optional[str] = None


class PaginatedOrdersResult(Struct):
    orders: List[Order]
    pagination: Pagination
    subaccount_id: int


class PaginatedTradesResult(Struct):
    pagination: Pagination
    subaccount_id: int
    trades: List[TradeHistoryResponse]


class PaginatedVaultActions(Struct):
    actions: List[VaultActionResponse]
    pagination: Pagination
    wallet: str


class PrivateSessionKeysResponse(Struct):
    public_session_keys: List[SessionKey]


class ProtocolVault(Struct):
    closed: bool
    config: VaultConfig
    global_hwm: Decimal
    last_fee_settled_at_sec: int
    protocol_fee_share_bps: int
    subaccount_id: int
    total_shares: Decimal


class PublicQuote(Struct):
    cancel_reason: RFQCancelReason
    creation_timestamp: int
    direction: Direction
    fill_pct: Decimal
    last_update_timestamp: int
    legs: List[PricedLegParamsAndResponse]
    legs_hash: str
    liquidity_role: LiquidityRole
    quote_id: str
    rfq_id: str
    status: RFQStatus
    subaccount_id: int
    wallet: Address


class PublicRfq(Struct):
    cancel_reason: RFQCancelReason
    creation_timestamp: int
    filled_pct: Decimal
    last_update_timestamp: int
    legs: List[LegUnpricedParams]
    partial_fill_step: Decimal
    rfq_id: str
    status: RFQStatus
    subaccount_id: int
    valid_until: int
    wallet: Address
    fill_rate: Optional[Decimal] = None
    recent_fill_rate: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    filled_direction: Optional[Direction] = None


class PublicTradesResult(Struct):
    pagination: Pagination
    trades: List[SettledTrade]


class Quote(Struct):
    cancel_reason: RFQCancelReason
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
    signature_expiry_sec: int
    status: RFQStatus
    subaccount_id: int
    tx_hash: Optional[str] = None
    tx_status: Optional[TxStatus] = None


class QuoteExecuteResponse(Struct):
    cancel_reason: RFQCancelReason
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
    rfq_filled_pct: Decimal
    rfq_id: str
    signature_expiry_sec: int
    status: RFQStatus
    subaccount_id: int


class QuoteGetResponse(Struct):
    pagination: Pagination
    quotes: List[Quote]


class QuotePollResponse(Struct):
    pagination: Pagination
    quotes: List[PublicQuote]


class QuoteReplaceResponse(Struct):
    cancelled_quote: Quote
    create_quote_error: Optional[RPCError] = None
    quote: Optional[Quote] = None


class RFQGetResponse(Struct):
    pagination: Pagination
    rfqs: List[Rfq]


class RFQPollResponse(Struct):
    pagination: Pagination
    rfqs: List[PublicRfq]


class RejectDepositRequestRequest(Struct):
    request_id: VaultRequestId
    reason: Optional[str] = None


class ReplaceOrderRequest(Struct):
    amount: Decimal
    direction: Direction
    instrument_name: str
    limit_price: Decimal
    max_fee: Decimal
    nonce: str
    signature: str
    signature_expiry_sec: int
    signer: str
    subaccount_id: int
    algo_duration_sec: Optional[int] = None
    algo_num_slices: Optional[int] = None
    algo_type: Optional[AlgoType] = None
    client: Optional[str] = '8baller-python-sdk'
    expected_filled_amount: Optional[Decimal] = None
    extra_fee: Optional[Decimal] = None
    is_atomic_signing: Optional[bool] = None
    label: Optional[str] = None
    mmp: Optional[bool] = None
    nonce_to_cancel: Optional[int] = None
    order_id_to_cancel: Optional[str] = None
    order_type: OrderType = OrderType('limit')
    reduce_only: Optional[bool] = None
    referral_code: Optional[str] = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'
    reject_post_only: Optional[bool] = None
    reject_timestamp: Optional[int] = None
    time_in_force: TimeInForce = TimeInForce('gtc')
    trigger_price: Optional[Decimal] = None
    trigger_price_type: Optional[TriggerPriceType] = None
    trigger_type: Optional[TriggerType] = None


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
    down_liquidation_price: Optional[Decimal] = None
    orderbook_total_cost: Optional[Decimal] = None
    post_liquidation_price: Optional[Decimal] = None
    up_liquidation_price: Optional[Decimal] = None
    best_quote: Optional[PublicQuote] = None
    invalid_reason: Optional[str] = None


class RiskUniverse(Struct):
    managers: List[RiskUniverseManager]
    risk_universe_id: int
    security_module: SecurityModuleDetails
    description: Optional[str] = None
    name: Optional[str] = None


class SignedAction(Struct):
    action: Action
    signature: List[int]


class SpotAssetEntry(Struct):
    address: str
    erc20: Erc20Details
    min_deposit_usd: str
    name: str
    universes: List[SpotUniverse]


class Subaccount(Struct):
    collaterals: List[Collateral]
    collaterals_initial_margin: str
    collaterals_maintenance_margin: str
    collaterals_value: str
    currency: List[str]
    failed_to_fetch: bool
    initial_margin: str
    is_under_liquidation: bool
    label: str
    maintenance_margin: str
    manager_id: int
    margin_type: str
    open_orders: List[Order]
    open_orders_margin: str
    positions: List[Position]
    positions_initial_margin: str
    positions_maintenance_margin: str
    positions_value: str
    projected_margin_change: str
    risk_universe_id: int
    subaccount_id: int
    subaccount_value: str
    vault_deposit_holds: List[VaultDepositHold]


class Trade(Struct):
    direction: Direction
    expected_rebate: Decimal
    extra_fee: Decimal
    index_price: Decimal
    instrument_name: str
    is_transfer: bool
    liquidity_role: LiquidityRole
    mark_price: Decimal
    op_uuid: str
    order_id: str
    realized_pnl: Decimal
    realized_pnl_excl_fees: Decimal
    subaccount_id: int
    timestamp: int
    trade_amount: Decimal
    trade_fee: Decimal
    trade_id: str
    trade_price: Decimal
    tx_status: TxStatus
    quote_id: Optional[str] = None
    rfq_id: Optional[str] = None
    label: str = ''
    tx_hash: Optional[str] = None


class TransferPositionsResponse(Struct):
    maker_quote: Quote
    taker_quote: Quote


class Vault(Struct):
    curator: Address
    curator_shares: Decimal
    description: str
    name: str
    protocol: ProtocolVault
    whitelist_only: bool
    benchmark_price: Optional[Decimal] = None
    mtm_cap: Optional[Decimal] = None
    nav_benchmark: Optional[Decimal] = None
    nav_usd: Optional[Decimal] = None
    simulated_share_price_usd: Optional[Decimal] = None


class VaultCancelResponse(Struct):
    cancelled_request_ids: List[VaultRequestId]
    op_uuid: str
    operation_id: int


class VaultPerformanceHistoryResult(Struct):
    points: List[VaultPerformancePointResponse]
    resolution: PerformanceResolution
    subaccount_id: int


class VaultRequestAckResponse(Struct):
    request_id: VaultRequestId


class VaultRequestResponse(Struct):
    creation_timestamp_ms: int
    id: VaultRequestId
    signed_action: SignedAction
    subaccount_id: int
    user_action_hash: str
    wallet: Address


class VaultShareEntryResponse(Struct):
    shares: Decimal
    vault: Vault


class VaultSharesResponse(Struct):
    vaults: List[VaultShareEntryResponse]


class VaultsResponse(Struct):
    pagination: Pagination
    vaults: List[Vault]


class VolFeedDataResponse(Struct):
    confidence: str
    currency: str
    deadline: int
    expiry: int
    signatures: OracleSignatureDataResponse
    timestamp: int
    vol_data: VolSVIParamDataResponse


class AggregatedOrdersResult(Struct):
    orders: List[Order]
    subaccount_id: int


class AggregatedTriggerOrdersResult(AggregatedOrdersResult):
    pass


class AssetEntry(Struct):
    address: str
    name: str
    universes: List[AssetUniverse]


class Currency(Struct):
    currency: str
    managers: List[UniverseManagers]
    market_type: MarketType
    spot: List[SpotAssetEntry]
    spot_price: str
    option: Optional[AssetEntry] = None
    perp: Optional[AssetEntry] = None
    spot_price_24h: Optional[str] = None


class GetAllInstrumentsResponse(Struct):
    instruments: List[Instrument]
    pagination: Pagination


class GetLatestSignedFeedsResponse(Struct):
    fwd_data: Dict[str, Dict[str, ForwardFeedDataResponse]]
    perp_data: Dict[str, Dict[str, PerpFeedDataResponse]]
    rate_data: Dict[str, Dict[str, RateFeedDataResponse]]
    spot_data: Dict[str, SpotFeedDataResponse]
    vol_data: Dict[str, Dict[str, VolFeedDataResponse]]


class MultipleVaultRequestsResponse(Struct):
    requests: List[VaultRequestResponse]
    total: int


class OrderCreatedResponse(Struct):
    order: Order
    trades: List[Trade]


class ReplaceOrderResponse(Struct):
    cancelled_order: Order
    create_order_error: Optional[RPCError] = None
    order: Optional[Order] = None
    trades: Optional[List[Trade]] = None
