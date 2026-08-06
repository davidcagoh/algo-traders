"""Benchmark and peer comparison.

Literature: Liu 2026, *Evaluating Structured Strategy Backtests*
(`../literature/strategy-evaluation/empirical-audits/2604.18821-backtest-regime-live-performance.pdf`,
1,726 commercial strategies) — measures live/backtest decay relative to
peer and external benchmarks, not just against zero return. This project's
own leaderboard already concedes "long-only trend strategies will
underperform buy-and-hold in strong bulls"
(`../freqtrade-experiment/hmm-slope-experiment/research/_index.md`) but had
no benchmark column to make that comparison a first-class number.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from evaluation.layers import DEFAULT_ANNUAL, cagr, sharpe


def buy_and_hold(prices: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.Series:
    """Wallet curve for a static buy-and-hold basket of `prices` columns."""
    cols = list(prices.columns)
    w = weights or {c: 1.0 / len(cols) for c in cols}
    normed = prices / prices.iloc[0]
    weighted = sum(normed[c] * w.get(c, 0.0) for c in cols)
    return 100.0 * weighted


def peer_benchmark(returns_matrix: pd.DataFrame, weights: str = "equal") -> pd.Series:
    """Wallet curve (starting at 100) for an equal-weight peer strategy
    basket, from a (period x strategy) per-period returns matrix."""
    if weights != "equal":
        raise ValueError(f"unsupported weights scheme: {weights!r}")
    if returns_matrix.shape[1] == 0:
        return pd.Series(dtype=float)
    combined = returns_matrix.mean(axis=1)
    levels = 100.0 * np.cumprod(1.0 + combined.to_numpy())
    return pd.Series(levels, index=returns_matrix.index)


@dataclass(frozen=True)
class ExcessMetrics:
    excess_cagr_pct: float
    excess_sharpe: float
    information_ratio: float
    up_capture: float
    down_capture: float


def excess_metrics(
    strategy: pd.Series, benchmark: pd.Series, annualisation: float = DEFAULT_ANNUAL
) -> ExcessMetrics:
    """Strategy performance relative to a benchmark wallet curve."""
    s_ret = strategy.pct_change().dropna()
    b_ret = benchmark.pct_change().dropna()
    aligned = pd.concat([s_ret, b_ret], axis=1, join="inner")
    aligned.columns = ["s", "b"]

    excess_cagr = (cagr(strategy, annualisation) - cagr(benchmark, annualisation)) * 100.0
    excess_sh = sharpe(strategy, annualisation) - sharpe(benchmark, annualisation)

    diff = aligned["s"] - aligned["b"]
    if len(diff) < 2 or diff.std() == 0:
        ir = float("nan")
    else:
        ir = float(diff.mean() / diff.std() * math.sqrt(annualisation))

    up_mask = aligned["b"] > 0
    down_mask = aligned["b"] < 0
    up_capture = (
        float(aligned.loc[up_mask, "s"].mean() / aligned.loc[up_mask, "b"].mean())
        if up_mask.sum() > 0 and aligned.loc[up_mask, "b"].mean() != 0
        else float("nan")
    )
    down_capture = (
        float(aligned.loc[down_mask, "s"].mean() / aligned.loc[down_mask, "b"].mean())
        if down_mask.sum() > 0 and aligned.loc[down_mask, "b"].mean() != 0
        else float("nan")
    )

    return ExcessMetrics(
        excess_cagr_pct=excess_cagr,
        excess_sharpe=excess_sh,
        information_ratio=ir,
        up_capture=up_capture,
        down_capture=down_capture,
    )


def format_benchmark_table(m: ExcessMetrics, label: str = "") -> str:
    title = f" — {label}" if label else ""
    return (
        f"### Benchmark comparison{title}\n\n"
        "| Metric | Value | Reading |\n"
        "|---|---:|---|\n"
        f"| Excess CAGR | {m.excess_cagr_pct:+.2f}% | strategy - benchmark annualised return |\n"
        f"| Excess Sharpe | {m.excess_sharpe:+.3f} | strategy - benchmark Sharpe |\n"
        f"| Information ratio | {m.information_ratio:.3f} | excess return / tracking error |\n"
        f"| Up-capture | {m.up_capture:.2f} | strategy return / benchmark return on up days |\n"
        f"| Down-capture | {m.down_capture:.2f} | same, on down days (lower is better) |\n"
    )
