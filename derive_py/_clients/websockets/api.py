"""Auto-generated API classes for WebSocket"""

from enum import Enum
from typing import Awaitable, Callable, Literal, TypeVar

from derive_py._clients.utils import SubscriptionResult, decode_result
from derive_py._clients.websockets.session import WebSocketSession
from derive_py.data_types.channel_models import (
    AuctionResult,
    BalanceUpdate,
    BestQuoteChannelResult,
    LoginRequest,
    MarginWatchResult,
    OrderbookSnapshot,
    PublicTrade,
    QuotePublishResult,
    SetCancelOnDisconnectRequest,
    SpotFeedPayload,
    TickerSlimPayload,
)
from derive_py.data_types.generated_models import (
    AggregatedOrdersResult,
    AggregatedTriggerOrdersResult,
    Asset,
    AssetType,
    BurnSharesRequest,
    CancelAlgoOrderRequest,
    CancelAllAlgoOrdersRequest,
    CancelAllRequest,
    CancelAllTriggerOrdersRequest,
    CancelBatchQuotesRequest,
    CancelBatchResult,
    CancelBatchRfqsRequest,
    CancelBatchRfqsResponse,
    CancelByInstrumentRequest,
    CancelByInstrumentResponse,
    CancelByLabelRequest,
    CancelByLabelResponse,
    CancelByNonceRequest,
    CancelByNonceResponse,
    CancelOrderRequest,
    CancelQuoteRequest,
    CancelRfqRequest,
    CancelTriggerOrderRequest,
    CancelVaultRequestRequest,
    ChangeSubaccountLabelRequest,
    CreateOrderRequest,
    CreateVaultRequest,
    Currency,
    DepositHistoryResult,
    EditSessionKeyRequest,
    EmptyRequest,
    ExecuteQuoteRequest,
    ForceBurnRequest,
    FundingRateHistoryResult,
    GetAccountRequest,
    GetAlgoOrdersRequest,
    GetAllInstrumentsRequest,
    GetAllInstrumentsResponse,
    GetAllPortfoliosRequest,
    GetAllReferralCodesParams,
    GetAssetsRequest,
    GetCollateralsRequest,
    GetCuratedVaultsRequest,
    GetCurrencyRequest,
    GetDepositHistoryRequest,
    GetErc20TransferHistoryRequest,
    GetFundingHistoryRequest,
    GetFundingRateHistoryRequest,
    GetIndexChartDataRequest,
    GetInstrumentRequest,
    GetInterestHistoryRequest,
    GetInterestRateHistoryRequest,
    GetLatestSignedFeedsRequest,
    GetLatestSignedFeedsResponse,
    GetLiquidationHistoryRequest,
    GetLiveBurnRequestsRequest,
    GetLiveMintRequestsRequest,
    GetLiveVaultRequestsRequest,
    GetOnchainActionHistoryParams,
    GetOnchainActionHistoryResponse,
    GetOpenOrdersRequest,
    GetOptionSettlementHistoryParams,
    GetOptionSettlementPricesRequest,
    GetOrderHistoryRequest,
    GetOrderRequest,
    GetPendingDepositsParams,
    GetPendingDepositsResult,
    GetPositionsRequest,
    GetPublicTradeHistoryRequest,
    GetQuotesRequest,
    GetReferralPerformanceParams,
    GetReferralPerformanceResult,
    GetRfqsRequest,
    GetShareholderVaultsRequest,
    GetSubaccountRequest,
    GetSubaccountsRequest,
    GetTickerRequest,
    GetTickersRequest,
    GetTickersResponse,
    GetTradeHistoryRequest,
    GetTradingviewChartDataRequest,
    GetTransactionParams,
    GetTransactionResult,
    GetTriggerOrdersRequest,
    GetVaultActionHistoryRequest,
    GetVaultPerformanceHistoryRequest,
    GetVaultRequest,
    GetVaultRequestHistoryRequest,
    GetVaultSharesRequest,
    GetVaultsRequest,
    GetWalletsFromSessionKeyRequest,
    GetWithdrawalHistoryRequest,
    IndexCandle,
    Instrument,
    InterestHistoryResult,
    InterestRateHistoryResult,
    LiquidationHistoryResult,
    MintSharesRequest,
    MmpConfigResult,
    MmpScopeRequest,
    MultipleVaultRequestsResponse,
    OffchainAckResponse,
    OptionSettlementHistoryResponse,
    OptionSettlementPricesResult,
    Order,
    OrderCreatedResponse,
    OrderDebugResponse,
    OrderQuoteRequest,
    OrderQuoteResponse,
    PaginatedOrdersResult,
    PaginatedTradesResult,
    PaginatedVaultActionHistory,
    PaginatedVaultRequestHistory,
    PerpSettlementHistoryResponse,
    PollQuotesRequest,
    PollRfqsRequest,
    PrivateChangeSubaccountLabelResponse,
    PrivateGetAccountResponse,
    PrivateGetCollateralsResponse,
    PrivateGetPositionsResponse,
    PrivateGetSubaccountsResponse,
    PrivateLiquidateRequest,
    PrivateLiquidateResponse,
    PrivateSessionKeysResponse,
    PrivateSetSessionKeyResponse,
    PrivateTransferSpotExternalRequest,
    PrivateTransferSpotExternalResponse,
    PrivateTransferSpotRequest,
    PrivateTransferSpotResponse,
    PrivateWithdrawRequest,
    PrivateWithdrawResponse,
    PublicExecuteQuoteDebugRequest,
    PublicGetWalletsFromSessionKeyResponse,
    PublicRfq,
    PublicSendQuoteDebugRequest,
    PublicStartAuctionRequest,
    PublicStartAuctionResponse,
    PublicTradesResult,
    PublicWithdrawDebugRequest,
    Quote,
    QuoteExecuteDebugResult,
    QuoteExecuteResponse,
    QuoteGetResponse,
    QuotePollResponse,
    QuoteReplaceResponse,
    QuoteSendDebugResult,
    RateLimitResult,
    Referrer,
    RegisterDepositAddressParams,
    RegisterDepositAddressResult,
    RejectDepositRequestRequest,
    ReplaceOrderRequest,
    ReplaceOrderResponse,
    ReplaceQuoteRequest,
    RequestVaultDepositRequest,
    RequestVaultWithdrawRequest,
    Rfq,
    RfqGetBestQuoteRequest,
    RfqGetBestQuoteResponse,
    RFQGetResponse,
    RFQPollResponse,
    RiskUniverse,
    SendQuoteRequest,
    SendRfqRequest,
    SessionKey,
    SessionKeysRequest,
    SetMmpConfigRequest,
    SetMmpConfigResponse,
    SetSessionKeyRequest,
    SettledTrade,
    Subaccount,
    TickerSlimSnapshot,
    Trade,
    TradingviewCandle,
    TransferHistoryResult,
    TransferPositionsRequest,
    TransferPositionsResponse,
    UpdateVaultInfoRequest,
    UpdateWhitelistedRecipientsRequest,
    UpdateWhitelistedRecipientsResponse,
    Vault,
    VaultCancelResponse,
    VaultCreateResponse,
    VaultForceBurnResponse,
    VaultIdsResponse,
    VaultPerformanceHistoryResult,
    VaultRequestAckResponse,
    VaultSettleResponse,
    VaultSharesResponse,
    VaultsResponse,
    WithdrawalHistoryResult,
)

MessageT = TypeVar('MessageT')
Handler = Callable[[MessageT], None] | Callable[[MessageT], Awaitable[None]]


# ============================================================================
# RPC API Classes
# ============================================================================


