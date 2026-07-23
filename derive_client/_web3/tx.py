from __future__ import annotations

import statistics
import time
from typing import cast

from eth_typing import ChecksumAddress as EthChecksumAddress
from eth_typing import HexStr
from web3 import Web3
from web3.contract.contract import ContractFunction
from web3.exceptions import TransactionNotFound
from web3.types import TxParams

from derive_client.config import GAS_FEE_BUFFER, MIN_PRIORITY_FEE
from derive_client.data_types import (
    ChecksumAddress,
    FeeEstimate,
    FeeEstimates,
    FeeHistory,
    GasPriority,
    LoggerType,
    TxHash,
    TypedSignedTransaction,
    TypedTransaction,
    TypedTxReceipt,
    Wei,
)
from derive_client.exceptions import (
    FinalityTimeout,
    InsufficientNativeBalance,
    TransactionDropped,
    TxPendingTimeout,
)


def estimate_fees(w3: Web3, blocks: int = 20) -> FeeEstimates:
    """Estimate EIP-1559 maxFeePerGas and maxPriorityFeePerGas from recent blocks for GasPriority percentiles."""

    percentiles = tuple(map(int, GasPriority))
    raw_fee_history = w3.eth.fee_history(blocks, "pending", list(percentiles))
    # web3.types.Wei and our own Wei are both int-based but nominally
    # distinct NewTypes -- cast at this one boundary rather than fight it
    # field-by-field.
    fee_history = FeeHistory(**cast(dict, raw_fee_history))
    latest_base_fee = fee_history.base_fee_per_gas[-1]

    percentile_rewards: dict[int, list[Wei]] = {p: [] for p in percentiles}
    for block_rewards in fee_history.reward:
        for percentile, reward in zip(percentiles, block_rewards):
            percentile_rewards[percentile].append(reward)

    estimates = {}
    for percentile in percentiles:
        rewards = percentile_rewards[percentile]
        non_zero_rewards = list(filter(lambda x: x, rewards))
        estimated_priority_fee = int(statistics.median(non_zero_rewards)) if non_zero_rewards else MIN_PRIORITY_FEE

        buffered_base_fee = int(latest_base_fee * GAS_FEE_BUFFER)
        estimated_max_fee = buffered_base_fee + estimated_priority_fee
        estimates[GasPriority(percentile)] = FeeEstimate(estimated_max_fee, estimated_priority_fee)

    return FeeEstimates(estimates)


def preflight_native_balance_check(
    w3: Web3,
    account_address: ChecksumAddress,
    fee_estimate: FeeEstimate,
    gas_limit: int,
    value: int,
) -> None:
    balance = w3.eth.get_balance(cast(EthChecksumAddress, account_address))
    max_cost = gas_limit * fee_estimate.max_fee_per_gas + value

    if balance < max_cost:
        raise InsufficientNativeBalance(
            f"Insufficient native balance: balance={balance}, required={max_cost} "
            f"({balance / max_cost * 100:.2f}% available; gas_limit={gas_limit}, value={value})",
            balance=balance,
            chain_id=w3.eth.chain_id,
            assumed_gas_limit=gas_limit,
            fee_estimate=fee_estimate,
        )


def prepare_transaction(
    func: ContractFunction,
    *,
    w3: Web3,
    from_address: ChecksumAddress,
    logger: LoggerType,
    value: int = 0,
    gas_priority: GasPriority = GasPriority.MEDIUM,
    gas_blocks: int = 30,
) -> TxParams:
    """Build, fee-estimate, balance-check and simulate a contract call.
    Returns the unsigned tx dict as-is (web3.py's own TxParams shape) --
    deliberately not re-wrapped in a derive_client type, since it's unconfirmed
    whether TypedTransaction's fields match a pre-sign build_transaction()
    output. (It IS confirmed to match the post-mine get_transaction()
    response -- see wait_for_finality below, which uses it there.)
    """

    nonce = w3.eth.get_transaction_count(cast(EthChecksumAddress, from_address))
    fee_estimates = estimate_fees(w3, blocks=gas_blocks)
    fee_estimate = fee_estimates[gas_priority]
    logger.info(f"Fee estimate [{gas_priority.name}]: {fee_estimate}")

    tx = func.build_transaction(
        cast(
            TxParams,
            {
                "from": from_address,
                "nonce": nonce,
                "maxFeePerGas": fee_estimate.max_fee_per_gas,
                "maxPriorityFeePerGas": fee_estimate.max_priority_fee_per_gas,
                "chainId": w3.eth.chain_id,
                "value": value,
            },
        )
    )

    gas_limit = tx.get("gas")
    if gas_limit is None:
        # build_transaction() always populates this via eth_estimateGas
        raise RuntimeError("build_transaction() did not return a 'gas' value, cannot preflight balance check.")

    preflight_native_balance_check(
        w3=w3, account_address=from_address, fee_estimate=fee_estimate, gas_limit=gas_limit, value=value
    )

    # Simulate against current state; raises with the revert reason if it would fail.
    w3.eth.call(tx)

    return tx


