"""ERC-20 contract helpers."""

from __future__ import annotations

import json

from web3 import Web3
from web3.contract.contract import Contract
from web3.types import TxParams

from derive_client._web3.tx import prepare_transaction
from derive_client.config import ABI_DATA_DIR
from derive_client.data_types import ChecksumAddress, GasPriority, LoggerType
from derive_client.exceptions import InsufficientTokenBalance


def get_erc20_contract(w3: Web3, token_address: ChecksumAddress) -> Contract:
    abi = json.loads((ABI_DATA_DIR / "erc20.json").read_text())
    return w3.eth.contract(address=token_address, abi=abi)


def get_balance(w3: Web3, *, token_address: ChecksumAddress, owner: ChecksumAddress) -> int:
    return get_erc20_contract(w3, token_address).functions.balanceOf(owner).call()


def get_allowance(w3: Web3, *, token_address: ChecksumAddress, owner: ChecksumAddress, spender: ChecksumAddress) -> int:
    return get_erc20_contract(w3, token_address).functions.allowance(owner, spender).call()


def ensure_sufficient_balance(w3: Web3, *, token_address: ChecksumAddress, owner: ChecksumAddress, amount: int) -> None:
    """Raises InsufficientTokenBalance with the actual numbers attached,
    rather than letting deposit() revert TokenTransferFailed with none."""

    balance = get_balance(w3, token_address=token_address, owner=owner)
    if balance < amount:
        raise InsufficientTokenBalance(
            f"{owner} holds {balance} of {token_address}, needs {amount} ({balance / amount * 100:.2f}% of required)."
        )


def prepare_approve(
    w3: Web3,
    *,
    token_address: ChecksumAddress,
    spender: ChecksumAddress,
    amount: int,
    from_address: ChecksumAddress,
    logger: LoggerType,
    approve_amount: int | None = None,
    gas_priority: GasPriority = GasPriority.MEDIUM,
) -> TxParams:
    """Unsigned approve() tx, or None if the current allowance already covers amount.

    approve_amount lets you approve more than this one call needs
    to cover several future deposits without re-approving each time.
    """

    current_allowance = get_allowance(w3, token_address=token_address, owner=from_address, spender=spender)
    if current_allowance >= amount:
        logger.info(f"Allowance {current_allowance} already covers {amount}, skipping approve()")
        return None

    func = get_erc20_contract(w3, token_address).functions.approve(spender, approve_amount or amount)
    return prepare_transaction(func, w3=w3, from_address=from_address, logger=logger, gas_priority=gas_priority)
