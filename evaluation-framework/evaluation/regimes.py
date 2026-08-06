"""Regime labeling and per-regime metric decomposition.

Literature: Liu 2026 (`../literature/strategy-evaluation/empirical-audits/2604.18821-backtest-regime-live-performance.pdf`)
— conditions the backtest-to-live decay haircut on launch regime, which
`evaluation.live.reconcile` uses this module for. This project's own regime
decomposition currently exists only as prose footnotes (2020-21 bull Calmar
14.04, 2022 bear -5.23, 2023-24 bull 21.13, 2025 bear 3.59) — this makes it
a first-class, reusable table instead.
"""

from __future__ import annotations

import pandas as pd

from evaluation.layers import DEFAULT_ANNUAL, LayeredMetrics, compute


def label_regimes(
    benchmark_prices: pd.Series, method: str = "drawdown", **kwargs: float
) -> pd.Series:
    """Categorical regime label per period: "bull" or "bear".

    `method="drawdown"`: bear whenever price is more than `dd_threshold`
    (default 0.10) below its running peak.
    `method="sma"`: bull when price > its `window`-period (default 180)
    SMA, else bear.
    `method="vol_tercile"`: bins trailing `window`-period (default 20)
    volatility into terciles, labeled "low_vol"/"mid_vol"/"high_vol".
    """
    if method == "drawdown":
        dd_threshold = kwargs.get("dd_threshold", 0.10)
        peak = benchmark_prices.cummax()
        drawdown = (benchmark_prices / peak) - 1.0
        return pd.Series(
            ["bear" if d <= -dd_threshold else "bull" for d in drawdown],
            index=benchmark_prices.index,
        )
    if method == "sma":
        window = int(kwargs.get("window", 180))
        sma = benchmark_prices.rolling(window, min_periods=1).mean()
        return pd.Series(
            ["bull" if p > s else "bear" for p, s in zip(benchmark_prices, sma)],
            index=benchmark_prices.index,
        )
    if method == "vol_tercile":
        window = int(kwargs.get("window", 20))
        returns = benchmark_prices.pct_change()
        vol = returns.rolling(window, min_periods=2).std()
        q1, q2 = vol.quantile([1 / 3, 2 / 3])
        labels = []
        for v in vol:
            if pd.isna(v):
                labels.append("mid_vol")
            elif v <= q1:
                labels.append("low_vol")
            elif v <= q2:
                labels.append("mid_vol")
            else:
                labels.append("high_vol")
        return pd.Series(labels, index=benchmark_prices.index)
    raise ValueError(f"unknown regime method: {method!r}")


def regime_metrics(
    wallet: pd.Series, labels: pd.Series, annualisation: float = DEFAULT_ANNUAL
) -> dict[str, LayeredMetrics]:
    """Full `LayeredMetrics` for each distinct regime label, computed on
    the wallet sub-series restricted to that regime's periods."""
    aligned_labels = labels.reindex(wallet.index).ffill().bfill()
    out: dict[str, LayeredMetrics] = {}
    for label in sorted(aligned_labels.dropna().unique()):
        mask = aligned_labels == label
        sub_wallet = wallet[mask]
        if len(sub_wallet) < 3:
            continue
        out[label] = compute(sub_wallet, annualisation=annualisation)
    return out


def regime_stability(regime_result: dict[str, LayeredMetrics]) -> dict[str, float]:
    """Flag strategies whose performance is concentrated in one regime.

    Returns each regime's share of total positive CAGR contribution (0-1);
    a strategy whose entire edge is in one regime shows one label near 1.0
    and the rest near 0 or negative.
    """
    cagrs = {label: m.cagr_pct for label, m in regime_result.items()}
    positive_total = sum(c for c in cagrs.values() if c > 0)
    if positive_total <= 0:
        return dict.fromkeys(cagrs, float("nan"))
    return {label: (c / positive_total if c > 0 else 0.0) for label, c in cagrs.items()}