class PublicRPC:
    """public RPC methods"""

    def __init__(self, session: WebSocketSession):
        self._session = session

    async def get_wallets_from_session_key(
        self,
        params: GetWalletsFromSessionKeyRequest,
    ) -> PublicGetWalletsFromSessionKeyResponse:
        """
        Public lookup that returns the wallet addresses a given session key is
        registered to, sorted by expiry, with expired keys omitted. An optional scope
        filter narrows results to keys holding that off-chain scope; returns an error if
        no matching, unexpired keys exist.
        """

        method = "public/get_wallets_from_session_key"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PublicGetWalletsFromSessionKeyResponse)

        return result

    async def order_quote(
        self,
        params: OrderQuoteRequest,
    ) -> OrderQuoteResponse:
        """
        Public dry-run variant of order_quote that estimates fill price, fees, margin
        impact, projected order status and realized PnL for a prospective order without
        placing it, returning all values as decimal strings. Unlike private/order_quote
        it bypasses session scope checks, so it can be used to preview costs without
        account authentication.
        """

        method = "public/order_quote"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, OrderQuoteResponse)

        return result

    async def execute_quote_debug(
        self,
        params: PublicExecuteQuoteDebugRequest,
    ) -> QuoteExecuteDebugResult:
        """
        Public signing-preview helper that returns the taker's EIP-712 encoding
        artifacts (encoded data and hashes) plus the maker-side encoded legs and legs
        hash for a quote execution a client is about to sign. It does not verify
        signatures, persist anything, or execute the trade; use it to construct and
        check the exact payload before calling private/execute_quote.
        """

        method = "public/execute_quote_debug"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, QuoteExecuteDebugResult)

        return result

    async def send_quote_debug(
        self,
        params: PublicSendQuoteDebugRequest,
    ) -> QuoteSendDebugResult:
        """
        Public signing-preview helper that returns the EIP-712 encoding artifacts
        (encoded data, its hash, the action hash, and the typed-data hash) for a maker
        quote a client is about to sign. It does not verify signatures, persist
        anything, or place a quote; use it to construct and check the exact payload to
        sign before calling private/send_quote.
        """

        method = "public/send_quote_debug"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, QuoteSendDebugResult)

        return result

    async def get_vault(
        self,
        params: GetVaultRequest,
    ) -> Vault:
        """
        Returns the full vault record — on-chain state plus curator metadata — for one
        vault subaccount id. Unauthenticated and read-only.
        """

        method = "public/get_vault"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, Vault)

        return result

    async def get_vault_action_history(
        self,
        params: GetVaultActionHistoryRequest,
    ) -> PaginatedVaultActionHistory:
        """
        Returns a vault's finalized deposit, withdrawal, fee-accrual, and cancel events
        — including NAV, share price, high-water mark, and the fee-share split across
        management, performance, curator, and protocol — at the vault level (per-holder
        position details are omitted). Inputs are the vault subaccount, an optional
        event_type filter, and pagination. Amounts and prices are decimal strings.
        Unauthenticated.
        """

        method = "public/get_vault_action_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PaginatedVaultActionHistory)

        return result

    async def get_vault_performance_history(
        self,
        params: GetVaultPerformanceHistoryRequest,
    ) -> VaultPerformanceHistoryResult:
        """
        Returns a time series of a vault's mark-to-market performance (NAV, share price,
        total and curator shares, high-water mark, optional benchmark) sampled hourly
        and downsampled to the requested resolution (1h, 8h, 24h, or 1wk). Supports
        optional from/to unix-second bounds and a limit (newest first, default 1000,
        capped at 10000). Values are decimal strings, with live prices nullable.
        Unauthenticated.
        """

        method = "public/get_vault_performance_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, VaultPerformanceHistoryResult)

        return result

    async def get_vaults(
        self,
        params: GetVaultsRequest,
    ) -> VaultsResponse:
        """
        Returns every vault in the system, each paired with its subaccount id, paginated
        by page and page_size. Unauthenticated and read-only.
        """

        method = "public/get_vaults"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, VaultsResponse)

        return result

    async def get_liquidation_history(
        self,
        params: GetLiquidationHistoryRequest,
    ) -> LiquidationHistoryResult:
        """
        Returns a paginated history of liquidation auctions, newest first, for a single
        subaccount or across all of them, optionally bounded by a start/end timestamp
        window over the auction start. Each entry gives the auctioned subaccount,
        whether the auction was solvent or insolvent, the fee charged at start, the
        start and end timestamps, and the bids that filled it with the fraction of the
        account each absorbed and the cash it moved.
        """

        method = "public/get_liquidation_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, LiquidationHistoryResult)

        return result

    async def withdraw_debug(
        self,
        params: PublicWithdrawDebugRequest,
    ) -> dict:
        """
        Dry-run helper that returns the EIP-712 typed data and hashes that would be
        computed for the given withdrawal parameters, so clients can verify their own
        signing and hashing before submitting. Takes the same inputs as private/withdraw
        (subaccount, signer, nonce, amount, max fee, expiry, asset) but performs no
        state change and needs no signature.
        """

        method = "public/withdraw_debug"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, dict)

        return result

    async def get_onchain_action_history(
        self,
        params: GetOnchainActionHistoryParams,
    ) -> GetOnchainActionHistoryResponse:
        """
        Returns the lifecycle of onchain actions submitted via
        `OnchainActionManager.sol`. Public endpoint.

        Onchain actions are either applied directly or with a `fallback` flag. Each
        onchain action is affected by the `fallback` flag uniquely:

        - Deposits: sequencer moved the deposit into the `fallback_subaccount`

        - SetSessionKey: no-op

        - Admin actions: no-op

        The onchain action can have several states:

        - `applied`: action was successfully applied by the sequencer

        - `applied_with_fallback`: action was applied by the sequencer with
        fallback=true

        - `instant_fallback`: action failed its initial attempt, will be re-submitted
        with fallback=true

        - `retry_then_fallback`: action failed its initial attempt, will be re-submitted
        with fallback=false until the retry budget is exceeded, then re-submitted with
        fallback=true

        - `never_escalate`: action failed its initial attempt but will retry until
        successful, never with fallback=true
        """

        method = "public/get_onchain_action_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, GetOnchainActionHistoryResponse)

        return result

    async def get_pending_deposits(
        self,
        params: GetPendingDepositsParams,
    ) -> GetPendingDepositsResult:
        """
        Returns deposits queued on L1 but not yet applied by the sequencer, indexed for
        a wallet and keyed by (tx_hash, log_index). Once a deposit is applied it moves
        to private/get_deposit_history; this endpoint covers the window in between.
        Public because a first-time depositor has no account (and thus no session key)
        until their deposit is applied.
        """

        method = "public/get_pending_deposits"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, GetPendingDepositsResult)

        return result

    async def register_deposit_address(
        self,
        params: RegisterDepositAddressParams,
    ) -> RegisterDepositAddressResult:
        """
        Returns the deterministic on-chain deposit address for a wallet and records it
        so incoming deposits are watched and credited. Pass the wallet and optionally an
        existing subaccount id; when creating a new subaccount (subaccount omitted or 0)
        a non-zero manager_id is required. Repeated calls return the same cached address
        and keep it alive, while new registrations are rate limited per rolling window;
        unused addresses are dropped after 7 days.
        """

        method = "public/register_deposit_address"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, RegisterDepositAddressResult)

        return result

    async def getRateLimits(
        self,
        params: EmptyRequest,
    ) -> RateLimitResult:
        """
        Returns the caller's current remaining rate-limit allowances for the active
        connection, broken out into matching-request, non-matching-request, and per-
        endpoint buckets. On WebSocket connections it also includes the remaining
        connection allowance.
        """

        method = "public/getRateLimits"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, RateLimitResult)

        return result

    async def get_time(
        self,
        params: EmptyRequest,
    ) -> int:
        """
        Returns the current server time in milliseconds since the UNIX epoch. Takes no
        parameters and requires no authentication. Use it to align the timestamps and
        nonces bound into signed actions with the server clock.
        """

        method = "public/get_time"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, int)

        return result

    async def get_transaction(
        self,
        params: GetTransactionParams,
    ) -> GetTransactionResult:
        """
        Looks up the settlement lifecycle of a previously submitted operation by its
        operation UUID (op_uuid). Returns the operation's serialized data along with its
        batch status, settlement transaction hash, and any error log; the status is null
        until the operation has been picked up for settlement.
        """

        method = "public/get_transaction"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, GetTransactionResult)

        return result

    async def get_all_currencies(
        self,
        params: EmptyRequest,
    ) -> list[Currency]:
        """
        Returns detailed metadata for every configured currency, including supported
        instrument types, risk managers, spot price and 24h-ago price, SRM/portfolio
        margin collateral discounts, lending borrow/supply APYs, open-interest caps and
        utilization per manager, and protocol asset addresses. Currencies that exist but
        have no configured assets are omitted. Public endpoint, no authentication
        required.
        """

        method = "public/get_all_currencies"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, list[Currency])

        return result

    async def get_all_instruments(
        self,
        params: GetAllInstrumentsRequest,
    ) -> GetAllInstrumentsResponse:
        """
        Returns a paginated list of full instrument definitions filtered by
        `instrument_type`, optional `currency`, and `expired` flag, with
        `page`/`page_size` (max 1000) controls and pagination metadata. Expired options
        are included when the `expired` flag is set. Public endpoint.
        """

        method = "public/get_all_instruments"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, GetAllInstrumentsResponse)

        return result

    async def get_all_live_instruments(
        self,
        params: EmptyRequest,
    ) -> list[str]:
        """
        Returns a sorted list of the names of every currently live instrument (active
        and within its scheduled activation window). Takes no parameters and returns
        names only, not full definitions. Public endpoint.
        """

        method = "public/get_all_live_instruments"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, list[str])

        return result

    async def get_assets(
        self,
        params: GetAssetsRequest,
    ) -> list[Asset]:
        """
        Returns the assets of a given `asset_type` (option, perp, or erc20) for a
        `currency`, with `expired` controlling whether past-expiry options are included.
        Each entry includes the asset id, name, on-chain address and sub_id,
        collateral/position flags, and type-specific details (option
        strike/expiry/settlement price, perp funding config, or ERC20 lending indices).
        Public endpoint.
        """

        method = "public/get_assets"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, list[Asset])

        return result

    async def get_currency(
        self,
        params: GetCurrencyRequest,
    ) -> Currency:
        """
        Returns the full detail record for one currency named by the required `currency`
        parameter: supported instrument types, risk managers, current and 24h spot
        price, margin collateral discounts, lending APYs and totals, per-manager open-
        interest caps and current OI, and protocol asset addresses. Returns a not-found
        error for unknown currencies. Public endpoint.
        """

        method = "public/get_currency"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, Currency)

        return result

    async def get_funding_rate_history(
        self,
        params: GetFundingRateHistoryRequest,
    ) -> FundingRateHistoryResult:
        """
        Returns funding-rate OHLC candles for a perpetual instrument (`instrument_name`)
        over an optional `start_timestamp`/`end_timestamp` window (UTC milliseconds) at
        a `period` granularity (defaults to 1h; 60s up to 1w supported). Each candle
        carries open/high/low/close per-hour rates plus a `funding_rate` mirroring the
        close. Public endpoint.
        """

        method = "public/get_funding_rate_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, FundingRateHistoryResult)

        return result

    async def get_index_chart_data(
        self,
        params: GetIndexChartDataRequest,
    ) -> list[IndexCandle]:
        """
        Returns spot index OHLC candles for a `currency` between required
        `start_timestamp` and `end_timestamp` (UTC seconds) at the given `period`
        granularity (1m up to 1w). Each candle includes open/high/low/close and a
        `price` mirroring the close. The requested range is clamped to a maximum number
        of buckets. Public endpoint.
        """

        method = "public/get_index_chart_data"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, list[IndexCandle])

        return result

    async def get_instrument(
        self,
        params: GetInstrumentRequest,
    ) -> Instrument:
        """
        Returns the full public definition of one instrument named by `instrument_name`:
        type, activation window and active status, tick size, min/max/step amounts,
        maker/taker/base fee rates, pro-rata matching parameters, base/quote currencies,
        and type-specific details (option, perp, or spot). Expired options remain
        queryable by `instrument_name`. Public endpoint.
        """

        method = "public/get_instrument"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, Instrument)

        return result

    async def get_interest_rate_history(
        self,
        params: GetInterestRateHistoryRequest,
    ) -> InterestRateHistoryResult:
        """
        Returns lending borrow/supply APY OHLC candles for a `currency`'s pool over an
        optional time window (UTC milliseconds) at a `period` of 1h or larger (defaults
        to 1h; sub-hour periods are rejected). An optional `risk_universe_id` restricts
        to one pool; otherwise every universe's candles are returned, each tagged and
        carrying pool total supply/borrow. Public endpoint.
        """

        method = "public/get_interest_rate_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, InterestRateHistoryResult)

        return result

    async def get_latest_signed_feeds(
        self,
        params: GetLatestSignedFeedsRequest,
    ) -> GetLatestSignedFeedsResponse:
        """
        Returns the most recent oracle-signed feed data — spot, forward, volatility
        (SVI), rate, perp, and perpetual funding-rate feeds — each with signer addresses
        and signatures for on-chain submission. Optional `currency` and `expiry` filters
        narrow the result (use `expiry` 0 for the non-expiry feeds: spot, perp and
        funding); both default to all. Public endpoint.
        """

        method = "public/get_latest_signed_feeds"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, GetLatestSignedFeedsResponse)

        return result

    async def get_option_settlement_prices(
        self,
        params: GetOptionSettlementPricesRequest,
    ) -> OptionSettlementPricesResult:
        """
        Returns the settlement price for each settled option expiry of a `currency`,
        with the expiry date (YYYYMMDD), unix expiry timestamp, and price. Only already-
        settled expiries are returned. Unknown currencies return a not-found error.
        Public endpoint.
        """

        method = "public/get_option_settlement_prices"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, OptionSettlementPricesResult)

        return result

    async def get_risk_universes(
        self,
        params: EmptyRequest,
    ) -> list[RiskUniverse]:
        """
        Returns every risk universe (the isolated risk-containment boundaries trades
        never cross), each with its display name and description, its managers — at most
        one Standard (`SM`) and one Portfolio (`PM2`), each listing the derivative
        instruments it risk-prices and the collateral assets it accepts with their
        margin discounts and deposit metadata — and its Security Module. The one call
        that answers which universe and manager to choose: pick a universe, pick a
        manager in it, and pass its `manager_id` when depositing to a new subaccount
        (the accepted collateral entries carry the `asset` address for the deposit). The
        no-margin fallback universe (id 0) is included; it custodies dead-lettered
        deposits and lists no tradeable instruments. Public endpoint, no authentication
        required.
        """

        method = "public/get_risk_universes"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, list[RiskUniverse])

        return result

    async def get_ticker(
        self,
        params: GetTickerRequest,
    ) -> TickerSlimSnapshot:
        """
        Returns the latest ticker snapshot for a single instrument named by
        `instrument_name`. The payload matches the data of a
        `ticker_slim.{instrument}.{interval}` subscription update (mark/index prices,
        best bid/ask, sizes, greeks, and related fields). Returns an error if no ticker
        is available. Public endpoint.
        """

        method = "public/get_ticker"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, TickerSlimSnapshot)

        return result

    async def get_tickers(
        self,
        params: GetTickersRequest,
    ) -> GetTickersResponse:
        """
        Returns a map of instrument name to latest ticker snapshot for an
        `instrument_type`. Options require both `currency` and an 8-digit `expiry_date`
        (YYYYMMDD); perps and spot accept an optional `currency` (omit to fetch all
        currencies) and reject `expiry_date`. Public endpoint.
        """

        method = "public/get_tickers"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, GetTickersResponse)

        return result

    async def get_trade_history(
        self,
        params: GetPublicTradeHistoryRequest,
    ) -> PublicTradesResult:
        """
        Returns paginated, anonymized settled trades with optional filters: `trade_id`
        (a UUID, which overrides all other filters), `instrument_name`,
        `instrument_type` (erc20/option/perp), `currency`, `subaccount_id`,
        `batch_status` (a batch-status name, default Settled), and
        `from_timestamp`/`to_timestamp`. Each trade is enriched with its settlement
        status and transaction hash. Public endpoint.
        """

        method = "public/get_trade_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PublicTradesResult)

        return result

    async def get_tradingview_chart_data(
        self,
        params: GetTradingviewChartDataRequest,
    ) -> list[TradingviewCandle]:
        """
        Returns traded-price OHLCV candles for an `instrument_name` between required
        `start_timestamp` and `end_timestamp` (UTC seconds) at the given `period` (1m up
        to 1w), aggregated from executed trade history. Each candle includes
        open/high/low/close prices plus USD and contract volume, formatted for charting.
        Public endpoint.
        """

        method = "public/get_tradingview_chart_data"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, list[TradingviewCandle])

        return result

    async def get_all_referral_codes(
        self,
        params: GetAllReferralCodesParams,
    ) -> list[Referrer]:
        """
        Returns every registered referral code along with the owner's wallet address
        and, when configured, the wallet that receives referral rewards. Takes no
        parameters.
        """

        method = "public/get_all_referral_codes"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, list[Referrer])

        return result

    async def get_referral_performance(
        self,
        params: GetReferralPerformanceParams,
    ) -> GetReferralPerformanceResult:
        """
        Returns broker-program referral performance for a referral code, identified
        either by the code itself or by the referrer's wallet, over a requested time
        window (start_ms to end_ms, capped at 28 days). The response includes total
        notional volume, referred fees, fee rewards, builder fees collected, the
        applicable fee-share percentage, and a per-role/currency/instrument-type
        breakdown, all as decimal strings.
        """

        method = "public/get_referral_performance"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, GetReferralPerformanceResult)

        return result

    async def start_auction(
        self,
        params: PublicStartAuctionRequest,
    ) -> PublicStartAuctionResponse:
        """
        public/start_auction
        """

        method = "public/start_auction"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PublicStartAuctionResponse)

        return result

    async def login(
        self,
        params: LoginRequest,
    ) -> list[int]:
        """
        WebSocket-only method that authenticates the connection so subsequent private/*
        calls and private channel subscriptions act on your wallet without per-request
        headers. Pass the wallet address, a millisecond UTC timestamp, and an EIP-191
        signature of that timestamp made by either the wallet itself or one of its
        registered session keys. Returns the subaccount ids the authenticated key can
        access.
        """

        method = "public/login"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, list[int])

        return result


