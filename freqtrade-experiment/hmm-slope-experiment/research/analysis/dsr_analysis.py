#!/usr/bin/env python3
"""
Deflated Sharpe Ratio analysis across all backtested strategies.

Migrated 2026-08-06 to use `evaluation.dsr` instead of a locally duplicated
copy of the DSR formula (López de Prado 2014). See
`evaluation-framework/evaluation/dsr.py` for the formula, the 2026-08-06
kurtosis-carve-out fix, and the `n_trials`/`sharpe_var` requirements this
script must satisfy.

**N_trials caveat:** `RUNS` below lists the 9 strategies this script reads
wallet ZIPs for — the same 9 rows `_dsr_table.json` has always reported.
That is *not* the true search size: `research/analysis/reports/` contains
34 dated result cards, i.e. many more strategies and variants were tried
and killed than these 9 survivors. `n_trials=len(RUNS)` here is therefore a
known-incomplete floor, same caveat as
`freqtrade-experiment/hmm-slope-experiment/research/analysis/pbo_vs_dsr.py`'s
HmmSmaSlope-family-only backfill — extending `backfill_ledger.py` to cover
the full report-card history (not just the HmmSmaSlope family) would fix
this properly; not done here to keep this migration scoped to removing
code duplication, not re-deriving the whole trial history.

Usage:
    ./.venv/bin/python analysis/dsr_analysis.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "evaluation-framework"))
from evaluation.backtest import load_daily_returns, load_trade_returns
from evaluation.dsr import compute_dsr_table, format_dsr_table

REPO_ROOT = Path(__file__).resolve().parent.parent
ZIP_DIR = REPO_ROOT / "analysis" / "backtests"

# Backtest archives to include in the analysis. Each entry is a tuple of
# (label, zip filename relative to ZIP_DIR, window-type for context).
RUNS = [
    ("HmmRegime4Rolling-multi (bull)", "hmm_multi_binance_bull_2023_2025.zip", "bull"),
    ("HmmCarry (bull)", "hmm_carry_binance_bull_2023_2025.zip", "bull"),
    ("FundingCarry (bull)", "funding_carry_binance_bull_2023_2025.zip", "bull"),
    ("HmmSmaSlope (bull)", "hmm_sma_slope_binance_bull.zip", "bull"),
    ("HmmSmaSlopeV2 (bull)", "hmm_sma_slope_v2_binance_bull.zip", "bull"),
    ("HmmSmaSlopeV3 (bull)", "hmm_sma_slope_v3_binance_bull.zip", "bull"),
    ("HmmSmaSlope (bear)", "hmm_sma_slope_hl_bear.zip", "bear"),
    ("HmmSmaSlopeV2 (bear)", "hmm_sma_slope_v2_hl_bear.zip", "bear"),
    ("HmmSmaSlopeV3 (bear)", "hmm_sma_slope_v3_hl_bear.zip", "bear"),
]


def main() -> None:
    wallets_daily: dict[str, pd.Series] = {}
    wallets_trade: dict[str, pd.Series] = {}
    windows: dict[str, str] = {}

    for label, fname, window in RUNS:
        path = ZIP_DIR / fname
        if not path.exists():
            print(f"  [skip] {label}: {fname} not found")
            continue
        windows[label] = window

        d_ret = load_daily_returns(path)
        # compute_dsr_table wants a wallet curve, not returns — reconstruct
        # one so it can derive Sharpe/skew/kurt/N itself (single source of
        # truth for the formula, matching how the package's own tests do it).
        wallets_daily[label] = 100.0 * (1.0 + d_ret).cumprod()

        t_ret = load_trade_returns(path)
        if len(t_ret) >= 3 and not d_ret.empty:
            wallets_trade[label] = 100.0 * (1.0 + t_ret).cumprod()

    def _run(title: str, wallets: dict[str, pd.Series], annualisation_hint: str) -> list:
        if not wallets:
            return []
        n_trials = len(RUNS)  # known floor — see module docstring
        rows = compute_dsr_table(wallets, n_trials=n_trials, annualisation=365.0)
        print(f"\n=== {title} === N_trials={n_trials} (floor, not full search)")
        print(format_dsr_table(rows, n_trials=n_trials))
        return rows

    daily_rows = _run("Daily-wallet returns (standard)", wallets_daily, "365d")
    trade_rows = _run("Per-trade returns (alternative basis)", wallets_trade, "trades/yr")

    out = REPO_ROOT / "analysis" / "reports" / "_dsr_table.json"
    with open(out, "w") as f:
        json.dump(
            {
                "daily_wallet": [
                    {
                        "strategy": r.label,
                        "window": windows.get(r.label, ""),
                        "sharpe": r.sharpe,
                        "skew": r.skew,
                        "kurt": r.kurt,
                        "n_obs": r.n_obs,
                        "dsr": r.dsr,
                    }
                    for r in daily_rows
                ],
                "per_trade": [
                    {
                        "strategy": r.label,
                        "window": windows.get(r.label, ""),
                        "sharpe": r.sharpe,
                        "skew": r.skew,
                        "kurt": r.kurt,
                        "n_obs": r.n_obs,
                        "dsr": r.dsr,
                    }
                    for r in trade_rows
                ],
            },
            f,
            indent=2,
        )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
