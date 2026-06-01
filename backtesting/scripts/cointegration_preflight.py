#!/usr/bin/env python3
"""
Cointegration preflight for the pairs family.

For every candidate pair in the 5-coin Binance perp universe, run a rolling
Engle-Granger test on prior 1000 bars of 4h log-prices, compute the OU
half-life of the residual spread, and emit a parquet of (pair, window_end,
p_value, hedge_ratio_beta, half_life_hours).

Filters applied in main():
  - p_value < 0.05
  - 12h <= half_life <= 240h (10 days)

The output filtered list goes into PairsZScore strategy.

Usage:
  ./freqtrade/.venv/bin/python scripts/cointegration_preflight.py
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "user_data" / "data" / "binance" / "futures"
OUT = REPO / "user_data" / "data" / "cointegration_preflight.parquet"

COINS = ["BTC", "ETH", "SOL", "AVAX", "DOGE"]
TIMEFRAME = "4h"
FIT_WINDOW = 1000   # bars
STEP = 168          # refit cadence (~weekly at 4h)
P_THRESHOLD = 0.05
HALF_LIFE_MIN_HOURS = 12
HALF_LIFE_MAX_HOURS = 240


def load_coin(coin: str) -> pd.Series:
    """Return close-price series for a coin, indexed by UTC."""
    path = DATA / f"{coin}_USDT_USDT-{TIMEFRAME}-futures.feather"
    df = pd.read_feather(path)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df.set_index("date")["close"].sort_index()


def ou_half_life(residual: pd.Series) -> float:
    """Estimate OU half-life in BARS from regression residual."""
    r = residual.dropna()
    if len(r) < 30:
        return float("nan")
    r_lag = r.shift(1).dropna()
    delta = r.diff().dropna()
    delta, r_lag = delta.align(r_lag, join="inner")
    if r_lag.var() == 0:
        return float("nan")
    # ΔR_t = -θ R_{t-1} + ε
    theta = -float(np.cov(delta, r_lag, bias=False)[0, 1] / r_lag.var())
    if theta <= 0:
        return float("nan")
    return float(np.log(2) / theta)


def rolling_cointegration(a: pd.Series, b: pd.Series) -> pd.DataFrame:
    """For each anchor point at FIT_WINDOW intervals of STEP, run E-G on prior FIT_WINDOW bars."""
    a, b = a.align(b, join="inner")
    log_a, log_b = np.log(a), np.log(b)
    rows = []
    for end in range(FIT_WINDOW, len(a), STEP):
        win_a = log_a.iloc[end - FIT_WINDOW:end]
        win_b = log_b.iloc[end - FIT_WINDOW:end]
        try:
            _t, pval, _cv = coint(win_a, win_b, trend="c", maxlag=24, autolag=None)
        except Exception:
            continue
        # OLS hedge ratio: log_a = α + β log_b + ε
        beta = float(np.cov(win_a, win_b, bias=False)[0, 1] / win_b.var())
        alpha = float(win_a.mean() - beta * win_b.mean())
        resid = win_a - (alpha + beta * win_b)
        hl_bars = ou_half_life(resid)
        hl_hours = hl_bars * 4 if not np.isnan(hl_bars) else float("nan")
        rows.append({
            "window_end": a.index[end - 1],
            "p_value": float(pval),
            "beta": beta,
            "alpha": alpha,
            "half_life_hours": hl_hours,
        })
    return pd.DataFrame(rows)


def main() -> None:
    print(f"Loading {len(COINS)} coins at {TIMEFRAME}...")
    series = {c: load_coin(c) for c in COINS}
    for c, s in series.items():
        print(f"  {c}: {len(s)} bars, {s.index.min().date()} → {s.index.max().date()}")

    all_rows = []
    for a, b in itertools.combinations(COINS, 2):
        print(f"\nrunning E-G on {a}-{b}...")
        df = rolling_cointegration(series[a], series[b])
        df["pair"] = f"{a}-{b}"
        all_rows.append(df)
        n = len(df)
        n_signif = (df["p_value"] < P_THRESHOLD).sum()
        in_band = ((df["half_life_hours"] >= HALF_LIFE_MIN_HOURS) & (df["half_life_hours"] <= HALF_LIFE_MAX_HOURS)).sum()
        print(f"  N_windows={n} p<{P_THRESHOLD}={n_signif} ({n_signif/n:.1%}) half_life_in_band={in_band}")

    full = pd.concat(all_rows, ignore_index=True)
    full.to_parquet(OUT)
    print(f"\nwrote {OUT} ({len(full)} rows)")

    # Quick summary: pairs that pass both filters most often
    print("\nPair ranking by (p < 0.05 AND half_life in band):")
    full["passes"] = (full["p_value"] < P_THRESHOLD) & (
        full["half_life_hours"].between(HALF_LIFE_MIN_HOURS, HALF_LIFE_MAX_HOURS)
    )
    summary = full.groupby("pair").agg(
        n_windows=("p_value", "count"),
        median_p=("p_value", "median"),
        median_hl_hours=("half_life_hours", "median"),
        pass_rate=("passes", "mean"),
    ).sort_values("pass_rate", ascending=False)
    print(summary.to_string())


if __name__ == "__main__":
    main()