class PrivateRPC:
    """private RPC methods"""

    def __init__(self, session: WebSocketSession):
        self._session = session

    async def change_subaccount_label(
        self,
        params: ChangeSubaccountLabelRequest,
    ) -> PrivateChangeSubaccountLabelResponse:
        """
        Updates the human-readable label for a subaccount. The label must be at most 16
        characters, otherwise an invalid-params error is returned. Requires a signed
        session key with account-info scope; on success it echoes back the subaccount ID
        and the new label.
        """

        method = "private/change_subaccount_label"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PrivateChangeSubaccountLabelResponse)

        return result

    async def get_all_portfolios(
        self,
        params: GetAllPortfoliosRequest,
    ) -> list[Subaccount]:
        """
        Returns the complete portfolio (same shape as get_subaccount) for every
        subaccount owned by the given wallet, including valuations, margin figures, open
        orders, positions, and collaterals. If an individual subaccount's portfolio
        cannot be built, it is returned as a placeholder entry with failed_to_fetch set
        to true rather than failing the whole request.
        """

        method = "private/get_all_portfolios"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, list[Subaccount])

        return result

    async def get_collaterals(
        self,
        params: GetCollateralsRequest,
    ) -> PrivateGetCollateralsResponse:
        """
        Returns the subaccount ID and the list of its collateral balances, including
        each asset's amount and current value valued against live feed data. A lighter
        alternative to get_subaccount when only collateral holdings are needed.
        """

        method = "private/get_collaterals"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PrivateGetCollateralsResponse)

        return result

    async def get_positions(
        self,
        params: GetPositionsRequest,
    ) -> PrivateGetPositionsResponse:
        """
        Returns the subaccount ID and the list of its active positions, including size,
        mark price, average price, unrealized and realized PnL, and Greeks where
        applicable, valued against live feed data at request time. A lighter alternative
        to get_subaccount when only positions are needed.
        """

        method = "private/get_positions"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PrivateGetPositionsResponse)

        return result

    async def get_subaccount(
        self,
        params: GetSubaccountRequest,
    ) -> Subaccount:
        """
        Returns the complete portfolio for a single subaccount: its label, manager and
        risk-universe identifiers, margin type and liquidation status, aggregate
        valuation and margin figures (positions, collaterals, initial and maintenance
        margin, open-order margin) as decimal strings, plus the full lists of open
        orders, positions, and collateral balances. Margin, mark price, and Greek values
        are computed from live feed data at request time.
        """

        method = "private/get_subaccount"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, Subaccount)

        return result

    async def get_subaccounts(
        self,
        params: GetSubaccountsRequest,
    ) -> PrivateGetSubaccountsResponse:
        """
        Returns the wallet address and the sorted list of subaccount IDs owned by that
        wallet. Yields an empty list if the wallet has no subaccounts.
        """

        method = "private/get_subaccounts"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PrivateGetSubaccountsResponse)

        return result

    async def edit_session_key(
        self,
        params: EditSessionKeyRequest,
    ) -> SessionKey:
        """
        Updates an existing session key's label, IP allowlist, and/or off-chain scopes
        for a given wallet; it cannot change on-chain (protocol) scopes, for which you
        must re-register with private/set_session_key. Editing only the label needs
        account-info permission, while changing the IP allowlist or off-chain scopes
        requires admin/owner authorization. Returns the updated session key details.
        """

        method = "private/edit_session_key"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, SessionKey)

        return result

    async def session_keys(
        self,
        params: SessionKeysRequest,
    ) -> PrivateSessionKeysResponse:
        """
        Returns every session key registered to the given wallet, including expired and
        not-yet-activated keys, each with its public address, scopes, expiry, label, IP
        allowlist, and permitted subaccounts.
        """

        method = "private/session_keys"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PrivateSessionKeysResponse)

        return result

    async def get_account(
        self,
        params: GetAccountRequest,
    ) -> PrivateGetAccountResponse:
        """
        Returns account-level information for a given wallet address: the list of its
        subaccount IDs, WebSocket rate limits (matching, non-matching, perp, and option
        messages per second) and any per-endpoint overrides, cancel-on-disconnect and
        RFQ-maker flags, the account creation timestamp, and a fee_info block with fee
        discounts and per-instrument maker/taker fee overrides expressed as decimals.
        Returns an account-not-found error if the wallet has never been registered.
        """

        method = "private/get_account"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PrivateGetAccountResponse)

        return result

    async def cancel(
        self,
        params: CancelOrderRequest,
    ) -> Order:
        """
        Cancels one resting order identified by order_id, subaccount_id and
        instrument_name. Requires any trade scope on the session; returns the cancelled
        order with its final status.
        """

        method = "private/cancel"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, Order)

        return result

    async def cancel_algo_order(
        self,
        params: CancelAlgoOrderRequest,
    ) -> Order:
        """
        Cancels a single active algo order identified by order_id and subaccount_id,
        stopping any further child-order execution. Requires any trade scope; returns
        the cancelled order.
        """

        method = "private/cancel_algo_order"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, Order)

        return result

    async def cancel_all(
        self,
        params: CancelAllRequest,
    ) -> str:
        """
        Cancels every open order on the given subaccount. Optional cancel_trigger_orders
        and cancel_algo_orders flags additionally clear the subaccount's trigger and
        algo orders in the same call. Requires any trade scope; returns "ok" on success.
        """

        method = "private/cancel_all"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, str)

        return result

    async def cancel_all_algo_orders(
        self,
        params: CancelAllAlgoOrdersRequest,
    ) -> str:
        """
        Cancels every active algo order on the given subaccount. Requires any trade
        scope; returns "ok" on success.
        """

        method = "private/cancel_all_algo_orders"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, str)

        return result

    async def cancel_all_trigger_orders(
        self,
        params: CancelAllTriggerOrdersRequest,
    ) -> str:
        """
        Cancels every pending trigger order on the given subaccount. Requires any trade
        scope; returns "ok" on success.
        """

        method = "private/cancel_all_trigger_orders"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, str)

        return result

    async def cancel_by_instrument(
        self,
        params: CancelByInstrumentRequest,
    ) -> CancelByInstrumentResponse:
        """
        Cancels every open order for a subaccount on a single instrument. Requires any
        trade scope; returns the number of orders cancelled.
        """

        method = "private/cancel_by_instrument"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, CancelByInstrumentResponse)

        return result

    async def cancel_by_label(
        self,
        params: CancelByLabelRequest,
    ) -> CancelByLabelResponse:
        """
        Cancels a subaccount's open orders that carry the given client label, optionally
        scoped to a single instrument_name. When an instrument is supplied the call is
        acknowledged with the number of orders cancelled; without one it runs as a bulk
        fire-and-forget cancel and returns a -1 sentinel count. Requires any trade
        scope.
        """

        method = "private/cancel_by_label"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, CancelByLabelResponse)

        return result

    async def cancel_by_nonce(
        self,
        params: CancelByNonceRequest,
    ) -> CancelByNonceResponse:
        """
        Cancels a single order identified by its signing nonce, instrument_name and
        subaccount_id. The owning wallet is taken from the authenticated session rather
        than the request. Requires any trade scope; returns the cancelled order.
        """

        method = "private/cancel_by_nonce"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, CancelByNonceResponse)

        return result

    async def cancel_trigger_order(
        self,
        params: CancelTriggerOrderRequest,
    ) -> Order:
        """
        Cancels a single pending trigger order identified by order_id and subaccount_id.
        Requires any trade scope; returns the cancelled order.
        """

        method = "private/cancel_trigger_order"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, Order)

        return result

    async def get_algo_orders(
        self,
        params: GetAlgoOrdersRequest,
    ) -> list[Order]:
        """
        Returns all active algo orders (e.g. time-sliced execution orders) for the given
        subaccount as a flat list. Read-only query.
        """

        method = "private/get_algo_orders"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, list[Order])

        return result

    async def get_open_orders(
        self,
        params: GetOpenOrdersRequest,
    ) -> AggregatedOrdersResult:
        """
        Returns all currently open orders for the given subaccount, including each
        order's instrument, direction, prices, amounts and status. Only orders resting
        on the order book are returned: pending trigger orders that have not yet fired
        are available from get_trigger_orders, and active algo orders from
        get_algo_orders. Once a trigger order fires, the resulting order appears here if
        it rests on the book rather than filling immediately; algo orders execute as IOC
        slices and so never rest here. Read-only query.
        """

        method = "private/get_open_orders"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, AggregatedOrdersResult)

        return result

    async def get_order(
        self,
        params: GetOrderRequest,
    ) -> Order:
        """
        Returns one order (active or completed) by order_id and subaccount_id; the
        subaccount filter enforces ownership. Returns the order or an order-does-not-
        exist error.
        """

        method = "private/get_order"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, Order)

        return result

    async def get_trigger_orders(
        self,
        params: GetTriggerOrdersRequest,
    ) -> AggregatedTriggerOrdersResult:
        """
        Returns all pending trigger (conditional) orders for the given subaccount that
        have not yet fired. Read-only query.
        """

        method = "private/get_trigger_orders"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, AggregatedTriggerOrdersResult)

        return result

    async def order(
        self,
        params: CreateOrderRequest,
    ) -> OrderCreatedResponse:
        """
        Submits a signed limit or market order for a subaccount, specifying instrument,
        direction, amount, limit price and max fee, plus optional flags like time-in-
        force, reduce-only, post-only and MMP. The same endpoint also creates trigger
        orders (via trigger_type/trigger_price) and algo orders (via algo_type), though
        the two cannot be combined in one request. Requires a signed order payload and
        Orderbook trade scope for the instrument's asset; returns the created order with
        its assigned id and current status.
        """

        method = "private/order"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, OrderCreatedResponse)

        return result

    async def order_debug(
        self,
        params: CreateOrderRequest,
    ) -> OrderDebugResponse:
        """
        Takes the same params as private/order and rebuilds the order Action without
        executing anything, returning the EIP-712 encoded_data, encoded_data_hashed,
        action_hash, typed_data_hash, domain_separator, action_typehash, module, owner
        and expected_signer, plus the decoded order action data. Byte-compare these
        against your local computation to find why a signature is rejected. Requires a
        logged-in session; no trade scope needed.
        """

        method = "private/order_debug"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, OrderDebugResponse)

        return result

    async def order_quote(
        self,
        params: OrderQuoteRequest,
    ) -> OrderQuoteResponse:
        """
        Dry-run pricing helper that estimates the outcome of a prospective order without
        placing it, returning projected fill price and amount, fees, pre/post initial
        margin, realized PnL, resulting order status and (where relevant) liquidation
        price and max tradable amount. All monetary values are returned as decimal
        strings. The private variant requires account-level authentication.
        """

        method = "private/order_quote"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, OrderQuoteResponse)

        return result

    async def replace(
        self,
        params: ReplaceOrderRequest,
    ) -> ReplaceOrderResponse:
        """
        Atomically cancels a resting order (identified by order_id_to_cancel or
        nonce_to_cancel) and submits a replacement order in a single request. The
        payload is a full new-order specification plus the cancel target and an optional
        expected_filled_amount guard. Requires a signed order payload and Orderbook
        trade scope; returns both the cancelled and the newly created order.
        """

        method = "private/replace"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, ReplaceOrderResponse)

        return result

    async def cancel_batch_quotes(
        self,
        params: CancelBatchQuotesRequest,
    ) -> CancelBatchResult:
        """
        Cancels all open quotes on a subaccount that match the supplied filters (any
        combination of quote_id, rfq_id, label, and nonce, applied together) in a single
        atomic operation. Omitting the optional filters targets all of the subaccount's
        open quotes. Returns the list of cancelled quote ids. Requires an RFQ trade
        scope.
        """

        method = "private/cancel_batch_quotes"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, CancelBatchResult)

        return result

    async def cancel_batch_rfqs(
        self,
        params: CancelBatchRfqsRequest,
    ) -> CancelBatchRfqsResponse:
        """
        Cancels all open RFQs on a subaccount that match the supplied filters (any
        combination of rfq_id, label, and nonce, applied together), cascade-cancelling
        their quotes. Omitting the optional filters targets all of the subaccount's open
        RFQs. Returns the set of cancelled RFQs. Requires an RFQ trade scope.
        """

        method = "private/cancel_batch_rfqs"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, CancelBatchRfqsResponse)

        return result

    async def cancel_quote(
        self,
        params: CancelQuoteRequest,
    ) -> Quote:
        """
        Cancels one open quote owned by the subaccount, identified by quote_id
        (optionally further constrained by rfq_id, label, or nonce). Returns the
        cancelled quote, or a quote-not-found error if it does not exist or is no longer
        open. Requires an RFQ trade scope.
        """

        method = "private/cancel_quote"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, Quote)

        return result

    async def cancel_rfq(
        self,
        params: CancelRfqRequest,
    ) -> str:
        """
        Cancels one open RFQ owned by the given subaccount and cascade-cancels any
        quotes makers have submitted against it, notifying those makers. Identify the
        RFQ by its rfq_id. Returns "ok" on success. Requires an RFQ trade scope.
        """

        method = "private/cancel_rfq"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, str)

        return result

    async def execute_quote(
        self,
        params: ExecuteQuoteRequest,
    ) -> QuoteExecuteResponse:
        """
        Taker-side call that accepts a specific maker quote and settles the trade
        atomically. You reference the rfq_id and quote_id and supply the taker's priced
        legs, direction, max fee, and EIP-712 signature (signer, signature, nonce,
        expiry), with an optional taker-protection flag. The signature is verified and
        the taker fill, maker quote, and RFQ are updated together in one atomic step.
        Requires trade scope for every instrument in the legs.
        """

        method = "private/execute_quote"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, QuoteExecuteResponse)

        return result

    async def get_quotes(
        self,
        params: GetQuotesRequest,
    ) -> QuoteGetResponse:
        """
        Returns a paginated, merged view of a subaccount's quotes, combining currently
        open quotes with the archived history of filled, cancelled, and expired ones.
        Supports filtering by quote_id, rfq_id, status, and a from/to timestamp window,
        with page and page_size controls. Each entry includes priced legs, direction,
        fees, liquidity role, and fill percentage.
        """

        method = "private/get_quotes"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, QuoteGetResponse)

        return result

    async def get_rfqs(
        self,
        params: GetRfqsRequest,
    ) -> RFQGetResponse:
        """
        Returns a paginated, merged view of a subaccount's RFQs, combining currently
        open RFQs with the archived history of filled, cancelled, and expired ones.
        Supports filtering by rfq_id, status, and a from/to timestamp window, with page
        and page_size controls. Each entry includes legs, status, timestamps, cost
        bounds, and fill percentage.
        """

        method = "private/get_rfqs"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, RFQGetResponse)

        return result

    async def poll_quotes(
        self,
        params: PollQuotesRequest,
    ) -> QuotePollResponse:
        """
        Taker-side call that lists the maker quotes received against RFQs owned by the
        subaccount. Supports filtering by quote_id, rfq_id, status, and a timestamp
        window, with pagination. Returns public quote views (including the maker's
        wallet) without any signing material.
        """

        method = "private/poll_quotes"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, QuotePollResponse)

        return result

    async def poll_rfqs(
        self,
        params: PollRfqsRequest,
    ) -> RFQPollResponse:
        """
        Maker-side call that lists the RFQs a subaccount is eligible to quote, i.e. RFQs
        that are open to all makers or that name the maker's wallet as a counterparty.
        Supports filtering by rfq_id, status, an originating RFQ subaccount, and a
        timestamp window, with pagination. Returns public RFQ views without taker-
        private signing material.
        """

        method = "private/poll_rfqs"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, RFQPollResponse)

        return result

    async def replace_quote(
        self,
        params: ReplaceQuoteRequest,
    ) -> QuoteReplaceResponse:
        """
        Maker-side call that atomically cancels an existing quote and submits a new
        signed quote for the same RFQ in one operation. You provide the new priced legs,
        direction, max fee, and EIP-712 signature, plus the quote to cancel (by quote_id
        or nonce_to_cancel). Returns the cancellation result together with the newly
        created quote. Requires trade scope for every instrument quoted.
        """

        method = "private/replace_quote"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, QuoteReplaceResponse)

        return result

    async def rfq_get_best_quote(
        self,
        params: RfqGetBestQuoteRequest,
    ) -> RfqGetBestQuoteResponse:
        """
        Taker-side dry run that evaluates a prospective RFQ (its legs and intended
        direction) without creating anything. Returns the best available maker quote if
        one exists, along with the expected fee, validity, projected liquidation prices,
        and realized-PnL estimate for taking it.
        """

        method = "private/rfq_get_best_quote"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, RfqGetBestQuoteResponse)

        return result

    async def send_quote(
        self,
        params: SendQuoteRequest,
    ) -> Quote:
        """
        Maker-side call that submits a priced, signed quote in response to an existing
        RFQ. You provide the priced legs, direction, max fee, an EIP-712 signature
        (signer, signature, nonce, expiry), and optional label or MMP flag. The quote's
        signature is verified and validated against the referenced RFQ before it is
        stored. Returns the created quote. Requires trade scope for every instrument
        quoted.
        """

        method = "private/send_quote"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, Quote)

        return result

    async def send_rfq(
        self,
        params: SendRfqRequest,
    ) -> Rfq:
        """
        Taker-side call that opens a new RFQ for a multi-leg structure on a subaccount,
        inviting makers to quote it. You supply the legs (instrument, amount, and
        direction per leg) plus optional limits such as min/max total cost, a partial-
        fill step, a label, and a list of specific counterparties to restrict who can
        see it. Returns the created RFQ including its assigned id and validity window.
        Requires trade scope for every instrument in the legs.
        """

        method = "private/send_rfq"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, Rfq)

        return result

    async def cancel_all_vault_requests(
        self,
        params: CancelVaultRequestRequest,
    ) -> VaultCancelResponse:
        """
        Submits a signed cancel action that drains all of the caller's pending deposit
        and withdraw requests for a given vault and posts the corresponding on-chain
        operation. Input is the vault subaccount; any subaccount the caller owns may
        sign. Requires the user-cancel permission.
        """

        method = "private/cancel_all_vault_requests"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, VaultCancelResponse)

        return result

    async def get_live_vault_requests(
        self,
        params: GetLiveVaultRequestsRequest,
    ) -> MultipleVaultRequestsResponse:
        """
        Returns the caller's currently-pending vault deposit and withdraw requests, read
        live from the vault queue. Not paginated (the live queue is bounded); settled
        and terminal history is served by get_vault_request_history. The wallet
        parameter must match the authenticated connection.
        """

        method = "private/get_live_vault_requests"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, MultipleVaultRequestsResponse)

        return result

    async def get_shareholder_vaults(
        self,
        params: GetShareholderVaultsRequest,
    ) -> VaultIdsResponse:
        """
        Returns the subaccount ids of the vaults in which the given wallet holds shares.
        The wallet parameter must match the authenticated connection. Read-only.
        """

        method = "private/get_shareholder_vaults"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, VaultIdsResponse)

        return result

    async def get_vault_request_history(
        self,
        params: GetVaultRequestHistoryRequest,
    ) -> PaginatedVaultRequestHistory:
        """
        Returns the caller's full vault action history (deposits, withdrawals, force-
        withdrawals, and cancels) across every status — enqueued, requested, applied,
        cancelled, rejected, or expired — with one row per action at its latest state.
        Paginated by page and page_size; monetary amounts, prices, and share counts are
        decimal strings. The wallet parameter must match the authenticated connection.
        """

        method = "private/get_vault_request_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PaginatedVaultRequestHistory)

        return result

    async def get_vault_shares(
        self,
        params: GetVaultSharesRequest,
    ) -> VaultSharesResponse:
        """
        Returns the caller's share balance for every vault it holds shares in, each
        paired with the full enriched vault row (the same shape as public/get_vault).
        The wallet parameter must match the authenticated connection. Read-only.
        """

        method = "private/get_vault_shares"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, VaultSharesResponse)

        return result

    async def request_vault_deposit(
        self,
        params: RequestVaultDepositRequest,
    ) -> VaultRequestAckResponse:
        """
        Submits a signed deposit action from the user's source subaccount and enqueues
        it in the vault's pending-deposit queue for the curator to settle. Inputs are
        the target vault subaccount, the deposit asset, and the amount as a decimal
        string. Returns an acknowledgement with the queued request; requires the user-
        deposit permission.
        """

        method = "private/request_vault_deposit"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, VaultRequestAckResponse)

        return result

    async def request_vault_withdraw(
        self,
        params: RequestVaultWithdrawRequest,
    ) -> VaultRequestAckResponse:
        """
        Submits a signed withdraw action that enqueues a request to burn a given number
        of vault shares and redeem the proceeds to the user's subaccount. Inputs are the
        vault subaccount and the share quantity to burn (decimal string). Returns an
        acknowledgement with the queued request; requires the user-withdraw permission.
        """

        method = "private/request_vault_withdraw"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, VaultRequestAckResponse)

        return result

    async def burn_vault_shares(
        self,
        params: BurnSharesRequest,
    ) -> VaultSettleResponse:
        """
        Curator-only endpoint that settles a pending withdraw request by signing a burn
        approval at a quoted share price (USD per share). Takes the request id and the
        user's withdraw-action hash, burns the shares, and returns the settlement
        result. Requires the curator mint-and-burn permission.
        """

        method = "private/burn_vault_shares"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, VaultSettleResponse)

        return result

    async def create_vault(
        self,
        params: CreateVaultRequest,
    ) -> VaultCreateResponse:
        """
        Registers a new vault on-chain from a signed action; the signing wallet becomes
        the vault's curator and seeds the initial deposit from its funding subaccount.
        Inputs set the deposit asset, initial deposit amount, initial share price,
        management/performance fee rates (in basis points), max slippage, redemption
        cooldown, an optional benchmark asset for the high-water mark, and the max
        sequencer fee authorized. Requires the vault curator-create permission.
        """

        method = "private/create_vault"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, VaultCreateResponse)

        return result

    async def force_burn(
        self,
        params: ForceBurnRequest,
    ) -> VaultForceBurnResponse:
        """
        Curator-only endpoint that builds an on-chain action to forcibly redeem a given
        holder's entire share balance at the current mark-to-market share price. Inputs
        are the vault subaccount and the holder's wallet address. Requires the curator
        mint-and-burn permission.
        """

        method = "private/force_burn"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, VaultForceBurnResponse)

        return result

    async def get_curated_vaults(
        self,
        params: GetCuratedVaultsRequest,
    ) -> VaultIdsResponse:
        """
        Returns the subaccount ids of the vaults curated by the given wallet. The wallet
        parameter must match the authenticated connection. Read-only.
        """

        method = "private/get_curated_vaults"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, VaultIdsResponse)

        return result

    async def get_live_burn_requests(
        self,
        params: GetLiveBurnRequestsRequest,
    ) -> MultipleVaultRequestsResponse:
        """
        Curator-only endpoint that returns a FIFO page of a vault's pending withdraw
        (burn) requests. Inputs are the vault subaccount and a page limit. Requires the
        curator mint-and-burn permission.
        """

        method = "private/get_live_burn_requests"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, MultipleVaultRequestsResponse)

        return result

    async def get_live_mint_requests(
        self,
        params: GetLiveMintRequestsRequest,
    ) -> MultipleVaultRequestsResponse:
        """
        Curator-only endpoint that returns a FIFO page of a vault's pending deposit
        (mint) requests. Inputs are the vault subaccount and a page limit. Requires the
        curator mint-and-burn permission.
        """

        method = "private/get_live_mint_requests"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, MultipleVaultRequestsResponse)

        return result

    async def mint_vault_shares(
        self,
        params: MintSharesRequest,
    ) -> VaultSettleResponse:
        """
        Curator-only endpoint that settles a pending deposit request by signing a mint
        approval at a quoted share price (USD per share). Takes the request id and the
        user's deposit-action hash, mints the corresponding shares, and returns the
        settlement result. Requires the curator mint-and-burn permission.
        """

        method = "private/mint_vault_shares"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, VaultSettleResponse)

        return result

    async def reject_deposit_request(
        self,
        params: RejectDepositRequestRequest,
    ) -> VaultRequestAckResponse:
        """
        Curator-only endpoint that removes a queued deposit request off-chain (no on-
        chain settlement), recording the rejection with an optional short reason. Takes
        the request id and returns an acknowledgement. Requires the curator mint-and-
        burn permission.
        """

        method = "private/reject_deposit_request"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, VaultRequestAckResponse)

        return result

    async def update_vault_info(
        self,
        params: UpdateVaultInfoRequest,
    ) -> OffchainAckResponse:
        """
        Applies an off-chain patch to a vault the caller curates, updating any of its
        display name, description, advisory mark-to-market cap (a USD decimal), or
        whitelist-only flag. Only the fields supplied are changed. The caller must own
        the vault's subaccount (i.e. be its curator); description length is capped.
        """

        method = "private/update_vault_info"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, OffchainAckResponse)

        return result

    async def get_deposit_history(
        self,
        params: GetDepositHistoryRequest,
    ) -> DepositHistoryResult:
        """
        Returns settled deposits for a single subaccount or an entire wallet (specify
        exactly one), optionally bounded by a start/end timestamp window. Each entry
        reports the deposited amount as a decimal, the fee routed to the security module
        (the net credited amount is amount minus fee), and the resolved settlement batch
        and status.
        """

        method = "private/get_deposit_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, DepositHistoryResult)

        return result

    async def get_erc20_transfer_history(
        self,
        params: GetErc20TransferHistoryRequest,
    ) -> TransferHistoryResult:
        """
        Returns settled spot (ERC-20) transfers involving a single subaccount or an
        entire wallet (specify exactly one), optionally bounded by a start/end timestamp
        window. Each entry reports the transfer amount and fee as decimals along with
        direction — the sender sees the gross amount plus fee, the receiver sees the net
        credit — plus the resolved settlement batch and status.
        """

        method = "private/get_erc20_transfer_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, TransferHistoryResult)

        return result

    async def get_funding_history(
        self,
        params: GetFundingHistoryRequest,
    ) -> PerpSettlementHistoryResponse:
        """
        Returns a paginated history of perpetual funding (settlement) events for a
        single subaccount or an entire wallet (specify exactly one), optionally bounded
        by a start/end timestamp window and filtered by perpetual instrument name. The
        response includes the funding events with their instrument name and settled
        amounts, plus pagination info with total count and page count.
        """

        method = "private/get_funding_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PerpSettlementHistoryResponse)

        return result

    async def get_interest_history(
        self,
        params: GetInterestHistoryRequest,
    ) -> InterestHistoryResult:
        """
        Returns realized interest settlements per subaccount, for a single subaccount or
        an entire wallet (specify exactly one), optionally bounded by a start/end
        timestamp window. Each entry gives the settled interest as a decimal, where a
        negative value was paid (borrowed) and a positive value was received (supplied).
        """

        method = "private/get_interest_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, InterestHistoryResult)

        return result

    async def get_option_settlement_history(
        self,
        params: GetOptionSettlementHistoryParams,
    ) -> OptionSettlementHistoryResponse:
        """
        Returns option settlement (expiry) events for a single subaccount or an entire
        wallet (specify exactly one). Each settlement includes the reconstructed option
        instrument name and the settled amounts for that expired position.
        """

        method = "private/get_option_settlement_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, OptionSettlementHistoryResponse)

        return result

    async def get_order_history(
        self,
        params: GetOrderHistoryRequest,
    ) -> PaginatedOrdersResult:
        """
        Returns a paginated history of orders for a single subaccount or for an entire
        wallet (specify exactly one), optionally bounded by a from/to timestamp window.
        Only orders in a terminal state (filled, cancelled, expired) are recorded here,
        one record per order. Trigger and algo orders appear once they terminate,
        carrying their accumulated filled amount; while they are still live — including
        partially executed algo orders and trigger orders that have not yet fired — read
        them from get_trigger_orders and get_algo_orders instead. Each page includes the
        order records plus pagination info with the total count and number of pages.
        """

        method = "private/get_order_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PaginatedOrdersResult)

        return result

    async def get_trade_history(
        self,
        params: GetTradeHistoryRequest,
    ) -> PaginatedTradesResult:
        """
        Returns a paginated history of executed trades for a single subaccount or an
        entire wallet (specify exactly one), with optional filters for a time window,
        order id, instrument name, or quote id. The response includes the trade records
        and pagination info with total count and page count.
        """

        method = "private/get_trade_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PaginatedTradesResult)

        return result

    async def get_withdrawal_history(
        self,
        params: GetWithdrawalHistoryRequest,
    ) -> WithdrawalHistoryResult:
        """
        Returns settled withdrawals for a single subaccount or an entire wallet (specify
        exactly one), optionally bounded by a start/end timestamp window. Each entry
        reports the withdrawn amount as a decimal, the fee routed to the security module
        (the net amount sent to the recipient is amount minus fee), and the resolved
        settlement batch and status.
        """

        method = "private/get_withdrawal_history"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, WithdrawalHistoryResult)

        return result

    async def get_mmp_config(
        self,
        params: MmpScopeRequest,
    ) -> list[MmpConfigResult]:
        """
        Returns the market maker protection (MMP) settings for a subaccount, optionally
        filtered to a single currency. Each entry reports the amount and delta limits
        (as decimal strings), the rolling interval and freeze duration (in
        milliseconds), and the current freeze state, including whether MMP is currently
        frozen and the timestamp at which it unfreezes.
        """

        method = "private/get_mmp_config"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, list[MmpConfigResult])

        return result

    async def reset_mmp(
        self,
        params: MmpScopeRequest,
    ) -> str:
        """
        Clears an active market maker protection freeze and resets the rolling MMP
        window for a subaccount, optionally scoped to a single currency. Use this to
        resume quoting after MMP has frozen a subaccount. Requires a trading-scoped
        session key and returns "ok" on success.
        """

        method = "private/reset_mmp"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, str)

        return result

    async def set_mmp_config(
        self,
        params: SetMmpConfigRequest,
    ) -> SetMmpConfigResponse:
        """
        Creates or fully replaces the market maker protection settings for a subaccount
        and currency. Accepts an amount limit and delta limit (as decimals) plus the
        rolling interval and freeze duration in milliseconds; omitted limits default to
        zero. Requires a trading-scoped session key and echoes the applied configuration
        back.
        """

        method = "private/set_mmp_config"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, SetMmpConfigResponse)

        return result

    async def transfer_positions(
        self,
        params: TransferPositionsRequest,
    ) -> TransferPositionsResponse:
        """
        Atomically transfers one or more derivative positions between a maker and a
        taker subaccount using matched, signed transfer quotes. Each side supplies its
        subaccount, signer, nonce, signature, expiry, max fee, direction, and priced
        legs (instrument, amount, price); the two quotes must mirror each other.
        Requires a session key with transfer permission and returns the resulting
        operation details.
        """

        method = "private/transfer_positions"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, TransferPositionsResponse)

        return result

    async def transfer_spot(
        self,
        params: PrivateTransferSpotRequest,
    ) -> PrivateTransferSpotResponse:
        """
        Submits a signed transfer of a single spot asset from one subaccount to another
        subaccount you own. You specify the source and destination subaccounts (or set
        new_subaccount_manager to create a new destination subaccount under a manager),
        the asset and its sub_id, the amount, a nonce, signer, signature with expiry,
        and the maximum USD sequencer fee. Requires a session key with a transfer
        permission and returns the operation id and uuid.
        """

        method = "private/transfer_spot"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PrivateTransferSpotResponse)

        return result

    async def transfer_spot_external(
        self,
        params: PrivateTransferSpotExternalRequest,
    ) -> PrivateTransferSpotExternalResponse:
        """
        Submits a signed transfer of a single spot asset to a subaccount belonging to a
        different owner. Alongside the standard transfer fields (asset, sub_id, amount,
        nonce, signer, signature, expiry, max USD fee) you give the recipient's wallet
        address and either an existing destination subaccount or 0 to create a new one
        under new_subaccount_manager; the max fee must cover both the transfer and any
        subaccount-creation cost. Requires a session key permitted to transfer to a
        different owner and returns the operation id and uuid.
        """

        method = "private/transfer_spot_external"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PrivateTransferSpotExternalResponse)

        return result

    async def update_whitelisted_recipients(
        self,
        params: UpdateWhitelistedRecipientsRequest,
    ) -> UpdateWhitelistedRecipientsResponse:
        """
        Adds and/or removes recipient wallet addresses on an account's transfer
        whitelist via a signed, wallet-level action. Provide the owner wallet, signer,
        nonce, signature with expiry, and the add and remove address lists. This is an
        owner-or-admin operation (session keys need the admin scope); it returns the
        operation id, uuid, and the full whitelist after the update is applied.
        """

        method = "private/update_whitelisted_recipients"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, UpdateWhitelistedRecipientsResponse)

        return result

    async def withdraw(
        self,
        params: PrivateWithdrawRequest,
    ) -> PrivateWithdrawResponse:
        """
        Submits a signed request to withdraw a spot asset out of a subaccount. You
        provide the subaccount id, asset name, amount in underlying units, a nonce, the
        signer, an EIP-712 signature with its expiry, and the maximum sequencer fee (in
        USD) you authorise; setting force_batch controls whether the withdrawal is
        batched. Requires a session key with withdraw permission, and returns the
        accepted operation id and its uuid for tracking.
        """

        method = "private/withdraw"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PrivateWithdrawResponse)

        return result

    async def liquidate(
        self,
        params: PrivateLiquidateRequest,
    ) -> PrivateLiquidateResponse:
        """
        private/liquidate
        """

        method = "private/liquidate"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PrivateLiquidateResponse)

        return result

    async def set_session_key(
        self,
        params: SetSessionKeyRequest,
    ) -> PrivateSetSessionKeyResponse:
        """
        private/set_session_key
        """

        method = "private/set_session_key"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, PrivateSetSessionKeyResponse)

        return result

    async def set_cancel_on_disconnect(
        self,
        params: SetCancelOnDisconnectRequest,
    ) -> str:
        """
        WebSocket-only method that toggles cancel on disconnect for the authenticated
        wallet. While enabled, dropping the WebSocket connection cancels the wallet's
        open orders, trigger and algo orders, and quotes. Pass enabled true or false;
        omitting it leaves the setting unchanged. Requires a session key with full trade
        scope; returns "ok".
        """

        method = "private/set_cancel_on_disconnect"
        envelope = await self._session._send_request(method, params=params)
        result = decode_result(envelope, str)

        return result


