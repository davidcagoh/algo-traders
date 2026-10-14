"""Evaluation-package adapter and stable research report renderer."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backtesting_suite.config import RunConfig
from backtesting_suite.data import DataBundle
from backtesting_suite.result import BacktestResult


def annualisation_for(timeframe: str) -> float:
    unit = timeframe[-1].lower()
    amount = int(timeframe[:-1])
    per_day = {"m": 1_440, "h": 24, "d": 1}.get(unit)
    if per_day is None or amount <= 0:
        raise ValueError(f"unsupported timeframe {timeframe!r}")
    return 365.0 * per_day / amount


def _json_number(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def _metric_dict(metrics: Any) -> dict[str, Any]:
    return {
        key: (_json_number(value) if isinstance(value, float) else value)
        for key, value in asdict(metrics).items()
    }


def _timeframe_label(markdown: str, timeframe: str) -> str:
    return markdown.replace("_N_obs (daily):", f"_N_obs ({timeframe} bars):")


def build_summary(
    config: RunConfig, data: DataBundle, result: BacktestResult
) -> tuple[dict[str, Any], str]:
    try:
        from evaluation import (
            buy_and_hold,
            compute,
            excess_metrics,
            format_benchmark_table,
            format_markdown_table,
            format_markdown_table_with_ci,
            label_regimes,
            metrics_with_ci,
            regime_metrics,
        )
    except ImportError as exc:
        raise RuntimeError(
            "evaluation package is required; run `pip install -e evaluation-framework`"
        ) from exc

    annualisation = annualisation_for(config.data.timeframe)
    wallet = result.equity
    metrics = compute(wallet, annualisation=annualisation)
    summary: dict[str, Any] = {
        "experiment": config.experiment,
        "strategy": config.strategy.import_path,
        "profile": config.evaluation.profile,
        "window": {"start": wallet.index.min().isoformat(), "end": wallet.index.max().isoformat()},
        "dataset": data.metadata,
        "metrics": _metric_dict(metrics),
        "execution": {
            "initial_equity": float(wallet.iloc[0]),
            "final_equity": float(wallet.iloc[-1]),
            "total_return_pct": float((wallet.iloc[-1] / wallet.iloc[0] - 1.0) * 100.0),
            "total_turnover": float(result.turnover.sum()),
            "fills": int(len(result.trades)),
            "transaction_cost": float(result.costs.get("transaction_cost", pd.Series(dtype=float)).sum()),
            "funding_pnl": float(result.costs.get("funding_pnl", pd.Series(dtype=float)).sum()),
            "borrow_cost": float(result.costs.get("borrow_cost", pd.Series(dtype=float)).sum()),
            "cost_components": {
                name: float(result.costs[name].sum())
                for name in result.metadata.get("cost_components", [])
            },
            "average_gross_exposure": float(result.executed_weights.abs().sum(axis=1).mean()),
            "average_net_exposure": float(result.executed_weights.sum(axis=1).mean()),
        },
    }
    sections = [
        f"# Backtest report — {config.experiment}",
        "",
        _timeframe_label(format_markdown_table(metrics), config.data.timeframe),
    ]

    if config.evaluation.bootstrap_samples > 0:
        _, intervals = metrics_with_ci(
            wallet,
            annualisation=annualisation,
            n_boot=config.evaluation.bootstrap_samples,
            seed=7,
        )
        summary["bootstrap_ci"] = {
            name: {
                "point": _json_number(interval.point),
                "lower": _json_number(interval.lower),
                "upper": _json_number(interval.upper),
                "method": interval.method,
                "n_boot": interval.n_boot,
            }
            for name, interval in intervals.items()
        }
        sections = [
            f"# Backtest report — {config.experiment}",
            "",
            _timeframe_label(
                format_markdown_table_with_ci(metrics, intervals),
                config.data.timeframe,
            ),
        ]

    benchmark_symbol = config.evaluation.benchmark
    if benchmark_symbol:
        if benchmark_symbol not in data.symbols:
            raise ValueError(f"benchmark {benchmark_symbol!r} is not in the data universe")
        prices = data.field(config.execution.price_field)[[benchmark_symbol]].dropna()
        benchmark = buy_and_hold(prices) * (wallet.iloc[0] / 100.0)
        benchmark = benchmark.reindex(wallet.index).ffill().dropna()
        strategy_aligned = wallet.reindex(benchmark.index)
        excess = excess_metrics(strategy_aligned, benchmark, annualisation)
        summary["benchmark"] = {"symbol": benchmark_symbol, **_metric_dict(excess)}
        sections.extend(["", format_benchmark_table(excess, benchmark_symbol)])

        if config.evaluation.regimes:
            labels = label_regimes(prices[benchmark_symbol])
            by_regime = regime_metrics(wallet, labels, annualisation)
            summary["regimes"] = {
                label: _metric_dict(regime) for label, regime in by_regime.items()
            }
            sections.extend(
                [
                    "",
                    "### Regime decomposition",
                    "",
                    f"Regimes use {benchmark_symbol} drawdowns: bear is 10% or more below its running peak.",
                    "",
                    "| Regime | Bars | CAGR | Sharpe | Calmar | MDD |",
                    "|---|---:|---:|---:|---:|---:|",
                ]
            )
            for label, regime in by_regime.items():
                sections.append(
                    f"| {label} | {regime.n_obs} | {regime.cagr_pct:+.2f}% | "
                    f"{regime.sharpe:.3f} | {regime.calmar:.2f} | {regime.mdd_pct:.2f}% |"
                )

    execution = summary["execution"]
    execution_rows = [
            "",
            "## Execution",
            "",
            "| Measure | Value |",
            "|---|---:|",
            f"| Initial equity | {execution['initial_equity']:.2f} |",
            f"| Final equity | {execution['final_equity']:.2f} |",
            f"| Total return | {execution['total_return_pct']:.2f}% |",
            f"| Total turnover | {execution['total_turnover']:.3f} |",
            f"| Fills | {execution['fills']} |",
            f"| Transaction costs | {execution['transaction_cost']:.2f} |",
    ]
    execution_rows.extend(
        f"| └ {name} | {value:.2f} |"
        for name, value in execution["cost_components"].items()
    )
    execution_rows.extend(
        [
            f"| Funding P&L | {execution['funding_pnl']:.2f} |",
            f"| Borrow cost | {execution['borrow_cost']:.2f} |",
            f"| Average gross exposure | {execution['average_gross_exposure']:.3f} |",
            f"| Average net exposure | {execution['average_net_exposure']:.3f} |",
        ]
    )
    sections.extend(execution_rows)
    if config.notes:
        sections.extend(["", "## Notes", "", config.notes])
    return summary, "\n".join(sections).rstrip() + "\n"


def write_report(directory: Path, summary: dict[str, Any], markdown: str) -> None:
    (directory / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    (directory / "report.md").write_text(markdown)
