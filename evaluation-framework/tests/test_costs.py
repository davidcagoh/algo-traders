from __future__ import annotations

import pandas as pd
import pytest

from evaluation.costs import (
    CostModel,
    apply_costs,
    breakeven_cost,
    cost_drag_summary,
    cost_grid,
    turnover,
)


@pytest.fixture
def trades() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "notional": [1000.0, 2000.0, 1500.0],
            "is_maker": [True, False, False],
            "open_time": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-05"], utc=True),
            "close_time": pd.to_datetime(
                ["2026-01-01 08:00", "2026-01-03 00:00", "2026-01-06 00:00"], utc=True
            ),
            "profit_abs": [10.0, -5.0, 20.0],
        }
    )


def test_zero_cost_model_is_identity(trades):
    model = CostModel(model_id="zero")
    priced = apply_costs(trades, model)
    assert (priced["net_profit_abs"] == priced["profit_abs"]).all()
    assert (priced["fee_cost"] == 0).all()
    assert (priced["funding_cost"] == 0).all()


def test_maker_taker_fees_applied_correctly(trades):
    model = CostModel(model_id="fees", maker_bps=1.0, taker_bps=5.0)
    priced = apply_costs(trades, model)
    assert priced["fee_cost"].iloc[0] == pytest.approx(1000.0 * 1.0 / 10_000)
    assert priced["fee_cost"].iloc[1] == pytest.approx(2000.0 * 5.0 / 10_000)


def test_funding_accrual_matches_hand_computation(trades):
    funding = pd.Series(
        [0.0001, 0.0001, 0.0001],
        index=pd.to_datetime(
            ["2026-01-01 00:00", "2026-01-01 08:00", "2026-01-02 00:00"], utc=True
        ),
    )
    model = CostModel(model_id="funding", funding_series=funding)
    priced = apply_costs(trades, model)
    # trade 0: open 2026-01-01 00:00, close 2026-01-01 08:00 -> only the
    # 00:00 funding event falls in [open, close)
    expected = 1000.0 * 0.0001
    assert priced["funding_cost"].iloc[0] == pytest.approx(expected)


def test_turnover_sums_absolute_notional(trades):
    assert turnover(trades) == pytest.approx(4500.0)


def test_cost_drag_summary_keys(trades):
    summary = cost_drag_summary(trades, CostModel(model_id="x", taker_bps=5.0))
    assert set(summary) == {
        "gross_profit",
        "net_profit",
        "fee_cost",
        "slippage_cost",
        "funding_cost",
        "turnover",
        "n_trades",
    }


def test_cost_grid_sorted_by_metric(trades):
    models = [
        CostModel(model_id="cheap", taker_bps=1.0),
        CostModel(model_id="expensive", taker_bps=50.0),
    ]
    grid = cost_grid(trades, models, metric="net_profit")
    assert grid.iloc[0].name == "cheap"


def test_cost_grid_unknown_metric_raises(trades):
    with pytest.raises(ValueError):
        cost_grid(trades, [CostModel(model_id="x")], metric="bogus")


def test_breakeven_cost_zero_for_losing_strategy():
    trades = pd.DataFrame(
        {
            "notional": [1000.0],
            "is_maker": [False],
            "open_time": pd.to_datetime(["2026-01-01"], utc=True),
            "close_time": pd.to_datetime(["2026-01-02"], utc=True),
            "profit_abs": [-10.0],
        }
    )
    assert breakeven_cost(trades) == 0.0


def test_breakeven_cost_recovers_injected_level():
    # gross profit 100 on 10,000 notional -> breakeven at 100 bps
    trades = pd.DataFrame(
        {
            "notional": [10_000.0],
            "is_maker": [False],
            "open_time": pd.to_datetime(["2026-01-01"], utc=True),
            "close_time": pd.to_datetime(["2026-01-02"], utc=True),
            "profit_abs": [100.0],
        }
    )
    be = breakeven_cost(trades, max_bps=500.0, steps=5001)
    assert be == pytest.approx(100.0, abs=1.0)


def test_breakeven_cost_never_exceeds_max_bps():
    trades = pd.DataFrame(
        {
            "notional": [1.0],
            "is_maker": [False],
            "open_time": pd.to_datetime(["2026-01-01"], utc=True),
            "close_time": pd.to_datetime(["2026-01-02"], utc=True),
            "profit_abs": [1_000_000.0],
        }
    )
    assert breakeven_cost(trades, max_bps=500.0, steps=10) == 500.0
