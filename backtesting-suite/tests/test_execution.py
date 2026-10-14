from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from backtesting_suite.config import (
    ConstraintConfig,
    CostConfig,
    ExecutionConfig,
)
from backtesting_suite.data import DataBundle
from backtesting_suite.execution.bar import BarExecutionModel, ExecutionError


def target(bundle: DataBundle, value: float) -> pd.DataFrame:
    return pd.DataFrame(value, index=bundle.index, columns=bundle.symbols)


def test_one_bar_delay_executes_at_next_open(daily_bundle: DataBundle) -> None:
    result = BarExecutionModel().simulate(
        daily_bundle,
        target(daily_bundle, 1.0),
        ExecutionConfig(signal_delay_bars=1, initial_cash=100.0, funding=False),
    )
    assert result.equity.iloc[1] == 100.0
    assert result.equity.iloc[2] == pytest.approx(110.0)
    assert result.executed_weights.iloc[0, 0] == 0.0
    assert result.executed_weights.iloc[1, 0] == 1.0


def test_proportional_cost_is_charged_before_market_return(daily_bundle: DataBundle) -> None:
    config = ExecutionConfig(
        signal_delay_bars=0,
        initial_cash=100.0,
        funding=False,
        transaction_costs=(CostConfig(type="proportional", name="fee", bps=100),),
    )
    result = BarExecutionModel().simulate(daily_bundle, target(daily_bundle, 1.0), config)
    assert result.costs.iloc[0]["fee"] == pytest.approx(1.0)
    assert result.equity.iloc[1] == pytest.approx(108.9)
    assert result.returns.iloc[0]["net_return"] == pytest.approx(0.089)


def test_positive_funding_is_paid_by_longs_and_received_by_shorts(
    daily_bundle: DataBundle,
) -> None:
    flat_fields = {name: frame.copy() for name, frame in daily_bundle.fields.items()}
    for name in ("open", "high", "low", "close"):
        flat_fields[name].loc[:, "BTC"] = 100.0
    funding = daily_bundle.funding.copy()
    funding.iloc[0, 0] = 0.01
    bundle = DataBundle(fields=flat_fields, funding=funding)
    config = ExecutionConfig(signal_delay_bars=0, initial_cash=100.0, funding=True)
    long_result = BarExecutionModel().simulate(bundle, target(bundle, 1.0), config)
    short_result = BarExecutionModel().simulate(bundle, target(bundle, -1.0), config)
    assert long_result.equity.iloc[1] == pytest.approx(99.0)
    assert short_result.equity.iloc[1] == pytest.approx(101.0)


def test_short_borrow_is_separate_from_strategy(daily_bundle: DataBundle) -> None:
    flat_fields = {name: frame.copy() for name, frame in daily_bundle.fields.items()}
    for name in ("open", "high", "low", "close"):
        flat_fields[name].loc[:, "BTC"] = 100.0
    bundle = DataBundle(fields=flat_fields, funding=daily_bundle.funding)
    config = ExecutionConfig(
        signal_delay_bars=0,
        initial_cash=100.0,
        funding=False,
        annual_borrow_bps=36_500,
    )
    result = BarExecutionModel().simulate(bundle, target(bundle, -1.0), config)
    assert result.costs.iloc[0]["borrow_cost"] == pytest.approx(1.0)
    assert result.equity.iloc[1] == pytest.approx(99.0)


def test_constraint_violation_can_raise_or_scale(daily_bundle: DataBundle) -> None:
    aggressive = target(daily_bundle, 2.0)
    with pytest.raises(ExecutionError, match="constraint violation"):
        BarExecutionModel().simulate(daily_bundle, aggressive, ExecutionConfig(signal_delay_bars=0))
    scaling = ConstraintConfig(
        max_gross_exposure=1.0,
        max_net_exposure=1.0,
        max_abs_weight=1.0,
        violation="scale",
    )
    config = replace(ExecutionConfig(signal_delay_bars=0), constraints=scaling)
    result = BarExecutionModel().simulate(daily_bundle, aggressive, config)
    assert result.executed_weights.iloc[0, 0] == pytest.approx(1.0)


def test_target_change_policy_does_not_restore_drifted_short_weight(
    daily_bundle: DataBundle,
) -> None:
    config = ExecutionConfig(
        signal_delay_bars=0,
        rebalance_policy="target_change",
        initial_cash=100.0,
        funding=False,
    )
    result = BarExecutionModel().simulate(daily_bundle, target(daily_bundle, -1.0), config)
    assert len(result.trades) == 1
    assert result.executed_weights.iloc[1, 0] == pytest.approx(
        result.ending_weights.iloc[0, 0]
    )


def test_required_missing_price_fails_closed(daily_bundle: DataBundle) -> None:
    broken = {name: frame.copy() for name, frame in daily_bundle.fields.items()}
    broken["open"].iloc[1, 0] = float("nan")
    bundle = DataBundle(fields=broken, funding=daily_bundle.funding)
    with pytest.raises(ExecutionError, match="missing open price"):
        BarExecutionModel().simulate(
            bundle,
            target(bundle, 1.0),
            ExecutionConfig(signal_delay_bars=0),
        )


def test_zero_return_policy_still_refuses_a_fill_without_a_price(
    daily_bundle: DataBundle,
) -> None:
    broken = {name: frame.copy() for name, frame in daily_bundle.fields.items()}
    broken["open"].iloc[1, 0] = float("nan")
    bundle = DataBundle(fields=broken, funding=daily_bundle.funding)
    targets = target(bundle, 0.0)
    targets.iloc[1:, 0] = 1.0
    with pytest.raises(ExecutionError, match="cannot fill at missing open price"):
        BarExecutionModel().simulate(
            bundle,
            targets,
            ExecutionConfig(signal_delay_bars=0, missing_price_policy="zero_return"),
        )
