# ruff: noqa: E741,E501
from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import TypeAlias

from msgspec import UNSET, Struct, UnsetType, field


class AccountFeeInfo(Struct):
    base_fee_discount: str
    rfq_maker_discount: str
    rfq_taker_discount: str
    option_maker_fee: str | None | UnsetType = UNSET
    option_taker_fee: str | None | UnsetType = UNSET
    perp_maker_fee: str | None | UnsetType = UNSET
    perp_taker_fee: str | None | UnsetType = UNSET
    spot_maker_fee: str | None | UnsetType = UNSET
    spot_taker_fee: str | None | UnsetType = UNSET


Address: TypeAlias = str


class AlgoType(StrEnum):
    twap = 'twap'


class AssetType(StrEnum):
    option = 'option'
    perp = 'perp'
    erc20 = 'erc20'


class BatchStatus(StrEnum):
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


class CancelAllAlgoOrdersResponse(StrEnum):
    ok = 'ok'


class CancelAllRequest(Struct):
    subaccount_id: int
    cancel_algo_orders: bool | UnsetType = UNSET
    cancel_trigger_orders: bool | UnsetType = UNSET


class CancelAllTriggerOrdersRequest(CancelAllAlgoOrdersRequest):
    pass


class CancelBatchQuotesRequest(Struct):
    subaccount_id: int
    label: str | UnsetType = UNSET
    nonce: int | UnsetType = UNSET
    quote_id: str | UnsetType = UNSET
    rfq_id: str | UnsetType = UNSET


class CancelBatchResult(Struct):
    cancelled_ids: list[str]


class CancelBatchRfqsRequest(Struct):
    subaccount_id: int
    label: str | UnsetType = UNSET
    nonce: int | UnsetType = UNSET
    rfq_id: str | UnsetType = UNSET


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
    instrument_name: str | UnsetType = UNSET


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
    label: str | UnsetType = UNSET
    nonce: int | UnsetType = UNSET
    rfq_id: str | UnsetType = UNSET


class CancelReason(StrEnum):
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
    benchmark_asset: Address | UnsetType = UNSET


class DailyTradingStatistics(
    Struct,
    rename={
        'contract_volume_24h': 'c',
        'high_24h': 'h',
        'low_24h': 'l',
        'trade_count_24h': 'n',
        'open_interest': 'oi',
        'percent_change_24h': 'p',
        'premium_volume_24h': 'pr',
        'notional_volume_24h': 'v',
    },
):
    contract_volume_24h: Decimal
    high_24h: Decimal
    low_24h: Decimal
    trade_count_24h: int
    open_interest: Decimal
    percent_change_24h: Decimal
    premium_volume_24h: Decimal
    notional_volume_24h: Decimal


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
    action_id: int | None | UnsetType = UNSET
    tx_hash: str | None | UnsetType = UNSET


class DepositHistoryResult(Struct):
    deposits: list[DepositEntry]


class DepositType(StrEnum):
    standard = 'standard'
    instant = 'instant'
    direct = 'direct'


class Direction(StrEnum):
    buy = 'buy'
    sell = 'sell'


class EditSessionKeyRequest(Struct):
    public_session_key: str
    wallet: str
    ip_whitelist: list[str] | UnsetType = UNSET
    label: str | UnsetType = UNSET
    offchain_scopes: list[str] | UnsetType = UNSET


EmptyRequest: TypeAlias = None


class Erc20Details(Struct):
    decimals: int
    underlying_erc20: str | None | UnsetType = UNSET


class ExpirySettlementPrice(Struct):
    expiry_date: str
    utc_expiry_sec: int
    price: str | None | UnsetType = UNSET


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
    funding_rate_history: list[FundingRateCandle]


class GetAccountRequest(Struct):
    wallet: Address


class GetAlgoOrdersRequest(CancelAllAlgoOrdersRequest):
    pass


class GetAllInstrumentsRequest(Struct):
    expired: bool
    instrument_type: AssetType
    currency: str | UnsetType = UNSET
    page: int | UnsetType = UNSET
    page_size: int | UnsetType = UNSET
    risk_universe_id: int | UnsetType = UNSET


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
    end_timestamp: int | UnsetType = UNSET
    start_timestamp: int | UnsetType = UNSET
    subaccount_id: int | UnsetType = UNSET
    wallet: str | UnsetType = UNSET


class GetErc20TransferHistoryRequest(GetDepositHistoryRequest):
    pass


class GetFundingHistoryRequest(Struct):
    end_timestamp: int | UnsetType = UNSET
    instrument_name: str | UnsetType = UNSET
    page: int | UnsetType = UNSET
    page_size: int | UnsetType = UNSET
    start_timestamp: int | UnsetType = UNSET
    subaccount_id: int | UnsetType = UNSET
    wallet: str | UnsetType = UNSET