# ============================================================================
# Channel Subscription Classes
# ============================================================================


class PublicChannels:
    """public channel subscriptions"""

    def __init__(self, session: WebSocketSession):
        self._session = session

    async def auctions_watch(
        self,
        callback: Handler[list[AuctionResult]],
    ) -> SubscriptionResult:
        """
        Channel name: `auctions.watch`. Public channel that streams the live state of
        all ongoing liquidation and insolvency auctions across the exchange. Takes no
        parameters.

        Args:
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "auctions.watch".format()
        envelope = await self._session.subscribe(channel, callback, list[AuctionResult])
        result = decode_result(envelope, SubscriptionResult)

        return result

    async def margin_watch(
        self,
        callback: Handler[list[MarginWatchResult]],
    ) -> SubscriptionResult:
        """
        Channel name: `margin.watch`. Public channel that streams margin and mark-to-
        market state for all accounts, letting you monitor collateralization and
        liquidation risk across the exchange. Takes no parameters.

        Args:
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "margin.watch".format()
        envelope = await self._session.subscribe(channel, callback, list[MarginWatchResult])
        result = decode_result(envelope, SubscriptionResult)

        return result

    async def orderbook_group_depth_by_instrument_name(
        self,
        instrument_name: str,
        group: Literal[1, 10, 100],
        depth: Literal[1, 10, 20, 100],
        callback: Handler[OrderbookSnapshot],
    ) -> SubscriptionResult:
        """
        Channel name: `orderbook.{instrument_name}.{group}.{depth}`. Public channel that
        periodically publishes aggregated bids and asks for a single instrument, where
        {instrument_name} is the market (e.g. ETH-PERP), {group} is the price-level
        aggregation size (1, 10, or 100), and {depth} is the number of levels returned
        per side (1, 10, 20, or 100).

        Args:
            instrument_name: Instrument Name
            group: Group
            depth: Depth
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "orderbook.{instrument_name}.{group}.{depth}".format(
            instrument_name=instrument_name.value if isinstance(instrument_name, Enum) else instrument_name,
            group=group.value if isinstance(group, Enum) else group,
            depth=depth.value if isinstance(depth, Enum) else depth,
        )
        envelope = await self._session.subscribe(channel, callback, OrderbookSnapshot)
        result = decode_result(envelope, SubscriptionResult)

        return result

    async def spot_feed_by_currency(
        self,
        currency: str,
        callback: Handler[SpotFeedPayload],
    ) -> SubscriptionResult:
        """
        Channel name: `spot_feed.{currency}`. Public channel that streams the spot price
        feed for a given underlying, where {currency} selects the asset (e.g. ETH or
        BTC).

        Args:
            currency: Currency
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "spot_feed.{currency}".format(
            currency=currency.value if isinstance(currency, Enum) else currency,
        )
        envelope = await self._session.subscribe(channel, callback, SpotFeedPayload)
        result = decode_result(envelope, SubscriptionResult)

        return result

    async def ticker_slim_interval_by_instrument_name(
        self,
        instrument_name: str,
        interval: Literal[100, 1000],
        callback: Handler[TickerSlimPayload],
    ) -> SubscriptionResult:
        """
        Channel name: `ticker_slim.{instrument_name}.{interval}`. Public channel that
        streams a lightweight ticker (prices and key stats) for an instrument, where
        {instrument_name} is the market and {interval} is the update cadence in
        milliseconds (100 or 1000).

        Args:
            instrument_name: Instrument Name
            interval: Interval
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "ticker_slim.{instrument_name}.{interval}".format(
            instrument_name=instrument_name.value if isinstance(instrument_name, Enum) else instrument_name,
            interval=interval.value if isinstance(interval, Enum) else interval,
        )
        envelope = await self._session.subscribe(channel, callback, TickerSlimPayload)
        result = decode_result(envelope, SubscriptionResult)

        return result

    async def trades_by_instrument_name(
        self,
        instrument_name: str,
        callback: Handler[list[PublicTrade]],
    ) -> SubscriptionResult:
        """
        Channel name: `trades.{instrument_name}`. Public channel that streams the public
        trade tape for a single instrument, where {instrument_name} is the market whose
        fills you want to follow.

        Args:
            instrument_name: Instrument Name
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "trades.{instrument_name}".format(
            instrument_name=instrument_name.value if isinstance(instrument_name, Enum) else instrument_name,
        )
        envelope = await self._session.subscribe(channel, callback, list[PublicTrade])
        result = decode_result(envelope, SubscriptionResult)

        return result

    async def trades_by_instrument_type(
        self,
        instrument_type: AssetType,
        currency: str,
        callback: Handler[list[PublicTrade]],
    ) -> SubscriptionResult:
        """
        Channel name: `trades.{instrument_type}.{currency}`. Public channel that streams
        public trades filtered by market category, where {instrument_type} is the kind
        of instrument (erc20, option, or perp) and {currency} is the underlying asset
        (e.g. ETH or BTC).

        Args:
            instrument_type: Instrument Type
            currency: Currency
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "trades.{instrument_type}.{currency}".format(
            instrument_type=instrument_type.value if isinstance(instrument_type, Enum) else instrument_type,
            currency=currency.value if isinstance(currency, Enum) else currency,
        )
        envelope = await self._session.subscribe(channel, callback, list[PublicTrade])
        result = decode_result(envelope, SubscriptionResult)

        return result

    async def trades_batch_status_by_instrument_type(
        self,
        instrument_type: AssetType,
        currency: str,
        batch_status: str,
        callback: Handler[list[SettledTrade]],
    ) -> SubscriptionResult:
        """
        Channel name: `trades.{instrument_type}.{currency}.{batch_status}`. Public
        channel that streams public trades filtered by category, underlying, and
        settlement batch status, where {instrument_type} is the instrument kind (erc20,
        option, or perp), {currency} is the underlying asset, and {batch_status} is the
        batch lifecycle stage (e.g. Settled, or a ...Error stage).

        Args:
            instrument_type: Instrument Type
            currency: Currency
            batch_status: Batch Status
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "trades.{instrument_type}.{currency}.{batch_status}".format(
            instrument_type=instrument_type.value if isinstance(instrument_type, Enum) else instrument_type,
            currency=currency.value if isinstance(currency, Enum) else currency,
            batch_status=batch_status.value if isinstance(batch_status, Enum) else batch_status,
        )
        envelope = await self._session.subscribe(channel, callback, list[SettledTrade])
        result = decode_result(envelope, SubscriptionResult)

        return result


