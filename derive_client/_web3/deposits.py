"""Direct on-chain deposits (OnchainActionManager.deposit / .depositToNewSubaccount)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal

from web3 import Web3
from web3.contract.contract import Contract
from web3.types import TxParams

from derive_client._web3.abi import ContractRegistry
from derive_client._web3.erc20 import ensure_sufficient_balance, prepare_approve
from derive_client._web3.tx import prepare_transaction, sign_transaction, submit_transaction
from derive_client._web3.tx import wait_for_finality as _wait_for_finality
from derive_client.data_types import (
    ChecksumAddress,
    GasPriority,
    LoggerType,
    MarginType,
    TxHash,
    TypedTxReceipt,
    UniverseType,
)
from derive_client.data_types.generated_models import RiskUniverse


@dataclass(frozen=True)
class ResolvedCollateral:
    manager_id: int
    protocol_asset_address: ChecksumAddress
    erc20_address: ChecksumAddress
    decimals: int
    min_deposit_usd: str  # deposits below this are donated to the security module, not credited


def resolve_manager_id(
    risk_universes: list[RiskUniverse], *, universe_type: UniverseType, margin_type: MarginType
) -> int:
    """(universe_type, margin_type) -> manager_id. Only needed when creating
    a NEW subaccount -- an existing one already carries manager_id directly
    on its own state, more precisely (globally unique, sidesteps
    margin_type being typed differently across models)."""

    risk_universe = next((ru for ru in risk_universes if ru.name == universe_type.value), None)
    if risk_universe is None:
        raise ValueError(
            f"No risk universe named {universe_type.value!r}. Known: {sorted(ru.name for ru in risk_universes)}"
        )

    manager = next((m for m in risk_universe.managers if m.margin_type == margin_type), None)
    if manager is None:
        known = sorted(m.margin_type for m in risk_universe.managers)
        raise ValueError(
            f"Universe {universe_type.value!r} has no manager with margin_type={margin_type}. Known: {known}"
        )

    return manager.manager_id


def resolve_collateral(risk_universes: list[RiskUniverse], *, manager_id: int, asset_name: str) -> ResolvedCollateral:
    """The one and only collateral-resolution code path. Both
    plan_new_subaccount and plan_deposit call this -- the former after
    resolve_manager_id(), the latter with a manager_id it already has."""

    manager = next((m for ru in risk_universes for m in ru.managers if m.manager_id == manager_id), None)
    if manager is None:
        known = sorted({m.manager_id for ru in risk_universes for m in ru.managers})
        raise ValueError(f"No manager with manager_id={manager_id}. Known: {known}")

    collateral = next((c for c in manager.collaterals if c.name == asset_name), None)
    if collateral is None:
        known = sorted(c.name for c in manager.collaterals)
        raise ValueError(f"No collateral {asset_name!r} for manager_id={manager_id}. Known: {known}")

    if not collateral.erc20.underlying_erc20:
        raise ValueError(
            f"{asset_name!r} for manager_id={manager_id} has no underlying_erc20 -- "
            "not depositable via the ERC-20 approve/deposit path."
        )

    return ResolvedCollateral(
        manager_id=manager.manager_id,
        protocol_asset_address=collateral.address,
        erc20_address=collateral.erc20.underlying_erc20,
        decimals=collateral.erc20.decimals,
        min_deposit_usd=collateral.min_deposit_usd,
    )


@dataclass
class DepositStep:
    kind: str  # "approve" | "deposit"
    description: str
    tx_params: TxParams

    _w3: Web3 = field(repr=False)
    _logger: LoggerType = field(repr=False)
    _private_key: str | None = field(default=None, repr=False)

    tx_hash: TxHash | None = field(default=None, init=False)
    receipt: TypedTxReceipt | None = field(default=None, init=False)

    def submit(self, private_key: str | None = None) -> TxHash:
        """Sign and broadcast. Returns tx_hash immediately, before finality
        is attempted -- keep it even if wait_for_finality() later times out.

        Defaults to the key the plan was built with; pass private_key
        explicitly to sign with something else."""

        key = private_key or self._private_key
        if key is None:
            raise ValueError("No private_key given and no default available -- pass one explicitly.")

        signed = sign_transaction(self._w3, self.tx_params, key)
        self.tx_hash = submit_transaction(self._w3, signed)
        return self.tx_hash

    def wait_for_finality(self, **kwargs) -> TypedTxReceipt:
        """Safe to call again after a timeout -- reuses the stored tx_hash,
        never resubmits. kwargs pass through to _web3.tx.wait_for_finality
        (finality_blocks, timeout, poll_interval)."""

        if self.tx_hash is None:
            raise RuntimeError("submit() hasn't been called yet -- nothing to wait for.")

        self.receipt = _wait_for_finality(self._w3, tx_hash=self.tx_hash, logger=self._logger, **kwargs)
        return self.receipt


class Deposits:
    """On-chain deposits into the Derive Protocol."""

    def __init__(self, registry: ContractRegistry, *, w3: Web3, logger: LoggerType):
        self._w3 = w3
        self._logger = logger
        self.contract: Contract = registry.get("ACTION_MANAGER")

    def prepare_deposit(
        self,
        *,
        from_address: ChecksumAddress,
        asset: ChecksumAddress,
        amount: int,
        subaccount_id: int,
        fallback_recipient: ChecksumAddress,
        gas_priority: GasPriority = GasPriority.MEDIUM,
    ) -> TxParams:
        """Fund an existing subaccount."""

        func = self.contract.functions.deposit(asset, amount, subaccount_id, fallback_recipient)
        return prepare_transaction(
            func, w3=self._w3, from_address=from_address, logger=self._logger, gas_priority=gas_priority
        )

    def prepare_deposit_to_new_subaccount(
        self,
        *,
        from_address: ChecksumAddress,
        asset: ChecksumAddress,
        amount: int,
        manager_id: int,
        owner: ChecksumAddress,
        gas_priority: GasPriority = GasPriority.MEDIUM,
    ) -> TxParams:
        """Create a NEW subaccount under manager_id, owned by owner."""

        func = self.contract.functions.depositToNewSubaccount(asset, amount, manager_id, owner)
        return prepare_transaction(
            func, w3=self._w3, from_address=from_address, logger=self._logger, gas_priority=gas_priority
        )

    def plan_new_subaccount(
        self,
        *,
        risk_universes: list[RiskUniverse],
        universe_type: UniverseType,
        margin_type: MarginType,
        asset_name: str,
        amount: Decimal,
        from_address: ChecksumAddress,
        owner: ChecksumAddress,
        private_key: str,
        gas_priority: GasPriority = GasPriority.MEDIUM,
    ) -> Iterator[DepositStep]:
        """Deposit `amount` of `asset_name` into a NEW subaccount under
        (universe, margin_type). Yields 1 or 2 DepositStep depending on
        whether an approve() is needed -- inspect .tx_params, then
        .submit(), then .wait_for_finality() on each."""

        manager_id = resolve_manager_id(risk_universes, universe_type=universe_type, margin_type=margin_type)
        collateral = resolve_collateral(risk_universes, manager_id=manager_id, asset_name=asset_name)
        native_amount = self._validate_and_scale(amount, collateral, asset_name)

        ensure_sufficient_balance(
            self._w3, token_address=collateral.erc20_address, owner=from_address, amount=native_amount
        )

        if approve_tx := prepare_approve(
            self._w3,
            token_address=collateral.erc20_address,
            spender=self.contract.address,
            amount=native_amount,
            from_address=from_address,
            logger=self._logger,
        ):
            yield self._step("approve", f"Approve {amount} {asset_name} for ACTION_MANAGER", approve_tx, private_key)

        deposit_tx = self.prepare_deposit_to_new_subaccount(
            from_address=from_address,
            asset=collateral.protocol_asset_address,
            amount=native_amount,
            manager_id=collateral.manager_id,
            owner=owner,
            gas_priority=gas_priority,
        )
        description = f"Deposit {amount} {asset_name} to a new {margin_type.value} subaccount in {universe_type.value}"
        yield self._step("deposit", description, deposit_tx, private_key)

    def plan_deposit(
        self,
        *,
        risk_universes: list[RiskUniverse],
        manager_id: int,
        subaccount_id: int,
        asset_name: str,
        amount: Decimal,
        from_address: ChecksumAddress,
        fallback_recipient: ChecksumAddress,
        private_key: str,
        gas_priority: GasPriority = GasPriority.MEDIUM,
    ) -> Iterator[DepositStep]:
        """Deposit `amount` of `asset_name` into an EXISTING subaccount.
        manager_id comes straight off the subaccount's own state
        (SubaccountState.manager_id) -- no universe_type/margin_type needed."""

        collateral = resolve_collateral(risk_universes, manager_id=manager_id, asset_name=asset_name)
        native_amount = self._validate_and_scale(amount, collateral, asset_name)

        ensure_sufficient_balance(
            self._w3, token_address=collateral.erc20_address, owner=from_address, amount=native_amount
        )

        if approve_tx := prepare_approve(
            self._w3,
            token_address=collateral.erc20_address,
            spender=self.contract.address,
            amount=native_amount,
            from_address=from_address,
            logger=self._logger,
        ):
            yield self._step("approve", f"Approve {amount} {asset_name} for ACTION_MANAGER", approve_tx, private_key)

        deposit_tx = self.prepare_deposit(
            from_address=from_address,
            asset=collateral.protocol_asset_address,
            amount=native_amount,
            subaccount_id=subaccount_id,
            fallback_recipient=fallback_recipient,
            gas_priority=gas_priority,
        )
        description = f"Deposit {amount} {asset_name} to subaccount {subaccount_id}"
        yield self._step("deposit", description, deposit_tx, private_key)

    def _validate_and_scale(self, amount: Decimal, collateral: ResolvedCollateral, asset_name: str) -> int:
        if amount < Decimal(collateral.min_deposit_usd):
            raise ValueError(
                f"{amount} {asset_name} is below the minimum deposit of {collateral.min_deposit_usd} "
                f"-- it would be donated to the security module, not credited to your subaccount."
            )
        return int(amount * 10**collateral.decimals)

    def _step(self, kind: str, description: str, tx_params: TxParams, private_key: str | None) -> DepositStep:
        return DepositStep(
            kind=kind,
            description=description,
            tx_params=tx_params,
            _w3=self._w3,
            _logger=self._logger,
            _private_key=private_key,
        )