class GetFundingRateHistoryRequest(Struct):
    instrument_name: str
    end_timestamp: int | UnsetType = UNSET
    period: int | UnsetType = UNSET
    start_timestamp: int | UnsetType = UNSET


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
    end_timestamp: int | UnsetType = UNSET
    period: int | UnsetType = UNSET
    risk_universe_id: int | UnsetType = UNSET
    start_timestamp: int | UnsetType = UNSET


class GetLatestSignedFeedsRequest(Struct):
    currency: str | UnsetType = UNSET
    expiry: int | UnsetType = UNSET


class GetLiveBurnRequestsRequest(Struct):
    limit: int
    subaccount_id: int


class GetLiveMintRequestsRequest(GetLiveBurnRequestsRequest):
    pass


class GetLiveVaultRequestsRequest(GetCuratedVaultsRequest):
    pass


class GetOnchainActionHistoryParams(Struct):
    action_type: int | UnsetType = UNSET
    end_timestamp: int | UnsetType = UNSET
    page: int | UnsetType = UNSET
    page_size: int | UnsetType = UNSET
    start_timestamp: int | UnsetType = UNSET
    wallet: str | UnsetType = UNSET


class GetOpenOrdersRequest(CancelAllAlgoOrdersRequest):
    pass


class GetOptionSettlementHistoryParams(Struct):
    subaccount_id: int | UnsetType = UNSET
    wallet: str | UnsetType = UNSET


class GetOptionSettlementPricesRequest(GetCurrencyRequest):
    pass


class GetOrderHistoryRequest(Struct):
    from_timestamp: int | UnsetType = UNSET
    page: int | UnsetType = UNSET
    page_size: int | UnsetType = UNSET
    subaccount_id: int | UnsetType = UNSET
    to_timestamp: int | UnsetType = UNSET
    wallet: str | UnsetType = UNSET


class GetOrderRequest(CancelAlgoOrderRequest):
    pass


class GetPendingDepositsParams(GetCuratedVaultsRequest):
    pass


class GetPositionsRequest(CancelAllAlgoOrdersRequest):
    pass


class GetPublicTradeHistoryRequest(Struct):
    batch_status: BatchStatus | UnsetType = UNSET
    currency: str | UnsetType = UNSET
    from_timestamp: int | UnsetType = UNSET
    instrument_name: str | UnsetType = UNSET
    instrument_type: AssetType | UnsetType = UNSET
    page: int | UnsetType = UNSET
    page_size: int | UnsetType = UNSET
    subaccount_id: int | UnsetType = UNSET
    to_timestamp: int | UnsetType = UNSET
    trade_id: str | UnsetType = UNSET


class GetQuotesRequest(Struct):
    subaccount_id: int
    from_timestamp: int | UnsetType = 0
    page: int | UnsetType = 1
    page_size: int | UnsetType = 20
    quote_id: str | UnsetType = UNSET
    rfq_id: str | UnsetType = UNSET
    status: str | UnsetType = UNSET
    to_timestamp: int | UnsetType = 9223372036854776000


class GetReferralPerformanceParams(Struct):
    end_ms: int
    start_ms: int
    referral_code: str | UnsetType = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'
    wallet: str | UnsetType = UNSET


class GetRfqsRequest(Struct):
    subaccount_id: int
    from_timestamp: int | UnsetType = 0
    page: int | UnsetType = 1
    page_size: int | UnsetType = 20
    rfq_id: str | UnsetType = UNSET
    status: str | UnsetType = UNSET
    to_timestamp: int | UnsetType = 9223372036854776000


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
    currency: str | UnsetType = UNSET
    expiry_date: int | UnsetType = UNSET


class GetTradeHistoryRequest(Struct):
    from_timestamp: int | UnsetType = UNSET
    instrument_name: str | UnsetType = UNSET
    order_id: str | UnsetType = UNSET
    page: int | UnsetType = UNSET
    page_size: int | UnsetType = UNSET
    quote_id: str | UnsetType = UNSET
    subaccount_id: int | UnsetType = UNSET
    to_timestamp: int | UnsetType = UNSET
    wallet: str | UnsetType = UNSET


class GetTradingviewChartDataRequest(Struct):
    end_timestamp: int
    instrument_name: str
    period: int
    start_timestamp: int


class GetTransactionParams(Struct):
    op_uuid: str


class GetTransactionResult(Struct):
    data: str
    error_log: str | None | UnsetType = UNSET
    status: BatchStatus | None | UnsetType = UNSET
    transaction_hash: str | None | UnsetType = UNSET


class GetTriggerOrdersRequest(CancelAllAlgoOrdersRequest):
    pass