class PrivateChannels:
    """private channel subscriptions"""

    def __init__(self, session: WebSocketSession):
        self._session = session

    async def balances_by_subaccount_id(
        self,
        subaccount_id: str,
        callback: Handler[list[BalanceUpdate]],
    ) -> SubscriptionResult:
        """
        Channel name: `{subaccount_id}.balances`. Private channel (requires
        authentication) that streams balance and position updates for one of your
        subaccounts, where {subaccount_id} is the numeric subaccount identifier.

        Args:
            subaccount_id: Subaccount Id
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "{subaccount_id}.balances".format(
            subaccount_id=subaccount_id.value if isinstance(subaccount_id, Enum) else subaccount_id,
        )
        envelope = await self._session.subscribe(channel, callback, list[BalanceUpdate])
        result = decode_result(envelope, SubscriptionResult)

        return result

    async def best_quotes_by_subaccount_id(
        self,
        subaccount_id: str,
        callback: Handler[list[BestQuoteChannelResult]],
    ) -> SubscriptionResult:
        """
        Channel name: `{subaccount_id}.best.quotes`. Private channel (requires
        authentication) that streams best-quote updates relevant to your subaccount,
        where {subaccount_id} is the numeric subaccount identifier.

        Args:
            subaccount_id: Subaccount Id
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "{subaccount_id}.best.quotes".format(
            subaccount_id=subaccount_id.value if isinstance(subaccount_id, Enum) else subaccount_id,
        )
        envelope = await self._session.subscribe(channel, callback, list[BestQuoteChannelResult])
        result = decode_result(envelope, SubscriptionResult)

        return result

    async def orders_by_subaccount_id(
        self,
        subaccount_id: str,
        callback: Handler[list[Order]],
    ) -> SubscriptionResult:
        """
        Channel name: `{subaccount_id}.orders`. Private channel (requires
        authentication) that streams live order updates (opens, fills, cancels, and
        status changes) for your subaccount, where {subaccount_id} is the numeric
        subaccount identifier.

        Args:
            subaccount_id: Subaccount Id
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "{subaccount_id}.orders".format(
            subaccount_id=subaccount_id.value if isinstance(subaccount_id, Enum) else subaccount_id,
        )
        envelope = await self._session.subscribe(channel, callback, list[Order])
        result = decode_result(envelope, SubscriptionResult)

        return result

    async def quotes_by_subaccount_id(
        self,
        subaccount_id: str,
        callback: Handler[list[QuotePublishResult]],
    ) -> SubscriptionResult:
        """
        Channel name: `{subaccount_id}.quotes`. Private channel (requires
        authentication) that streams updates to your RFQ quotes for a subaccount, where
        {subaccount_id} is the numeric subaccount identifier.

        Args:
            subaccount_id: Subaccount Id
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "{subaccount_id}.quotes".format(
            subaccount_id=subaccount_id.value if isinstance(subaccount_id, Enum) else subaccount_id,
        )
        envelope = await self._session.subscribe(channel, callback, list[QuotePublishResult])
        result = decode_result(envelope, SubscriptionResult)

        return result

    async def trades_by_subaccount_id(
        self,
        subaccount_id: str,
        callback: Handler[list[Trade]],
    ) -> SubscriptionResult:
        """
        Channel name: `{subaccount_id}.trades`. Private channel (requires
        authentication) that streams your subaccount's own trade fills as they occur,
        where {subaccount_id} is the numeric subaccount identifier.

        Args:
            subaccount_id: Subaccount Id
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "{subaccount_id}.trades".format(
            subaccount_id=subaccount_id.value if isinstance(subaccount_id, Enum) else subaccount_id,
        )
        envelope = await self._session.subscribe(channel, callback, list[Trade])
        result = decode_result(envelope, SubscriptionResult)

        return result

    async def trades_batch_status_by_subaccount_id(
        self,
        subaccount_id: str,
        batch_status: str,
        callback: Handler[list[Trade]],
    ) -> SubscriptionResult:
        """
        Channel name: `{subaccount_id}.trades.{batch_status}`. Private channel (requires
        authentication) that streams your subaccount's trades filtered by settlement
        batch status, where {subaccount_id} is the numeric subaccount identifier and
        {batch_status} is the batch lifecycle stage (e.g. Settled, or a ...Error stage).

        Args:
            subaccount_id: Subaccount Id
            batch_status: Batch Status
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "{subaccount_id}.trades.{batch_status}".format(
            subaccount_id=subaccount_id.value if isinstance(subaccount_id, Enum) else subaccount_id,
            batch_status=batch_status.value if isinstance(batch_status, Enum) else batch_status,
        )
        envelope = await self._session.subscribe(channel, callback, list[Trade])
        result = decode_result(envelope, SubscriptionResult)

        return result

    async def rfqs_by_wallet(
        self,
        wallet: str,
        callback: Handler[list[PublicRfq]],
    ) -> SubscriptionResult:
        """
        Channel name: `{wallet}.rfqs`. Private channel (requires authentication) that
        streams RFQ (request-for-quote) updates for all subaccounts under a wallet,
        where {wallet} is your wallet address.

        Args:
            wallet: Wallet
            callback: Callback function to handle notifications

        Returns:
            Subscription result with status and current subscriptions
        """

        channel = "{wallet}.rfqs".format(
            wallet=wallet.value if isinstance(wallet, Enum) else wallet,
        )
        envelope = await self._session.subscribe(channel, callback, list[PublicRfq])
        result = decode_result(envelope, SubscriptionResult)

        return result


# ============================================================================
# Combined API Classes
# ============================================================================


class PublicAPI:
    """Combined  public API - RPC and channels"""

    def __init__(self, session: WebSocketSession):
        self.rpc = PublicRPC(session)

        self.channels = PublicChannels(session)


class PrivateAPI:
    """Combined  private API - RPC and channels"""

    def __init__(self, session: WebSocketSession):
        self.rpc = PrivateRPC(session)

        self.channels = PrivateChannels(session)
