"""Auto-generated endpoint definitions from OpenAPI spec."""

from __future__ import annotations

from typing import Any, overload


class Endpoint:
    """Descriptor that provides both REST URLs and WebSocket method names."""

    def __init__(self, section: str, path: str):
        self.section = section
        self.path = path
        self.method = f"{section}/{path}"

    def url(self, base_url: str) -> str:
        """Returns full URL for REST"""
        return f"{base_url.rstrip('/')}/{self.method}"

    @overload
    def __get__(self, inst: None, owner: type) -> Endpoint: ...

    @overload
    def __get__(self, inst: object, owner: type) -> str: ...

    def __get__(self, inst: Any, owner: Any) -> Endpoint | str:
        if inst is None:
            return self  # Allow class-level access to .method
        return self.url(inst._base_url)


class PublicEndpoints:
    def __init__(self, base_url: str):
        self._base_url = base_url

    get_wallets_from_session_key = Endpoint("public", "get_wallets_from_session_key")
    order_quote = Endpoint("public", "order_quote")
    execute_quote_debug = Endpoint("public", "execute_quote_debug")
    send_quote_debug = Endpoint("public", "send_quote_debug")
    get_vault = Endpoint("public", "get_vault")
    get_vault_action_history = Endpoint("public", "get_vault_action_history")
    get_vault_performance_history = Endpoint("public", "get_vault_performance_history")
    get_vaults = Endpoint("public", "get_vaults")
    withdraw_debug = Endpoint("public", "withdraw_debug")
    get_onchain_action_history = Endpoint("public", "get_onchain_action_history")
    get_pending_deposits = Endpoint("public", "get_pending_deposits")
    register_deposit_address = Endpoint("public", "register_deposit_address")
    getRateLimits = Endpoint("public", "getRateLimits")
    get_time = Endpoint("public", "get_time")
    get_transaction = Endpoint("public", "get_transaction")
    get_all_currencies = Endpoint("public", "get_all_currencies")
    get_all_instruments = Endpoint("public", "get_all_instruments")
    get_all_live_instruments = Endpoint("public", "get_all_live_instruments")
    get_assets = Endpoint("public", "get_assets")
    get_currency = Endpoint("public", "get_currency")
    get_funding_rate_history = Endpoint("public", "get_funding_rate_history")
    get_index_chart_data = Endpoint("public", "get_index_chart_data")
    get_instrument = Endpoint("public", "get_instrument")
    get_interest_rate_history = Endpoint("public", "get_interest_rate_history")
    get_latest_signed_feeds = Endpoint("public", "get_latest_signed_feeds")
    get_option_settlement_prices = Endpoint("public", "get_option_settlement_prices")
    get_risk_universes = Endpoint("public", "get_risk_universes")
    get_ticker = Endpoint("public", "get_ticker")
    get_tickers = Endpoint("public", "get_tickers")
    get_trade_history = Endpoint("public", "get_trade_history")
    get_tradingview_chart_data = Endpoint("public", "get_tradingview_chart_data")
    get_all_referral_codes = Endpoint("public", "get_all_referral_codes")
    get_referral_performance = Endpoint("public", "get_referral_performance")
    start_auction = Endpoint("public", "start_auction")