class GetVaultActionHistoryRequest(Struct):
    subaccount_id: int
    event_type: str | UnsetType = UNSET
    page: int | UnsetType = UNSET
    page_size: int | UnsetType = UNSET


class GetVaultRequest(CancelAllAlgoOrdersRequest):
    pass


class GetVaultRequestHistoryRequest(Struct):
    wallet: str
    page: int | UnsetType = UNSET
    page_size: int | UnsetType = UNSET


class GetVaultSharesRequest(GetCuratedVaultsRequest):
    pass


class GetVaultsRequest(Struct):
    page: int | UnsetType = 1
    page_size: int | UnsetType = 100


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


class LiquidityRole(StrEnum):
    maker = 'maker'
    taker = 'taker'


class ManagerCollateral(Struct):
    address: str
    erc20: Erc20Details
    im_discount: str
    min_deposit_usd: str
    mm_discount: str
    name: str


class MarginType(StrEnum):
    SM = 'SM'
    PM2 = 'PM2'


class MarketType(StrEnum):
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
    currency: str | UnsetType = UNSET


class OffchainAckResponse(Struct):
    status: str


class OffchainKeyScope(StrEnum):
    account_info = 'account_info'


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
    error_code: int | None | UnsetType = UNSET
    error_message: str | None | UnsetType = UNSET
    fallback_at: int | None | UnsetType = UNSET
    first_failed_at: int | None | UnsetType = UNSET
    last_failed_at: int | None | UnsetType = UNSET
    op_uuid: str | None | UnsetType = UNSET
    tx_hash: str | None | UnsetType = UNSET


class OpenInterestStats(Struct):
    current_open_interest: str
    interest_cap: str


class OptionDetails(Struct):
    expiry: int
    index: str
    option_type: str
    strike: str
    settlement_price: str | None | UnsetType = UNSET


class OptionPricing(
    Struct,
    rename={
        'ask_iv': 'ai',
        'bid_iv': 'bi',
        'delta': 'd',
        'discount_factor': 'df',
        'forward_price': 'f',
        'gamma': 'g',
        'iv': 'i',
        'mark_price': 'm',
        'rho': 'r',
        'theta': 't',
        'vega': 'v',
    },
):
    ask_iv: str
    bid_iv: str
    delta: str
    discount_factor: str
    forward_price: str
    gamma: str
    iv: str
    mark_price: str
    rho: str
    theta: str
    vega: str


class OptionSettlementPricesResult(Struct):
    expiries: list[ExpirySettlementPrice]


class OptionSettlementResponse(Struct):
    amount: str
    expiry: int
    instrument_name: str
    settlement_price: str
    settlement_value: str
    subaccount_id: int


class OracleSignatureDataResponse(Struct):
    signatures: list[str]
    signers: list[Address]


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
    recovered_signer: str | None | UnsetType = UNSET


class OrderStatus(StrEnum):
    open = 'open'
    filled = 'filled'
    rejected = 'rejected'
    cancelled = 'cancelled'
    expired = 'expired'
    untriggered = 'untriggered'
    algo_active = 'algo_active'


class OrderType(StrEnum):
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
    credit_nonce: str | None | UnsetType = UNSET


class PerformanceResolution(StrEnum):
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
    tx_hash: str | None | UnsetType = UNSET


class PerpSettlementHistoryResponse(Struct):
    events: list[PerpSettlementEventResponse]
    pagination: Pagination


class PollQuotesRequest(GetQuotesRequest):
    pass


class PollRfqsRequest(Struct):
    subaccount_id: int
    from_timestamp: int | UnsetType = 0
    page: int | UnsetType = 1
    page_size: int | UnsetType = 20
    rfq_id: str | UnsetType = UNSET
    rfq_subaccount_id: int | UnsetType = UNSET
    status: str | UnsetType = UNSET
    to_timestamp: int | UnsetType = 9223372036854776000


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
    instrument_type: AssetType
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
    leverage: str | None | UnsetType = UNSET
    liquidation_price: str | None | UnsetType = UNSET


class PricedLegParamsAndResponse(Struct):
    amount: Decimal
    direction: Direction
    instrument_name: str
    price: Decimal


class PrivateChangeSubaccountLabelResponse(ChangeSubaccountLabelRequest):
    pass


class PrivateGetAccountResponse(Struct):
    cancel_on_disconnect: bool
    fallback_subaccount_id: int
    fee_info: AccountFeeInfo
    is_rfq_maker: bool
    per_endpoint_tps: dict[str, int]
    subaccount_ids: list[int]
    wallet: str
    websocket_matching_tps: int
    websocket_non_matching_tps: int
    websocket_option_tps: int
    websocket_perp_tps: int
    whitelisted_recipients: list[str]
    creation_timestamp_sec: int | None | UnsetType = UNSET
    referral_code: str | None | UnsetType = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'


