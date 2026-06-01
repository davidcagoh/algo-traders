#!/usr/bin/env python3
"""
Build the correlation matrix + MDB table for the A1.5 common-window ZIPs.

Writes:
  wiki/assets/correlation_matrix.png   — heatmap (Pearson)
  wiki/results/_correlation_table.json — corr matrix + MDB table

Usage:
  ./freqtrade/.venv/bin/python scripts/run_correlation_mdb.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from eval_layers import (
    build_returns_matrix,
    correlation_matrix,
    marginal_diversification_benefit,
    mdb_robust_flag,
    render_heatmap,
)

REPO = Path(__file__).resolve().parent.parent
ZIP_DIR = REPO / "user_data" / "backtest_results"

# Map: family-code → ZIP path. Locked from A1.5.
ZIPS: dict[str, Path] = {
    "T0":   ZIP_DIR / "a15_longonly_binance_common.zip",
    "T1":   ZIP_DIR / "a15_trendfilter200_binance_common.zip",
    "T2":   ZIP_DIR / "a15_smaregime720_binance_common.zip",
    "T3":   ZIP_DIR / "a15_smaregime180_binance_common.zip",
    "R1~":  ZIP_DIR / "a15_hmmregime4_binance_common.zip",
    "R2":   ZIP_DIR / "a15_hmmregime4rolling_binance_common.zip",
    "R2x":  ZIP_DIR / "a15_hmm4rolling_multi_binance_common.zip",
    "R∧T1": ZIP_DIR / "a15_hmm_sma_slope_multi_binance_common.zip",
    "R∧T2": ZIP_DIR / "a15_hmm_sma_slope_v2_multi_binance_common.zip",
    "R∧T3": ZIP_DIR / "a15_hmm_sma_slope_v3_multi_binance_common.zip",
    "C1":   ZIP_DIR / "a15_funding_carry_multi_binance_common.zip",
    "R∧C1": ZIP_DIR / "a15_hmm_carry_multi_binance_common.zip",
    "X1":   ZIP_DIR / "a15_pairs_sol_doge.zip",
    "X2":   ZIP_DIR / "a15_cross_sectional_momentum.zip",
    "F1":   ZIP_DIR / "a15_funding_extreme_mr.zip",
}

# Current paper-trade book — A2 expanded book from {T3} to {T3, R∧T2}.
BOOK = ["T3", "R∧T2"]


def main() -> None:
    print(f"Loading {len(ZIPS)} ZIPs and building returns matrix...")
    returns = build_returns_matrix(ZIPS)
    print(f"  date range: {returns.index.min().date()} → {returns.index.max().date()}")
    print(f"  observations: {len(returns)} days")

    print("\nPearson correlation matrix:")
    corr = correlation_matrix(returns, method="pearson")
    print(corr.round(2).to_string())

    print("\nSpearman correlation matrix:")
    corr_s = correlation_matrix(returns, method="spearman")
    print(corr_s.round(2).to_string())

    out_png = REPO / "wiki" / "assets" / "correlation_matrix.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)
    render_heatmap(corr, out_png, title="Strategy correlation — A1.5 common window (Pearson)")
    print(f"\nwrote {out_png}")

    print(f"\nMDB vs book = {BOOK}")
    rows = []
    header = f"{'code':<6} {'corr_T3':>8} {'MDB-eq':>8} {'MDB-rp':>8} {'MDB-mv':>8} {'robust':>7}"
    print(header)
    print("-" * len(header))
    for code in ZIPS:
        if code in BOOK:
            print(f"{code:<6} {'(book)':>8} {'—':>8} {'—':>8} {'—':>8} {'(book)':>7}")
            rows.append({"code": code, "corr_to_book": None, "mdb_eq": None, "mdb_rp": None, "mdb_mv": None, "robust": None, "in_book": True})
            continue
        corr_t3 = float(corr.loc[code, "T3"])
        mdb_eq = marginal_diversification_benefit(returns, BOOK, code, "eq")
        mdb_rp = marginal_diversification_benefit(returns, BOOK, code, "rp")
        mdb_mv = marginal_diversification_benefit(returns, BOOK, code, "mv")
        robust = mdb_robust_flag(returns, BOOK, code)
        print(f"{code:<6} {corr_t3:>+8.2f} {mdb_eq:>+8.3f} {mdb_rp:>+8.3f} {mdb_mv:>+8.3f} {'YES' if robust else 'no':>7}")
        rows.append({
            "code": code, "corr_to_book": corr_t3,
            "mdb_eq": mdb_eq, "mdb_rp": mdb_rp, "mdb_mv": mdb_mv,
            "robust": robust, "in_book": False,
        })

    out_json = REPO / "wiki" / "results" / "_correlation_table.json"
    payload = {
        "common_window": {
            "start": str(returns.index.min().date()),
            "end": str(returns.index.max().date()),
            "n_days": int(len(returns)),
        },
        "book": BOOK,
        "annualisation": 365,
        "pearson_corr": corr.round(4).to_dict(),
        "spearman_corr": corr_s.round(4).to_dict(),
        "mdb": rows,
        "notes": [
            "MDB-rp uses 90-day vol window for risk-parity weights (pre-decision Q2).",
            "MDB-mv uses long-only Markowitz tangency (Σ⁻¹μ, clipped, normalized). Unstable at small N — treat as upper bound.",
            "Missing-day returns filled with 0 (strategy was flat). Pulls correlation toward zero by construction.",
        ],
    }
    out_json.write_text(json.dumps(payload, indent=2, default=str))
    print(f"\nwrote {out_json}")


if __name__ == "__main__":
    main()
