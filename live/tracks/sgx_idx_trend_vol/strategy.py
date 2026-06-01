"""Venue-agnostic port of feishu's `trend_vol_v4` mechanism.

Ingredients (matches `feishu/signals/{low_vol,vol_managed,trend_vol_v4}.py`):
  1. Low-vol selection: rank by inverse rolling-N return std.
  2. Liquidity filter: drop bottom q-pct by rolling turnover.
  3. Market-vol regime gate: blank rebalance when rolling cross-sectional
     variance exceeds sigma_threshold × its median.
  4. Trend filter: drop stocks with M-day return ≤ trend_threshold.
  5. Inverse-vol portfolio weights on the top-N survivors.

Differences vs feishu port:
  - Input format is a panel dict {'close', 'volume', 'amount'} of
    (date × ticker) DataFrames, not the long-form OHLCV used by feishu's
    competition backtester.
  - No `adj_factor` math — assumes yfinance auto-adjusted closes.
  - All windows are configurable; defaults match `trend_vol_v4` exactly
    (vol=60, liq=20, regime=30, trend=35, threshold=-0.025, sigma=2.0, N=20)
    to preserve mechanism fidelity. Hyperparameter retuning on tuning
    window is a separate step.
  - Output: a (date × ticker) weights DataFrame, NaN where unselected,
    rows sum to 1 on rebalance days, all-NaN rows on blanked days.

The weights DataFrame can be fed to any panel-rebalance backtest.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TrendVolParams:
    """Hyperparameters. Defaults match feishu's `trend_vol_v4`."""
    vol_window: int = 60          # rolling vol for low-vol rank
    liq_window: int = 20          # rolling turnover for liquidity filter
    liq_exclude: float = 0.05     # bottom fraction by liquidity to drop
    regime_window: int = 30       # rolling market variance window
    sigma_threshold: float = 2.0  # blank if rolling_var > sigma * median
    trend_window: int = 35        # trailing return window for trend filter
    trend_threshold: float = -0.025  # min trailing return to qualify
    top_n: int = 20               # portfolio size
    weight_window: int = 60       # inverse-vol weights window
    # Hedged-mechanism extension (pre-registered in `decisions/004`).
    # When set, applies a broad-market SMA gate that overrides the
    # mechanism's weights with go-flat (zero) on out-of-market days.
    hedge_window: int = 0         # 0 = disabled; 200 = standard SMA hedge


# ─── Step 1 — Low-vol rank ────────────────────────────────────────────────────


def _low_vol_signal(
    close: pd.DataFrame,
    amount: pd.DataFrame,
    params: TrendVolParams,
) -> pd.DataFrame:
    """Negated rolling-std with liquidity filter, cross-sectional z-scored."""
    ret = close.pct_change()
    rolling_std = ret.rolling(params.vol_window).std()
    signal = -rolling_std  # high = low vol = favoured

    if params.liq_exclude > 0.0:
        liq = amount.rolling(params.liq_window).mean()
        liq_threshold = liq.quantile(params.liq_exclude, axis=1)
        illiquid = liq.lt(liq_threshold, axis=0)
        signal = signal.where(~illiquid, np.nan)

    mu = signal.mean(axis=1)
    sd = signal.std(axis=1).replace(0, np.nan)
    return signal.sub(mu, axis=0).div(sd, axis=0)


# ─── Step 2 — Market-vol regime gate ──────────────────────────────────────────


def _regime_gate_mask(
    close: pd.DataFrame,
    params: TrendVolParams,
) -> pd.Series:
    """True on days where the market-vol gate fires (blank the row)."""
    ret = close.pct_change()
    daily_var = (ret**2).mean(axis=1)
    rolling_var = daily_var.rolling(
        params.regime_window, min_periods=params.regime_window
    ).mean()
    median_var = rolling_var.median()
    if median_var == 0 or np.isnan(median_var):
        return pd.Series(False, index=close.index)
    return rolling_var > (params.sigma_threshold * median_var)


# ─── Step 3 — Trend filter ────────────────────────────────────────────────────


def _trend_mask(close: pd.DataFrame, params: TrendVolParams) -> pd.DataFrame:
    """True where M-day trailing return > trend_threshold."""
    trend = close / close.shift(params.trend_window) - 1.0
    return trend > params.trend_threshold


# ─── Step 4 — Selection ───────────────────────────────────────────────────────


def selection(
    close: pd.DataFrame,
    amount: pd.DataFrame,
    params: TrendVolParams = TrendVolParams(),
) -> pd.DataFrame:
    """Boolean (date × ticker) matrix: True iff selected on that day.

    All-False rows on regime-gate days. Top-N by low-vol z-score among
    trend-filter survivors.
    """
    z = _low_vol_signal(close, amount, params)
    z = z.where(_trend_mask(close, params))

    blank = _regime_gate_mask(close, params)
    z.loc[blank] = np.nan

    rank = z.rank(axis=1, ascending=False, method="first")
    return rank <= params.top_n


# ─── Step 5 — Inverse-vol weights ─────────────────────────────────────────────


def weights(
    close: pd.DataFrame,
    amount: pd.DataFrame,
    params: TrendVolParams = TrendVolParams(),
) -> pd.DataFrame:
    """(date × ticker) weight matrix. NaN where unselected. Rows sum to 1.

    Days on which the regime gate fires produce all-NaN rows; a backtest
    on this output should hold the previous day's positions.
    """
    selected = selection(close, amount, params)

    ret = close.pct_change()
    sigma = ret.rolling(params.weight_window).std()
    raw = (1.0 / sigma).where(selected)

    row_sum = raw.sum(axis=1).replace(0, np.nan)
    w = raw.div(row_sum, axis=0)

    # all-NaN rows survive the divide as all-NaN (intended).
    return w


# ─── Step 6 — Optional broad-market trend hedge (decisions/004) ───────────────


def hedged_weights(
    close: pd.DataFrame,
    amount: pd.DataFrame,
    params: TrendVolParams = TrendVolParams(),
) -> pd.DataFrame:
    """Apply the broad-market SMA hedge on top of `weights()`.

    Out-of-market rows are forced to all-zero (go flat). In-market rows
    pass through unchanged (including the mechanism's own regime-blank).
    No-op if `params.hedge_window` is 0 or unset.
    """
    base = weights(close, amount, params)
    if not params.hedge_window:
        return base

    # Equal-weighted broad proxy. Forward-only (rolling uses past).
    broad = close.mean(axis=1)
    broad_sma = broad.rolling(params.hedge_window).mean()
    out_of_market = broad <= broad_sma  # NaN comparison is False → treated as in
    out_dates = out_of_market[out_of_market].index

    hedged = base.copy()
    # Zero out the row (not NaN) so backtest interprets as "rebalance to flat".
    hedged.loc[out_dates] = 0.0
    return hedged
