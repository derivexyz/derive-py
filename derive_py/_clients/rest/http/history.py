"""Historical record operations, scoped to a single subaccount or an entire wallet."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from derive_py._clients.utils import unset_if_none
from derive_py.data_types import ChecksumAddress
from derive_py.data_types.generated_models import (
    DepositHistoryResult,
    GetDepositHistoryRequest,
    GetErc20TransferHistoryRequest,
    GetFundingHistoryRequest,
    GetInterestHistoryRequest,
    GetOptionSettlementHistoryParams,
    GetOrderHistoryRequest,
    GetTradeHistoryRequest,
    GetWithdrawalHistoryRequest,
    InterestHistoryResult,
    OptionSettlementHistoryResponse,
    PaginatedOrdersResult,
    PaginatedTradesResult,
    PerpSettlementHistoryResponse,
    TransferHistoryResult,
    WithdrawalHistoryResult,
)

if TYPE_CHECKING:
    from derive_py._clients.rest.http.account import LightAccount
    from derive_py._clients.rest.http.api import PrivateAPI

    from .subaccount import Subaccount


#: Endpoints without a pagination envelope truncate silently at this many rows.
HISTORY_ROW_CAP = 1000


class HistoryOperations:
    """Settled historical records for a single subaccount or for a whole wallet."""

    def __init__(
        self,
        *,
        private_api: PrivateAPI,
        wallet: Optional[ChecksumAddress] = None,
        subaccount_id: Optional[int] = None,
    ):
        """
        Initialize history operations (internal use - use the alternate
        constructors `for_wallet()` / `for_subaccount()` instead).

        Args:
            private_api: Private API interface for authenticated requests
            wallet: Wallet address, for wallet-wide history
            subaccount_id: Subaccount ID, for single-subaccount history

        Raises:
            ValueError: If neither or both of wallet and subaccount_id are given
        """

        if (wallet is None) == (subaccount_id is None):
            msg = (
                "HistoryOperations requires exactly one of wallet or subaccount_id; "
                f"got wallet={wallet!r}, subaccount_id={subaccount_id!r}"
            )
            raise ValueError(msg)

        self._private_api = private_api
        self._wallet = wallet
        self._subaccount_id = subaccount_id

    @classmethod
    def for_wallet(cls, account: LightAccount) -> HistoryOperations:
        """Build wallet-scoped history operations. Returns records across every
        subaccount owned by the wallet."""

        return cls(private_api=account._private_api, wallet=account.address)

    @classmethod
    def for_subaccount(cls, subaccount: Subaccount) -> HistoryOperations:
        """Build subaccount-scoped history operations. Returns records for that
        one subaccount only."""

        return cls(private_api=subaccount._private_api, subaccount_id=subaccount.id)

    @property
    def wallet(self) -> Optional[ChecksumAddress]:
        """Wallet this instance is scoped to, or None if scoped to a subaccount."""

        return self._wallet

    @property
    def subaccount_id(self) -> Optional[int]:
        """Subaccount this instance is scoped to, or None if scoped to a wallet."""

        return self._subaccount_id

    @property
    def scope(self) -> str:
        """Human-readable scope, e.g. `wallet=0xabc...` or `subaccount_id=1234`."""

        if self._wallet is not None:
            return f"wallet={self._wallet}"
        return f"subaccount_id={self._subaccount_id}"

    def deposits(
        self,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
    ) -> DepositHistoryResult:
        """Settled deposits. Each entry reports the gross amount and the security
        module fee; the net credited amount is amount minus fee.

        Not paginated: results are capped at HISTORY_ROW_CAP rows and truncate
        silently. Narrow the timestamp window if the cap is reached.
        """

        params = GetDepositHistoryRequest(
            wallet=unset_if_none(self._wallet),
            subaccount_id=unset_if_none(self._subaccount_id),
            start_timestamp=unset_if_none(start_timestamp),
            end_timestamp=unset_if_none(end_timestamp),
        )
        result = self._private_api.rpc.get_deposit_history(params)
        return result

    def withdrawals(
        self,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
    ) -> WithdrawalHistoryResult:
        """Settled withdrawals. Each entry reports the gross amount and the
        security module fee; the net amount sent to the recipient is amount minus
        fee.

        Not paginated: results truncate silently at HISTORY_ROW_CAP rows.
        """

        params = GetWithdrawalHistoryRequest(
            wallet=unset_if_none(self._wallet),
            subaccount_id=unset_if_none(self._subaccount_id),
            start_timestamp=unset_if_none(start_timestamp),
            end_timestamp=unset_if_none(end_timestamp),
        )
        result = self._private_api.rpc.get_withdrawal_history(params)
        return result

    def erc20_transfers(
        self,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
    ) -> TransferHistoryResult:
        """Settled spot (ERC-20) transfers. Amounts are directional: the sender
        sees the gross amount plus fee, the receiver sees the net credit.

        Not paginated: results truncate silently at HISTORY_ROW_CAP rows.
        """

        params = GetErc20TransferHistoryRequest(
            wallet=unset_if_none(self._wallet),
            subaccount_id=unset_if_none(self._subaccount_id),
            start_timestamp=unset_if_none(start_timestamp),
            end_timestamp=unset_if_none(end_timestamp),
        )
        result = self._private_api.rpc.get_erc20_transfer_history(params)
        return result

    def interest(
        self,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
    ) -> InterestHistoryResult:
        """Realized interest settlements. A negative value was paid (borrowed),
        a positive value was received (supplied).

        Not paginated: results truncate silently at HISTORY_ROW_CAP rows.
        """

        params = GetInterestHistoryRequest(
            wallet=unset_if_none(self._wallet),
            subaccount_id=unset_if_none(self._subaccount_id),
            start_timestamp=unset_if_none(start_timestamp),
            end_timestamp=unset_if_none(end_timestamp),
        )
        result = self._private_api.rpc.get_interest_history(params)
        return result

    def option_settlements(self) -> OptionSettlementHistoryResponse:
        """Option settlement (expiry) events, with the reconstructed instrument
        name and settled amounts per expired position.

        Takes no time window: this endpoint has no timestamp filter.
        """

        params = GetOptionSettlementHistoryParams(
            wallet=unset_if_none(self._wallet),
            subaccount_id=unset_if_none(self._subaccount_id),
        )
        result = self._private_api.rpc.get_option_settlement_history(params)
        return result

    def funding(
        self,
        instrument_name: Optional[str] = None,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> PerpSettlementHistoryResponse:
        """Perpetual funding (settlement) events, optionally filtered to one
        perpetual instrument. Paginated: read `pagination` off the result."""

        params = GetFundingHistoryRequest(
            wallet=unset_if_none(self._wallet),
            subaccount_id=unset_if_none(self._subaccount_id),
            instrument_name=unset_if_none(instrument_name),
            start_timestamp=unset_if_none(start_timestamp),
            end_timestamp=unset_if_none(end_timestamp),
            page=page,
            page_size=page_size,
        )
        result = self._private_api.rpc.get_funding_history(params)
        return result

    def orders(
        self,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> PaginatedOrdersResult:
        """Terminal orders (filled, cancelled, expired), one record per order.
        Live trigger and algo orders are not here: read those from
        `orders.get_trigger_orders()` and `orders.get_algo_orders()`.

        Paginated: read `pagination` off the result.
        """

        params = GetOrderHistoryRequest(
            wallet=unset_if_none(self._wallet),
            subaccount_id=unset_if_none(self._subaccount_id),
            from_timestamp=unset_if_none(start_timestamp),
            to_timestamp=unset_if_none(end_timestamp),
            page=page,
            page_size=page_size,
        )
        result = self._private_api.rpc.get_order_history(params)
        return result

    def trades(
        self,
        instrument_name: Optional[str] = None,
        order_id: Optional[str] = None,
        quote_id: Optional[str] = None,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> PaginatedTradesResult:
        """Executed trades for this scope. This is your own fill history; for the
        anonymised public tape see `markets.trades()`.

        Paginated: read `pagination` off the result.
        """

        params = GetTradeHistoryRequest(
            wallet=unset_if_none(self._wallet),
            subaccount_id=unset_if_none(self._subaccount_id),
            instrument_name=unset_if_none(instrument_name),
            order_id=unset_if_none(order_id),
            quote_id=unset_if_none(quote_id),
            from_timestamp=unset_if_none(start_timestamp),
            to_timestamp=unset_if_none(end_timestamp),
            page=page,
            page_size=page_size,
        )
        result = self._private_api.rpc.get_trade_history(params)
        return result

    def __repr__(self) -> str:
        return f"<{self.__class__.__qualname__}({self.scope}) object at {hex(id(self))}>"