class PrivateGetCollateralsResponse(Struct):
    collaterals: list[Collateral]
    subaccount_id: int


class PrivateGetPositionsResponse(Struct):
    positions: list[Position]
    subaccount_id: int


class PrivateGetSubaccountsResponse(Struct):
    subaccount_ids: list[int]
    wallet: str


class PrivateLiquidateRequest(Struct):
    cash_transfer: Decimal
    last_seen_trade_id: int
    liquidate_subaccount_id: int
    merge_account: bool
    nonce: int
    percent_of_acc: Decimal
    price_limit: Decimal
    signature: str
    signature_expiry_sec: int
    signer: str
    subaccount_id: int


class PrivateLiquidateResponse(Struct):
    op_uuid: str
    operation_id: int


class PrivateSetSessionKeyResponse(Struct):
    expiry_sec: int
    ip_whitelist: list[str]
    offchain_scopes: list[str]
    protocol_scopes: list[str]
    public_session_key: str
    subaccount_ids: list[int]
    label: str | None | UnsetType = UNSET


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


class PrivateTransferSpotExternalResponse(PrivateLiquidateResponse):
    pass


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


class PrivateTransferSpotResponse(PrivateLiquidateResponse):
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
    recipient: str | UnsetType = UNSET


class PrivateWithdrawResponse(PrivateLiquidateResponse):
    pass


class PublicExecuteQuoteDebugRequest(Struct):
    direction: Direction
    legs: list[PricedLegParamsAndResponse]
    max_fee: Decimal
    nonce: int
    quote_id: str
    rfq_id: str
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int


class PublicGetWalletsFromSessionKeyResponse(Struct):
    wallets: list[str]


class PublicSendQuoteDebugRequest(Struct):
    direction: Direction
    legs: list[PricedLegParamsAndResponse]
    max_fee: Decimal
    nonce: int
    rfq_id: str
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int


class PublicStartAuctionRequest(Struct):
    subaccount_id: int


class PublicStartAuctionResponse(PrivateLiquidateResponse):
    pass


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
    recipient: str | UnsetType = UNSET


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


class RFQCancelReason(StrEnum):
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
    validation_failed = 'validation_failed'


class RFQStatus(StrEnum):
    open = 'open'
    filled = 'filled'
    cancelled = 'cancelled'
    expired = 'expired'


class RPCError(Struct):
    code: int
    message: str
    data: str | None | UnsetType = UNSET


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
    remaining_per_endpoint: dict[str, RateLimitInfo]
    remaining_connections: RateLimitInfo | None | UnsetType = UNSET


class ReferralPerformanceByInstrumentType(Struct):
    builder_fee: str
    fee_reward: str
    notional_volume: str
    referred_fee: str
    unique_traders_referred: int


class Referrer(Struct):
    wallet: str
    referral_code: str = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'
    receiving_wallet: str | None | UnsetType = UNSET


class RegisterDepositAddressParams(Struct):
    deposit_type: DepositType
    wallet: str
    manager_id: int | UnsetType = UNSET
    subaccount_id: int | UnsetType = 0


class RegisterDepositAddressResult(Struct):
    deposit_address: str
    deposit_type: DepositType
    wallet: str
    manager_id: int | None | UnsetType = UNSET
    subaccount_id: int | None | UnsetType = UNSET


class ReplaceQuoteRequest(Struct):
    direction: Direction
    legs: list[PricedLegParamsAndResponse]
    max_fee: Decimal
    nonce: int
    rfq_id: str
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int
    client: str | UnsetType = '8baller-python-sdk'
    extra_fee: Decimal | UnsetType = Decimal('0')
    label: str | UnsetType = ''
    mmp: bool | UnsetType = False
    nonce_to_cancel: int | UnsetType = UNSET
    quote_id_to_cancel: str | UnsetType = UNSET
    referral_code: str | UnsetType = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'


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
    legs: list[LegUnpricedParams]
    partial_fill_step: Decimal
    rfq_id: str
    status: RFQStatus
    subaccount_id: int
    valid_until: int
    wallet: Address
    ask_total_cost: Decimal | None = None
    bid_total_cost: Decimal | None = None
    mark_total_cost: Decimal | None = None
    max_total_cost: Decimal | None = None
    min_total_cost: Decimal | None = None
    total_cost: Decimal | None = None
    counterparties: list[Address] | UnsetType = UNSET
    filled_direction: Direction | None | UnsetType = UNSET


class RfqGetBestQuoteRequest(Struct):
    subaccount_id: int
    client: str | UnsetType = '8baller-python-sdk'
    direction: Direction | UnsetType = Direction('buy')
    extra_fee: Decimal | UnsetType = Decimal('0')
    legs: list[LegUnpricedParams] | UnsetType = field(default_factory=list)
    rfq_id: str | UnsetType = UNSET


