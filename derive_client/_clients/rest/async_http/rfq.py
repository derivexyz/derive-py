"""RFQ management operations."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

import msgspec
from derive_action_signing import (
    RFQExecuteModuleData,
    RFQQuoteDetails,
    RFQQuoteModuleData,
)

from derive_client._clients.utils import sort_by_instrument_name
from derive_client.config import INT64_MAX
from derive_client.data_types.generated_models import (
    CancelBatchQuotesRequest,
    CancelBatchResult,
    CancelBatchRfqsRequest,
    CancelBatchRfqsResponse,
    CancelQuoteRequest,
    CancelRfqRequest,
    Direction,
    ExecuteQuoteRequest,
    GetQuotesRequest,
    GetRfqsRequest,
    LegUnpricedParams,
    PollQuotesRequest,
    PollRfqsRequest,
    PricedLegParamsAndResponse,
    Quote,
    QuoteExecuteResponse,
    QuoteGetResponse,
    QuotePollResponse,
    Rfq,
    RfqGetBestQuoteRequest,
    RfqGetBestQuoteResponse,
    RFQGetResponse,
    RFQPollResponse,
    SendQuoteRequest,
    SendRfqRequest,
)

if TYPE_CHECKING:
    from .subaccount import Subaccount


class RFQOperations:
    """High-level RFQ management operations."""

    def __init__(self, *, subaccount: Subaccount):
        """
        Initialize order operations.

        Args:
            subaccount: Subaccount instance providing access to auth, config, and APIs
        """
        self._subaccount = subaccount

    async def send_rfq(
        self,
        *,
        legs: list[LegUnpricedParams],
        counterparties: Optional[list[str]] = None,
        label: str = "",
        max_total_cost: Optional[Decimal] = None,
        min_total_cost: Optional[Decimal] = None,
        partial_fill_step: Decimal = Decimal("1"),
    ) -> Rfq:
        """Requests two-sided quotes from participating market makers."""

        subaccount_id = self._subaccount.id
        legs = sort_by_instrument_name(legs)

        params = SendRfqRequest(
            legs=legs,
            subaccount_id=subaccount_id,
            counterparties=counterparties if counterparties is not None else msgspec.UNSET,
            label=label,
            max_total_cost=max_total_cost,
            min_total_cost=min_total_cost,
            partial_fill_step=partial_fill_step,
        )
        result = await self._subaccount._private_api.rpc.send_rfq(params)
        return result

    async def get_rfqs(
        self,
        *,
        page: int = 1,
        page_size: int = 100,
        rfq_id: Optional[str] = None,
        status: Optional[str] = None,
        from_timestamp: int = 0,
        to_timestamp: int = INT64_MAX,
    ) -> RFQGetResponse:
        """Retrieves a list of RFQs matching filter criteria.

        Takers can use this to get their open RFQs, RFQ history, etc."""

        subaccount_id = self._subaccount.id
        params = GetRfqsRequest(
            subaccount_id=subaccount_id,
            from_timestamp=from_timestamp,
            page=page,
            page_size=page_size,
            rfq_id=rfq_id,
            status=status,
            to_timestamp=to_timestamp,
        )
        result = await self._subaccount._private_api.rpc.get_rfqs(params)
        return result

    async def cancel_rfq(self, *, rfq_id: str) -> str:
        """
        Cancels a single RFQ by id.

        v3 change: response is now the literal string "ok", not a Result object.
        """

        subaccount_id = self._subaccount.id
        params = CancelRfqRequest(rfq_id=rfq_id, subaccount_id=subaccount_id)
        result = await self._subaccount._private_api.rpc.cancel_rfq(params)
        return result

    async def cancel_batch_rfqs(
        self,
        *,
        label: Optional[str] = None,
        nonce: Optional[int] = None,
        rfq_id: Optional[str] = None,
    ) -> CancelBatchRfqsResponse:
        """Cancels RFQs given optional filters.

        If no filters are provided, all RFQs for the subaccount are cancelled.

        All filters are combined using `AND` logic, so mutually exclusive filters will
        result in no RFQs being cancelled.

        v3 change: response is now {cancelled_ids: list[str]}, not the previous shape.
        """

        subaccount_id = self._subaccount.id
        params = CancelBatchRfqsRequest(
            subaccount_id=subaccount_id,
            label=label,
            nonce=nonce,
            rfq_id=rfq_id,
        )
        result = await self._subaccount._private_api.rpc.cancel_batch_rfqs(params)
        return result

    async def poll_rfqs(
        self,
        *,
        from_timestamp: int = 0,
        page: int = 1,
        page_size: int = 100,
        rfq_id: Optional[str] = None,
        rfq_subaccount_id: Optional[int] = None,
        status: Optional[str] = None,
        to_timestamp: int = INT64_MAX,
    ) -> RFQPollResponse:
        """Retrieves a list of RFQs matching filter criteria.

        Market makers can use this to poll RFQs directed to them.
        """

        # requires authorization: Unauthorized as RFQ maker
        subaccount_id = self._subaccount.id
        params = PollRfqsRequest(
            subaccount_id=subaccount_id,
            from_timestamp=from_timestamp,
            page=page,
            page_size=page_size,
            rfq_id=rfq_id,
            rfq_subaccount_id=rfq_subaccount_id,
            status=status,
            to_timestamp=to_timestamp,
        )
        result = await self._subaccount._private_api.rpc.poll_rfqs(params)
        return result

    async def send_quote(
        self,
        *,
        direction: Direction,
        legs: list[PricedLegParamsAndResponse],
        rfq_id: str,
        max_fee: Decimal = Decimal("1000"),
        signature_expiry_sec: Optional[int] = None,
        nonce: Optional[int] = None,
        label: str = "",
        mmp: bool = False,
    ) -> Quote:
        """Sends a quote in response to an RFQ request.

        The legs supplied in the parameters must exactly match those in the RFQ.
        """

        subaccount_id = self._subaccount.id
        legs = sort_by_instrument_name(legs)

        module_address = self._subaccount._config.contracts.RFQ_MODULE

        rfq_legs = []
        for leg in legs:
            instrument = self._subaccount.markets._get_cached_instrument(instrument_name=leg.instrument_name)
            asset_address = instrument.base_asset_address
            sub_id = int(instrument.base_asset_sub_id)

            rfq_quote_details = RFQQuoteDetails(
                instrument_name=leg.instrument_name,
                direction=leg.direction.value,
                asset_address=asset_address,
                sub_id=sub_id,
                price=leg.price,
                amount=leg.amount,
            )
            rfq_legs.append(rfq_quote_details)

        module_data = RFQQuoteModuleData(
            global_direction=direction.value,
            max_fee=max_fee,
            legs=rfq_legs,
        )

        signed_action = self._subaccount.sign_action(
            nonce=nonce,
            module_address=module_address,
            module_data=module_data,
            signature_expiry_sec=signature_expiry_sec,
        )

        params = SendQuoteRequest(
            direction=direction,
            legs=legs,
            max_fee=max_fee,
            nonce=signed_action.nonce,
            rfq_id=rfq_id,
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
            subaccount_id=subaccount_id,
            label=label,
            mmp=mmp,
        )
        result = await self._subaccount._private_api.rpc.send_quote(params)
        return result

    async def cancel_quote(self, quote_id: str) -> Quote:
        """Cancels an open quote."""

        subaccount_id = self._subaccount.id
        params = CancelQuoteRequest(
            quote_id=quote_id,
            subaccount_id=subaccount_id,
        )
        result = await self._subaccount._private_api.rpc.cancel_quote(params)
        return result

    async def cancel_batch_quotes(
        self,
        *,
        label: Optional[str] = None,
        nonce: Optional[int] = None,
        quote_id: Optional[str] = None,
        rfq_id: Optional[str] = None,
    ) -> CancelBatchResult:
        """Cancels quotes given optional filters. If no filters are provided, all quotes by
        the subaccount are cancelled.

        All filters are combined using `AND` logic, so mutually exclusive filters will
        result in no quotes being cancelled.
        """

        subaccount_id = self._subaccount.id
        params = CancelBatchQuotesRequest(
            subaccount_id=subaccount_id,
            label=label,
            nonce=nonce,
            quote_id=quote_id,
            rfq_id=rfq_id,
        )
        result = await self._subaccount._private_api.rpc.cancel_batch_quotes(params)
        return result

    async def get_quotes(
        self,
        *,
        from_timestamp: int = 0,
        page: int = 1,
        page_size: int = 100,
        quote_id: Optional[str] = None,
        rfq_id: Optional[str] = None,
        status: Optional[str] = None,
        to_timestamp: int = INT64_MAX,
    ) -> QuoteGetResponse:
        """Retrieves a list of quotes matching filter criteria.

        Market makers can use this to get their open quotes, quote history, etc.
        """

        subaccount_id = self._subaccount.id
        params = GetQuotesRequest(
            subaccount_id=subaccount_id,
            from_timestamp=from_timestamp,
            page=page,
            page_size=page_size,
            quote_id=quote_id,
            rfq_id=rfq_id,
            status=status,
            to_timestamp=to_timestamp,
        )
        result = await self._subaccount._private_api.rpc.get_quotes(params)
        return result

    async def poll_quotes(
        self,
        *,
        from_timestamp: int = 0,
        page: int = 1,
        page_size: int = 100,
        quote_id: Optional[str] = None,
        rfq_id: Optional[str] = None,
        status: Optional[str] = None,
        to_timestamp: int = INT64_MAX,
    ) -> QuotePollResponse:
        """Retrieves a list of quotes matching filter criteria.

        Takers can use this to poll open quotes that they can fill against their open
        RFQs.
        """

        subaccount_id = self._subaccount.id
        params = PollQuotesRequest(
            subaccount_id=subaccount_id,
            from_timestamp=from_timestamp,
            page=page,
            page_size=page_size,
            quote_id=quote_id,
            rfq_id=rfq_id,
            status=status,
            to_timestamp=to_timestamp,
        )
        result = await self._subaccount._private_api.rpc.poll_quotes(params)
        return result

    async def execute_quote(
        self,
        *,
        direction: Direction,
        legs: list[PricedLegParamsAndResponse],
        quote_id: str,
        rfq_id: str,
        max_fee: Decimal = Decimal("1000"),
        label: str = "",
        signature_expiry_sec: Optional[int] = None,
        nonce: Optional[int] = None,
    ) -> QuoteExecuteResponse:
        """Executes a quote."""

        subaccount_id = self._subaccount.id
        legs = sort_by_instrument_name(legs)

        module_address = self._subaccount._config.contracts.RFQ_MODULE

        quote_legs = []
        for leg in legs:
            instrument = self._subaccount.markets._get_cached_instrument(instrument_name=leg.instrument_name)
            asset_address = instrument.base_asset_address
            sub_id = int(instrument.base_asset_sub_id)

            rfq_quote_details = RFQQuoteDetails(
                instrument_name=leg.instrument_name,
                direction=leg.direction.value,
                asset_address=asset_address,
                sub_id=sub_id,
                price=leg.price,
                amount=leg.amount,
            )
            quote_legs.append(rfq_quote_details)

        module_data = RFQExecuteModuleData(
            global_direction=direction.value,
            max_fee=max_fee,
            legs=quote_legs,
        )

        signed_action = self._subaccount.sign_action(
            nonce=nonce,
            module_address=module_address,
            module_data=module_data,
            signature_expiry_sec=signature_expiry_sec,
        )

        params = ExecuteQuoteRequest(
            subaccount_id=subaccount_id,
            direction=direction,
            legs=legs,
            max_fee=max_fee,
            nonce=signed_action.nonce,
            quote_id=quote_id,
            rfq_id=rfq_id,
            signature=signed_action.signature,
            signature_expiry_sec=signed_action.signature_expiry_sec,
            signer=signed_action.signer,
            label=label,
        )
        result = await self._subaccount._private_api.rpc.execute_quote(params)
        return result

    async def get_best_quote(
        self,
        legs: list[LegUnpricedParams],
        direction: Direction = Direction.buy,
    ) -> RfqGetBestQuoteResponse:
        """Performs a "dry run" on an RFQ, returning the estimated fee and whether the
        trade is expected to pass.

        Should any exception be raised in the process of evaluating the trade, a
        standard RPC error will be returned with the error details.
        """

        subaccount_id = self._subaccount.id
        legs = sort_by_instrument_name(legs)

        params = RfqGetBestQuoteRequest(
            legs=legs,
            subaccount_id=subaccount_id,
            direction=direction,
        )
        result = await self._subaccount._private_api.rpc.rfq_get_best_quote(params)
        return result
