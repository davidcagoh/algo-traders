from __future__ import annotations

from dataclasses import replace

from backtesting_suite.config import (
    DataConfig,
    EvaluationConfig,
    ExecutionConfig,
    RunConfig,
    StrategyConfig,
)
from backtesting_suite.dashboard import build_dashboard_html
from backtesting_suite.data import DataBundle
from backtesting_suite.execution.bar import BarExecutionModel


def test_dashboard_is_self_contained_and_handles_undefined_metrics(
    daily_bundle: DataBundle,
) -> None:
    config = RunConfig(
        experiment="dashboard_test",
        data=DataConfig(
            manifest="unused.json",
            market="spot",
            timeframe="1d",
            universe=("BTC",),
            start="2024-01-01",
            end="2024-01-04",
        ),
        strategy=StrategyConfig(import_path="example:Strategy"),
        execution=ExecutionConfig(funding=False),
        evaluation=EvaluationConfig(benchmark="BTC"),
    )
    targets = daily_bundle.field("close") * 0.0
    result = BarExecutionModel().simulate(daily_bundle, targets, config.execution)
    result.metadata["created_at"] = "2024-01-05T00:00:00+00:00"
    summary = {
        "window": {"start": "2024-01-01T00:00:00+00:00", "end": "2024-01-04T00:00:00+00:00"},
        "metrics": {
            "cagr_pct": 0.0,
            "sharpe": None,
            "calmar": None,
            "mdd_pct": 0.0,
        },
        "execution": {
            "total_return_pct": 0.0,
            "final_equity": 100_000.0,
            "total_turnover": 0.0,
            "transaction_cost": 0.0,
        },
    }

    html = build_dashboard_html(config, daily_bundle, result, summary)

    assert "<!doctype html>" in html
    assert "plotly.js" in html
    assert '<script src="https://cdn.plot.ly' not in html
    assert "Rolling risk statistics" in html
    assert "Equity and PnL over time" in html
    assert "Historical stress windows" in html
    assert "Portfolio weights" in html
    assert "Risk and path statistics" in html
    assert "Benchmark-regime stress" in html
    assert "n/a" in html


def test_dashboard_includes_long_position_weight(daily_bundle: DataBundle) -> None:
    execution = replace(ExecutionConfig(funding=False), signal_delay_bars=0)
    config = RunConfig(
        experiment="weight_test",
        data=DataConfig("unused.json", "spot", "1d", ("BTC",), "2024-01-01", "2024-01-04"),
        strategy=StrategyConfig(import_path="example:Strategy"),
        execution=execution,
    )
    targets = daily_bundle.field("close") * 0.0 + 1.0
    result = BarExecutionModel().simulate(daily_bundle, targets, execution)
    summary = {
        "window": {"start": "2024-01-01T00:00:00+00:00", "end": "2024-01-04T00:00:00+00:00"},
        "metrics": {"cagr_pct": 1.0, "sharpe": 1.0, "calmar": 1.0, "mdd_pct": 1.0},
        "execution": {
            "total_return_pct": 1.0,
            "final_equity": 101_000.0,
            "total_turnover": 1.0,
            "transaction_cost": 0.0,
        },
    }

    html = build_dashboard_html(config, daily_bundle, result, summary)

    assert "BTC" in html
    assert "Executed weight %" in html