class RiskUniverseManager(Struct):
    collaterals: list[ManagerCollateral]
    instruments: list[str]
    manager_id: int
    margin_type: MarginType


class SecurityModuleDetails(Struct):
    cash_asset: str
    cash_currency: str
    subaccount_id: int


class SendQuoteRequest(Struct):
    direction: Direction
    legs: list[PricedLegParamsAndResponse]
    max_fee: Decimal
    nonce: int
    rfq_id: str
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int
    client: str | UnsetType = '8baller-python-sdk'
    extra_fee: Decimal | UnsetType = Decimal('0')
    label: str | UnsetType = ''
    mmp: bool | UnsetType = False
    referral_code: str | UnsetType = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'


class SendRfqRequest(Struct):
    legs: list[LegUnpricedParams]
    subaccount_id: int
    client: str | UnsetType = '8baller-python-sdk'
    counterparties: list[str] | UnsetType = UNSET
    extra_fee: Decimal | UnsetType = Decimal('0')
    label: str | UnsetType = ''
    max_total_cost: Decimal | UnsetType = UNSET
    min_total_cost: Decimal | UnsetType = UNSET
    partial_fill_step: Decimal | UnsetType = Decimal('1')
    referral_code: str | UnsetType = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'


class SessionKey(Struct):
    expiry_sec: int
    ip_whitelist: list[str]
    label: str
    offchain_scopes: list[str]
    protocol_scopes: list[str]
    public_session_key: str
    registered_sec: int
    subaccount_ids: list[int]


class SessionKeysRequest(Struct):
    wallet: str


class SetMmpConfigRequest(Struct):
    currency: str
    mmp_frozen_time: int
    mmp_interval: int
    subaccount_id: int
    mmp_amount_limit: Decimal | UnsetType = Decimal('0')
    mmp_delta_limit: Decimal | UnsetType = Decimal('0')


class SetMmpConfigResponse(Struct):
    currency: str
    mmp_amount_limit: str
    mmp_delta_limit: str
    mmp_frozen_time: int
    mmp_interval: int
    subaccount_id: int


class SetSessionKeyRequest(Struct):
    expiry_sec: int
    nonce: str
    offchain_scopes: list[str]
    protocol_scopes: list[str]
    public_session_key: str
    signature: str
    signature_expiry_sec: int
    signer: str
    wallet: str
    ip_whitelist: list[str] | UnsetType = UNSET
    label: str | UnsetType = UNSET
    subaccount_ids: list[int] | UnsetType = UNSET


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
    quote_id: str | None = None
    rfq_id: str | None = None
    batch_status: BatchStatus | None | UnsetType = UNSET


class SignedTransferQuoteRequest(Struct):
    direction: Direction
    legs: list[PricedLegParamsAndResponse]
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
    feed_source_type: str | None | UnsetType = UNSET


class SpotPublicDetails(Struct):
    borrow_index: str
    decimals: int
    supply_index: str
    underlying_erc20_address: str


class SpotUniverse(Struct):
    oi: OpenInterestStats
    pm2_im_discount: str
    pm2_mm_discount: str
    risk_universe_id: int
    srm_im_discount: str
    srm_mm_discount: str
    lending: LendingDetails | None | UnsetType = UNSET


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
    funding_rate: str | None | UnsetType = UNSET
    option_pricing: OptionPricing | None | UnsetType = UNSET


class TimeInForce(StrEnum):
    gtc = 'gtc'
    post_only = 'post_only'
    fok = 'fok'
    ioc = 'ioc'


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
    quote_id: str | None = None
    rfq_id: str | None = None
    batch_status: BatchStatus | None | UnsetType = UNSET
    label: str | UnsetType = ''
    tx_hash: str | None | UnsetType = UNSET


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
    quote_id: str | None = None
    rfq_id: str | None = None
    batch_status: BatchStatus | None | UnsetType = UNSET
    tx_hash: str | None | UnsetType = UNSET


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
    tx_hash: str | None | UnsetType = UNSET


class TransferHistoryResult(Struct):
    transfers: list[TransferEntry]


class TransferPositionsRequest(Struct):
    maker_params: SignedTransferQuoteRequest
    taker_params: SignedTransferQuoteRequest
    wallet: Address


class TriggerPriceType(StrEnum):
    mark = 'mark'
    index = 'index'  # type: ignore


class TriggerType(StrEnum):
    stoploss = 'stoploss'
    takeprofit = 'takeprofit'


class UniverseManagers(Struct):
    risk_universe_id: int
    pm: int | None | UnsetType = UNSET
    risk_universe_name: str | None | UnsetType = UNSET
    sm: int | None | UnsetType = UNSET