class PrivateEndpoints:
    def __init__(self, base_url: str):
        self._base_url = base_url

    change_subaccount_label = Endpoint("private", "change_subaccount_label")
    get_all_portfolios = Endpoint("private", "get_all_portfolios")
    get_collaterals = Endpoint("private", "get_collaterals")
    get_positions = Endpoint("private", "get_positions")
    get_subaccount = Endpoint("private", "get_subaccount")
    get_subaccounts = Endpoint("private", "get_subaccounts")
    edit_session_key = Endpoint("private", "edit_session_key")
    session_keys = Endpoint("private", "session_keys")
    get_account = Endpoint("private", "get_account")
    cancel = Endpoint("private", "cancel")
    cancel_algo_order = Endpoint("private", "cancel_algo_order")
    cancel_all = Endpoint("private", "cancel_all")
    cancel_all_algo_orders = Endpoint("private", "cancel_all_algo_orders")
    cancel_all_trigger_orders = Endpoint("private", "cancel_all_trigger_orders")
    cancel_by_instrument = Endpoint("private", "cancel_by_instrument")
    cancel_by_label = Endpoint("private", "cancel_by_label")
    cancel_by_nonce = Endpoint("private", "cancel_by_nonce")
    cancel_trigger_order = Endpoint("private", "cancel_trigger_order")
    get_algo_orders = Endpoint("private", "get_algo_orders")
    get_open_orders = Endpoint("private", "get_open_orders")
    get_order = Endpoint("private", "get_order")
    get_trigger_orders = Endpoint("private", "get_trigger_orders")
    order = Endpoint("private", "order")
    order_debug = Endpoint("private", "order_debug")
    order_quote = Endpoint("private", "order_quote")
    replace = Endpoint("private", "replace")
    cancel_batch_quotes = Endpoint("private", "cancel_batch_quotes")
    cancel_batch_rfqs = Endpoint("private", "cancel_batch_rfqs")
    cancel_quote = Endpoint("private", "cancel_quote")
    cancel_rfq = Endpoint("private", "cancel_rfq")
    execute_quote = Endpoint("private", "execute_quote")
    get_quotes = Endpoint("private", "get_quotes")
    get_rfqs = Endpoint("private", "get_rfqs")
    poll_quotes = Endpoint("private", "poll_quotes")
    poll_rfqs = Endpoint("private", "poll_rfqs")
    replace_quote = Endpoint("private", "replace_quote")
    rfq_get_best_quote = Endpoint("private", "rfq_get_best_quote")
    send_quote = Endpoint("private", "send_quote")
    send_rfq = Endpoint("private", "send_rfq")
    cancel_all_vault_requests = Endpoint("private", "cancel_all_vault_requests")
    get_live_vault_requests = Endpoint("private", "get_live_vault_requests")
    get_shareholder_vaults = Endpoint("private", "get_shareholder_vaults")
    get_vault_request_history = Endpoint("private", "get_vault_request_history")
    get_vault_shares = Endpoint("private", "get_vault_shares")
    request_vault_deposit = Endpoint("private", "request_vault_deposit")
    request_vault_withdraw = Endpoint("private", "request_vault_withdraw")
    burn_vault_shares = Endpoint("private", "burn_vault_shares")
    create_vault = Endpoint("private", "create_vault")
    force_burn = Endpoint("private", "force_burn")
    get_curated_vaults = Endpoint("private", "get_curated_vaults")
    get_live_burn_requests = Endpoint("private", "get_live_burn_requests")
    get_live_mint_requests = Endpoint("private", "get_live_mint_requests")
    mint_vault_shares = Endpoint("private", "mint_vault_shares")
    reject_deposit_request = Endpoint("private", "reject_deposit_request")
    update_vault_info = Endpoint("private", "update_vault_info")
    get_deposit_history = Endpoint("private", "get_deposit_history")
    get_erc20_transfer_history = Endpoint("private", "get_erc20_transfer_history")
    get_funding_history = Endpoint("private", "get_funding_history")
    get_interest_history = Endpoint("private", "get_interest_history")
    get_option_settlement_history = Endpoint("private", "get_option_settlement_history")
    get_order_history = Endpoint("private", "get_order_history")
    get_trade_history = Endpoint("private", "get_trade_history")
    get_withdrawal_history = Endpoint("private", "get_withdrawal_history")
    get_mmp_config = Endpoint("private", "get_mmp_config")
    reset_mmp = Endpoint("private", "reset_mmp")
    set_mmp_config = Endpoint("private", "set_mmp_config")
    transfer_positions = Endpoint("private", "transfer_positions")
    transfer_spot = Endpoint("private", "transfer_spot")
    transfer_spot_external = Endpoint("private", "transfer_spot_external")
    update_whitelisted_recipients = Endpoint("private", "update_whitelisted_recipients")
    withdraw = Endpoint("private", "withdraw")
    liquidate = Endpoint("private", "liquidate")
    set_session_key = Endpoint("private", "set_session_key")
