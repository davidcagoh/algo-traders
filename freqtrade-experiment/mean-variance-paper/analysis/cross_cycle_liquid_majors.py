#!/usr/bin/env python3
"""
Cross-cycle proxy validation for the signed mean-variance methodology.

`mean-variance-paper`'s headline result (shrunk_mean_variance_signed:
+122.61%, Sharpe 3.86) was only ever tested on one ~7-month Hyperliquid
window (2025-11-05 -> 2026-06-01), because Hyperliquid's public API caps
history at ~5000 1h candles (~208 days) per (pair, timeframe) — see
`../hmm-slope-experiment/research/analysis/reports/2026-04-24-decision-002-hyperliquid-deep-history.md`.
It cannot be backtested across multiple cycles on its actual 9-coin
universe: several of those coins (WLFI, VVV, XPL) launched in 2025 and have
no prior cycle to test against at all, on any venue.

This script does NOT validate the actual traded book. It substitutes a
liquid-majors proxy universe (BTC, ETH, SOL, AVAX, ARB, DOGE) that has deep
history on Binance (`../hmm-slope-experiment/research/data/binance/futures/`,
back to 2019-2023 depending on the coin), and re-runs the identical
`shrunk_mean_variance_signed` construction (reusing
`run_portfolio_short_funding.simulate`/`target_weights`/`metrics` verbatim
— same optimizer, same weighting logic, only the data source and universe
differ) across windows from structurally different regimes. This tells us
whether the *method* has an edge outside its one favorable window; it
cannot tell us whether the *actual* WLFI/VVV/XPL-containing book depends on
those tokens' idiosyncratic momentum, since no substitute data exists for
that question.

Usage:
    ./.venv/bin/python analysis/cross_cycle_liquid_majors.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_portfolio_short_funding import markdown, metrics, simulate

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO.parent / "hmm-slope-experiment" / "research" / "data" / "binance" / "futures"
RESULTS_DIR = REPO / "analysis" / "results"

COINS = ["BTC", "ETH", "SOL", "AVAX", "ARB", "DOGE"]

# Windows chosen from BTC's monthly closes over the full cached history
# (2019-09 -> 2026-05): the original mean-variance-paper study window
# (2025-11 -> 2026-06) was itself a sharp bear-into-recovery leg (BTC
# ~$110k -> ~$67k -> ~$76k), which is why the signed (short-capable)
# variant outperformed so heavily. The two windows below test regimes that
# aren't sharp-bear-into-recovery: a strong uninterrupted bull, and a
# multi-month chop/consolidation (historically the hardest regime for
# dispersion-harvesting strategies).
WINDOWS = {
    "bull_2023H2-2024Q1": ("2023-10-01", "2024-04-01"),
    "chop_2024Q2-Q4": ("2024-04-01", "2024-11-01"),
}

# Same defaults as run_portfolio_short_funding.main() / the "current" sweep
# winner (mean_shrink=0.50, risk_aversion=1.0) from
# portfolio_mv_param_sweep_hl_1h_current.md.
PARAMS = dict(
    lookback=60,
    rebalance_days=7,
    fee=0.00035,
    cap=0.20,
    gross_limit=1.0,
    mean_shrink=0.50,
    risk_aversion=1.0,
    turnover_penalty=0.05,
)

METHODS = [
    "btc_long",
    "equal_weight_long",
    "inverse_vol_long",
    "minimum_variance_signed",
    "shrunk_mean_variance_signed",
]


def load_daily_prices(coins: list[str]) -> pd.DataFrame:
    series = []
    for coin in coins:
        path = DATA_DIR / f"{coin}_USDT_USDT-1h-futures.feather"
        df = pd.read_feather(path)
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.sort_values("date").drop_duplicates("date")
        daily = df.set_index("date")["close"].resample("1D").last().dropna()
        series.append(daily.rename(coin))
    return pd.concat(series, axis=1).dropna(how="any")


def load_daily_funding(coins: list[str], index: pd.DatetimeIndex) -> pd.DataFrame:
    series = []
    for coin in coins:
        path = DATA_DIR / f"{coin}_USDT_USDT-8h-funding_rate.feather"
        df = pd.read_feather(path)
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.sort_values("date").drop_duplicates("date")
        daily = df.set_index("date")["open"].resample("1D").sum()
        series.append(daily.rename(coin))
    return pd.concat(series, axis=1).reindex(index).fillna(0.0)


def run_window(label: str, start: str, end: str, prices: pd.DataFrame, funding: pd.DataFrame) -> dict:
    # Buffer the slice by `lookback` calendar days before `start` so the
    # optimizer's first in-window rebalance uses real pre-window history,
    # not the window's own early days as a synthetic lookback.
    full_returns = prices.pct_change().dropna()
    buffered_start = pd.Timestamp(start, tz="UTC") - pd.Timedelta(days=PARAMS["lookback"])
    end_ts = pd.Timestamp(end, tz="UTC")
    price_returns = full_returns.loc[buffered_start:end_ts]
    funding_w = funding.reindex(price_returns.index).fillna(0.0)

    rows = {}
    for method in METHODS:
        rets, weights, costs, fund_pnl = simulate(
            price_returns,
            funding_w,
            method,
            PARAMS["lookback"],
            PARAMS["rebalance_days"],
            PARAMS["fee"],
            PARAMS["cap"],
            PARAMS["gross_limit"],
            PARAMS["mean_shrink"],
            PARAMS["risk_aversion"],
            PARAMS["turnover_penalty"],
        )
        rows[method] = metrics(rets, weights, costs, fund_pnl, PARAMS["rebalance_days"])
    active_start = price_returns.index[PARAMS["lookback"]].date()
    print(f"\n=== {label}: {active_start} -> {price_returns.index.max().date()} (active, excl. {PARAMS['lookback']}d lookback buffer) ===")
    print(markdown(rows))
    return rows


def main() -> None:
    prices = load_daily_prices(COINS)
    price_returns = prices.pct_change().dropna()
    funding = load_daily_funding(COINS, price_returns.index)

    all_rows = {}
    for label, (start, end) in WINDOWS.items():
        all_rows[label] = run_window(label, start, end, prices, funding)

    out = RESULTS_DIR / "cross_cycle_liquid_majors_proxy.json"
    out.write_text(
        json.dumps(
            {
                "universe": COINS,
                "data_source": "binance (proxy — NOT the actual hyperliquid 9-coin book)",
                "params": PARAMS,
                "windows": WINDOWS,
                "results": all_rows,
            },
            indent=2,
        )
    )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