class UpdateVaultInfoRequest(Struct):
    subaccount_id: int
    description: str | UnsetType = UNSET
    mtm_cap: Decimal | UnsetType = UNSET
    name: str | UnsetType = UNSET
    whitelist_only: bool | UnsetType = UNSET


class UpdateWhitelistedRecipientsRequest(Struct):
    add: list[str]
    nonce: int
    remove: list[str]
    signature: str
    signature_expiry_sec: int
    signer: str
    wallet: str


class UpdateWhitelistedRecipientsResponse(Struct):
    op_uuid: str
    operation_id: int
    whitelisted_recipients: list[str]


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
    benchmark_asset: Address | None | UnsetType = UNSET


class VaultCreateResponse(PrivateLiquidateResponse):
    pass


class VaultDepositHold(Struct):
    amount: str
    asset_name: str
    currency: str
    vault_id: int


class VaultForceBurnResponse(PrivateLiquidateResponse):
    pass


class VaultIdsResponse(Struct):
    subaccount_ids: list[int]


class VaultPerformancePointResponse(Struct):
    curator_shares: Decimal
    global_hwm: Decimal
    share_price: Decimal
    total_shares: Decimal
    ts: int
    benchmark_price: Decimal | None = None
    nav: Decimal | None = None
    nav_benchmark: Decimal | None = None


class VaultRequestId(Struct):
    vault_nonce: str
    vault_subaccount_id: int
    wallet: Address


class VaultSettleResponse(PrivateLiquidateResponse):
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
    tx_hash: str | None | UnsetType = UNSET


class WithdrawalHistoryResult(Struct):
    withdrawals: list[WithdrawalEntry]


class Action(Struct):
    data: list[int]
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
    erc20_details: SpotPublicDetails | None | UnsetType = UNSET
    option_details: OptionDetails | None | UnsetType = UNSET
    perp_details: PerpDetails | None | UnsetType = UNSET


class AssetUniverse(Struct):
    oi: OpenInterestStats
    risk_universe_id: int
    risk_universe_name: str | None | UnsetType = UNSET


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
    algo_duration_sec: int | UnsetType = UNSET
    algo_num_slices: int | UnsetType = UNSET
    algo_type: AlgoType | UnsetType = UNSET
    client: str | UnsetType = '8baller-python-sdk'
    extra_fee: Decimal | UnsetType = UNSET
    is_atomic_signing: bool | UnsetType = UNSET
    label: str | UnsetType = UNSET
    mmp: bool | UnsetType = UNSET
    order_type: OrderType | UnsetType = OrderType('limit')
    reduce_only: bool | UnsetType = UNSET
    referral_code: str | UnsetType = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'
    reject_post_only: bool | UnsetType = UNSET
    reject_timestamp: int | UnsetType = UNSET
    time_in_force: TimeInForce | UnsetType = TimeInForce('gtc')
    trigger_price: Decimal | UnsetType = UNSET
    trigger_price_type: TriggerPriceType | UnsetType = UNSET
    trigger_type: TriggerType | UnsetType = UNSET


class ExecuteQuoteRequest(Struct):
    direction: Direction
    legs: list[PricedLegParamsAndResponse]
    max_fee: Decimal
    nonce: int
    quote_id: str
    rfq_id: str
    signature: str
    signature_expiry_sec: int
    signer: Address
    subaccount_id: int
    client: str | UnsetType = '8baller-python-sdk'
    enable_taker_protection: bool | UnsetType = False
    label: str | UnsetType = ''
    referral_code: str | UnsetType = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'


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


class FundingFeedDataResponse(Struct):
    confidence: str
    currency: str
    deadline: int
    funding_rate: str
    signatures: OracleSignatureDataResponse
    timestamp: int


class GetOnchainActionHistoryResponse(Struct):
    actions: list[OnchainActionHistoryEntry]
    pagination: Pagination


class GetPendingDepositsResult(Struct):
    pending_deposits: list[PendingDepositEntry]
    wallet: str


class GetReferralPerformanceResult(Struct):
    fee_share_percentage: str
    rewards: dict[str, dict[str, dict[str, ReferralPerformanceByInstrumentType]]]
    stdrv_balance: str
    total_builder_fee_collected: str
    total_fee_rewards: str
    total_notional_volume: str
    total_referred_fees: str
    referral_code: str = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'


class GetTickersResponse(Struct):
    tickers: dict[str, TickerSlimSnapshot]


class GetVaultPerformanceHistoryRequest(Struct):
    resolution: PerformanceResolution
    subaccount_id: int
    from_: int | UnsetType = field(name='from', default=UNSET)
    limit: int | UnsetType = UNSET
    to: int | UnsetType = UNSET