def sign_transaction(w3: Web3, tx: TxParams, private_key: str) -> TypedSignedTransaction:
    """Optional convenience for local-key signing. Not part of the required
    flow -- submit_transaction() only needs raw_transaction bytes, sourced
    however you like."""

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
    return TypedSignedTransaction(**signed_tx._asdict())


def submit_transaction(w3: Web3, signed_tx: TypedSignedTransaction) -> TxHash:
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return TxHash(tx_hash)


def wait_for_finality(
    w3: Web3,
    tx_hash: str,
    logger: LoggerType,
    finality_blocks: int = 10,
    timeout: float = 300.0,
    poll_interval: float = 1.0,
) -> TypedTxReceipt:
    """
    Wait until tx is mined and has `finality_blocks` confirmations.
    On timeout this raises one of:
      - FinalityTimeout: receipt exists but not enough confirmations
      - TxPendingTimeout: no receipt, but tx present and pending in mempool
      - TransactionDropped: no receipt and tx not known to node (likely dropped)

    Notes on reorgs and provider inconsistency:
      - A chain reorg can cause a previously-seen receipt to disappear (tx becomes "unmined").
        In that case the tx will often reappear as pending in the mempool (TxPendingTimeout),
        but it can also be dropped entirely (TransactionDropped) or re-mined later.
      - With rotating RPC providers you may observe receipts, tx entries, and block numbers
        from different nodes that disagree. This function classifies a timeout based on a
        single get_transaction probe and is intentionally conservative; callers should
        interpret exceptions as:
          * FinalityTimeout: node reports mined or we observed a receipt but not enough confirms:
            wait longer; invoke this function again.
          * TxPendingTimeout: node knows the tx and reports it pending:
            either wait/poll longer or resubmit (reuse the nonce to prevent duplication).
          * TransactionDropped: node has no record (likely dropped or node out-of-sync):
            either wait/poll longer or resubmit (reuse the nonce to prevent duplication).
    """

    block_number = -1
    tx_hash = cast(HexStr, tx_hash)
    start_time = time.monotonic()

    while True:
        try:
            raw_receipt = w3.eth.get_transaction_receipt(tx_hash)
            receipt = TypedTxReceipt.model_validate(raw_receipt)
        # receipt can disappear temporarily during reorgs, or if RPC provider is not synced
        except TransactionNotFound as exc:
            receipt = None
            logger.debug("No tx receipt for tx_hash=%s", tx_hash, extra={"exc": exc})

        # blockNumber can change as tx gets reorged into different blocks
        try:
            if receipt is not None:
                block_number = w3.eth.block_number
                if block_number >= receipt.blockNumber + finality_blocks:
                    return receipt
        except Exception as exc:
            msg = "Failed to fetch block_number trying to assess finality of tx_hash=%s"
            logger.debug(msg, tx_hash, extra={"exc": exc})

        if time.monotonic() - start_time > timeout:
            # 1) We have a receipt but did not reach required confirmations
            if receipt is not None:
                raise FinalityTimeout(
                    f"Timed out waiting for finality: tx={tx_hash!r}, timeout_s={timeout}, "
                    f"required confirmations={finality_blocks}."
                    f"\nreceipt_block={receipt.blockNumber!r}, current_block={block_number!r}.",
                    "\nAction: wait longer / poll for finality again.",
                )
            # 2) No receipt: check if tx is known to node (mempool) or dropped
            try:
                tx = TypedTransaction.model_validate(w3.eth.get_transaction(tx_hash))
            except Exception as exc:
                tx = None
                logger.debug("get_transaction probe failed for tx_hash=%s", tx_hash, extra={"exc": exc})

            # still pending in mempool
            if tx is not None and tx.blockNumber is None:
                raise TxPendingTimeout(
                    f"No receipt within timeout: tx={tx_hash!r}, timeout_s={timeout}.",
                    "\nNode reports transaction present and pending in mempool.",
                    "\nAction: either wait/poll longer or resubmit (reuse the nonce to prevent duplication).",
                )
            # node reports tx mined, but no receipt
            elif tx is not None:
                raise FinalityTimeout(
                    f"Timed out waiting for finality: tx={tx_hash!r}, timeout_s={timeout}, "
                    f"required confirmations={finality_blocks}."
                    f"\nNode reports tx mined at block {tx.blockNumber!r} but receipt not observed by this verifier."
                    "\nAction: wait longer / poll for finality again.",
                )
            # tx dropped or node no longer knows about it
            else:
                raise TransactionDropped(
                    f"Transaction not found after timeout: tx={tx_hash!r}, timeout_s={timeout}.",
                    "\nNode does not report a receipt or pending transaction (likely dropped).",
                    "\nAction: either wait/poll longer or resubmit (reuse the nonce to prevent duplication).",
                )

        logger.debug("Waiting for finality: tx=%s sleeping=%.1fs", tx_hash, poll_interval)
        time.sleep(poll_interval)