class GetWalletsFromSessionKeyRequest(Struct):
    public_session_key: str
    scope: OffchainKeyScope | UnsetType = UNSET


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
    erc20_details: SpotPublicDetails | None | UnsetType = UNSET
    mark_price_fee_rate_cap: str | None | UnsetType = UNSET
    option_details: OptionDetails | None | UnsetType = UNSET
    perp_details: PerpDetails | None | UnsetType = UNSET


class InterestHistoryResult(Struct):
    events: list[InterestPayment]


class InterestRateCandle(Struct):
    borrow_apy: Ohlc
    risk_universe_id: int
    supply_apy: Ohlc
    timestamp: int
    total_borrow: str
    total_supply: str


class InterestRateHistoryResult(Struct):
    interest_rate_history: list[InterestRateCandle]


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
    settlements: list[OptionSettlementResponse]


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
    quote_id: str | None = None
    replaced_order_id: str | None = None
    signed_limit_price: Decimal | None = None
    trigger_price: Decimal | None = None
    algo_duration_sec: int | None | UnsetType = UNSET
    algo_num_slices: int | None | UnsetType = UNSET
    algo_slices_completed: int | None | UnsetType = UNSET
    algo_type: AlgoType | None | UnsetType = UNSET
    cancel_reason: CancelReason | UnsetType = CancelReason('')
    label: str | UnsetType = ''
    trigger_price_type: TriggerPriceType | None | UnsetType = UNSET
    trigger_reject_message: str | None | UnsetType = UNSET
    trigger_type: TriggerType | None | UnsetType = UNSET


class OrderCreatedResponse(Struct):
    order: Order
    trades: list[Trade]


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
    client: str | UnsetType = '8baller-python-sdk'
    extra_fee: Decimal | UnsetType = UNSET
    is_atomic_signing: bool | UnsetType = False
    label: str | UnsetType = ''
    mmp: bool | UnsetType = False
    order_type: OrderType | UnsetType = OrderType('limit')
    reduce_only: bool | UnsetType = False
    referral_code: str | UnsetType = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'
    reject_post_only: bool | UnsetType = True
    reject_timestamp: int | UnsetType = 9223372036854776000
    time_in_force: TimeInForce | UnsetType = TimeInForce('gtc')
    trigger_price: Decimal | UnsetType = UNSET
    trigger_price_type: TriggerPriceType | UnsetType = UNSET
    trigger_type: TriggerType | UnsetType = UNSET


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
    invalid_reason: str | None | UnsetType = UNSET
    max_amount: str | None | UnsetType = UNSET
    post_liquidation_price: str | None | UnsetType = UNSET


class PaginatedOrdersResult(Struct):
    orders: list[Order]
    pagination: Pagination
    subaccount_id: int


class PaginatedTradesResult(Struct):
    pagination: Pagination
    subaccount_id: int
    trades: list[TradeHistoryResponse]


class PaginatedVaultActionHistory(Struct):
    events: list[PublicVaultActionResponse]
    pagination: Pagination
    subaccount_id: int


class PaginatedVaultRequestHistory(Struct):
    actions: list[VaultActionResponse]
    pagination: Pagination
    wallet: str


class PrivateSessionKeysResponse(Struct):
    public_session_keys: list[SessionKey]


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
    legs: list[PricedLegParamsAndResponse]
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
    legs: list[LegUnpricedParams]
    partial_fill_step: Decimal
    rfq_id: str
    status: RFQStatus
    subaccount_id: int
    valid_until: int
    wallet: Address
    fill_rate: Decimal | None = None
    recent_fill_rate: Decimal | None = None
    total_cost: Decimal | None = None
    filled_direction: Direction | None | UnsetType = UNSET


class PublicTradesResult(Struct):
    pagination: Pagination
    trades: list[SettledTrade]


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
    legs: list[PricedLegParamsAndResponse]
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
    batch_status: BatchStatus | None | UnsetType = UNSET
    tx_hash: str | None | UnsetType = UNSET


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
    legs: list[PricedLegParamsAndResponse]
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
    quotes: list[Quote]


class QuotePollResponse(Struct):
    pagination: Pagination
    quotes: list[PublicQuote]


class QuoteReplaceResponse(Struct):
    cancelled_quote: Quote
    create_quote_error: RPCError | None | UnsetType = UNSET
    quote: Quote | None | UnsetType = UNSET


class RFQGetResponse(Struct):
    pagination: Pagination
    rfqs: list[Rfq]


class RFQPollResponse(Struct):
    pagination: Pagination
    rfqs: list[PublicRfq]


class RejectDepositRequestRequest(Struct):
    request_id: VaultRequestId
    reason: str | UnsetType = UNSET


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
    algo_duration_sec: int | UnsetType = UNSET
    algo_num_slices: int | UnsetType = UNSET
    algo_type: AlgoType | UnsetType = UNSET
    client: str | UnsetType = '8baller-python-sdk'
    expected_filled_amount: Decimal | UnsetType = UNSET
    extra_fee: Decimal | UnsetType = UNSET
    is_atomic_signing: bool | UnsetType = UNSET
    label: str | UnsetType = UNSET
    mmp: bool | UnsetType = UNSET
    nonce_to_cancel: int | UnsetType = UNSET
    order_id_to_cancel: str | UnsetType = UNSET
    order_type: OrderType | UnsetType = OrderType('limit')
    reduce_only: bool | UnsetType = UNSET
    referral_code: str | UnsetType = '0x9135BA0f495244dc0A5F029b25CDE95157Db89AD'
    reject_post_only: bool | UnsetType = UNSET
    reject_timestamp: int | UnsetType = UNSET
    time_in_force: TimeInForce | UnsetType = TimeInForce('gtc')
    trigger_price: Decimal | UnsetType = UNSET
    trigger_price_type: TriggerPriceType | UnsetType = UNSET
    trigger_type: TriggerType | UnsetType = UNSET


class ReplaceOrderResponse(Struct):
    cancelled_order: Order
    create_order_error: RPCError | None | UnsetType = UNSET
    order: Order | None | UnsetType = UNSET
    trades: list[Trade] | UnsetType = UNSET


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
    invalid_reason: str | None | UnsetType = UNSET


class RiskUniverse(Struct):
    managers: list[RiskUniverseManager]
    risk_universe_id: int
    security_module: SecurityModuleDetails
    description: str | None | UnsetType = UNSET
    name: str | None | UnsetType = UNSET


class SignedAction(Struct):
    action: Action
    signature: list[int]


class SpotAssetEntry(Struct):
    address: str
    erc20: Erc20Details
    min_deposit_usd: str
    name: str
    universes: list[SpotUniverse]


class Subaccount(Struct):
    collaterals: list[Collateral]
    collaterals_initial_margin: str
    collaterals_maintenance_margin: str
    collaterals_value: str
    currency: list[str]
    failed_to_fetch: bool
    initial_margin: str
    is_under_liquidation: bool
    label: str
    maintenance_margin: str
    manager_id: int
    margin_type: str
    open_orders: list[Order]
    open_orders_margin: str
    positions: list[Position]
    positions_initial_margin: str
    positions_maintenance_margin: str
    positions_value: str
    projected_margin_change: str
    risk_universe_id: int
    subaccount_id: int
    subaccount_value: str
    vault_deposit_holds: list[VaultDepositHold]
    mm_credits: str | UnsetType = UNSET


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
    benchmark_price: Decimal | None | UnsetType = UNSET
    mtm_cap: Decimal | None | UnsetType = UNSET
    nav_benchmark: Decimal | None | UnsetType = UNSET
    nav_usd: Decimal | None | UnsetType = UNSET
    simulated_share_price_usd: Decimal | None | UnsetType = UNSET


class VaultCancelResponse(Struct):
    cancelled_request_ids: list[VaultRequestId]
    op_uuid: str
    operation_id: int


class VaultPerformanceHistoryResult(Struct):
    points: list[VaultPerformancePointResponse]
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
    vaults: list[VaultShareEntryResponse]


class VaultsResponse(Struct):
    pagination: Pagination
    vaults: list[Vault]


class VolFeedDataResponse(Struct):
    confidence: str
    currency: str
    deadline: int
    expiry: int
    signatures: OracleSignatureDataResponse
    timestamp: int
    vol_data: VolSVIParamDataResponse


class AggregatedOrdersResult(Struct):
    orders: list[Order]
    subaccount_id: int


class AggregatedTriggerOrdersResult(AggregatedOrdersResult):
    pass


class AssetEntry(Struct):
    address: str
    name: str
    universes: list[AssetUniverse]


class Currency(Struct):
    currency: str
    managers: list[UniverseManagers]
    market_type: MarketType
    spot: list[SpotAssetEntry]
    spot_price: str
    option: AssetEntry | None | UnsetType = UNSET
    perp: AssetEntry | None | UnsetType = UNSET
    spot_price_24h: str | None | UnsetType = UNSET


class GetAllInstrumentsResponse(Struct):
    instruments: list[Instrument]
    pagination: Pagination


class GetLatestSignedFeedsResponse(Struct):
    funding_data: dict[str, FundingFeedDataResponse]
    fwd_data: dict[str, dict[str, ForwardFeedDataResponse]]
    perp_data: dict[str, dict[str, PerpFeedDataResponse]]
    rate_data: dict[str, dict[str, RateFeedDataResponse]]
    spot_data: dict[str, SpotFeedDataResponse]
    vol_data: dict[str, dict[str, VolFeedDataResponse]]


class MultipleVaultRequestsResponse(Struct):
    requests: list[VaultRequestResponse]
    total: int
