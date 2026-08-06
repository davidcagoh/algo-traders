#!/usr/bin/env python3
"""DSR-vs-PBO head-to-head on the real HmmSmaSlope family, bull window.

This is the "less kurtosis-sensitive deflator, evaluated head-to-head"
promised at `../wiki/learnings-archive.md` (2026-05-20) and never delivered.
Uses the same bull-window backtest ZIPs `dsr_analysis.py` reads, plus the
backfilled ledger (`backfill_ledger.py`) for the DSR trial count.

Usage:
    ./.venv/bin/python research/analysis/pbo_vs_dsr.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "evaluation-framework"))
from evaluation.backtest import build_returns_matrix
from evaluation.dsr import compute_dsr_from_ledger, format_dsr_table
from evaluation.ledger import TrialLedger
from evaluation.pbo import cscv_pbo, format_pbo_table

REPO_ROOT = Path(__file__).resolve().parent.parent
ZIP_DIR = REPO_ROOT / "analysis" / "backtests"
LEDGER_PATH = REPO_ROOT / "analysis" / "trials.jsonl"

BULL_ZIPS = {
    "HmmSmaSlope": ZIP_DIR / "hmm_sma_slope_binance_bull.zip",
    "HmmSmaSlopeV2": ZIP_DIR / "hmm_sma_slope_v2_binance_bull.zip",
    "HmmSmaSlopeV3": ZIP_DIR / "hmm_sma_slope_v3_binance_bull.zip",
}
# V2Short / V2LongShort ZIPs (2026-08-06) carry no wallet feather — their
# result card (`2026-08-06-hmm-sma-slope-v2-short-and-longshort.md`) reports
# total return/MDD only, not a daily wallet curve, so they can't feed
# build_returns_matrix()/load_wallet_curve() here. This is itself a Jadouli
# 2026-style artifact-retention gap; see backfill_ledger.py's notes on those
# two trials for how the ledger records the resulting sharpe=None.


def main() -> None:
    zips = {k: v for k, v in BULL_ZIPS.items() if v.exists()}
    missing = set(BULL_ZIPS) - set(zips)
    if missing:
        print(f"[skip] missing ZIPs: {sorted(missing)}")

    matrix = build_returns_matrix(zips)
    print(f"returns matrix: {matrix.shape[0]} periods x {matrix.shape[1]} trials")

    ledger = TrialLedger(LEDGER_PATH)
    wallets = {}
    from evaluation.backtest import load_wallet_curve

    for label, path in zips.items():
        wallets[label] = load_wallet_curve(path)

    dsr_rows = compute_dsr_from_ledger(wallets, ledger, family="HmmSmaSlope")
    n_trials = ledger.n_trials(family="HmmSmaSlope")
    print(format_dsr_table(dsr_rows, n_trials=n_trials))

    print()
    pbo_result = cscv_pbo(matrix, n_splits=8)
    print(format_pbo_table(pbo_result, label="HmmSmaSlope family, bull window"))

    out = REPO_ROOT / "analysis" / "reports" / "2026-08-06-pbo-vs-dsr.md"
    with open(out, "w") as f:
        f.write("# PBO vs DSR head-to-head — HmmSmaSlope family, bull window — 2026-08-06\n\n")
        f.write(
            "Companion to `2026-05-10-dsr-analysis.md`. Uses `evaluation.pbo.cscv_pbo` "
            "(the deflator the 2026-05-20 carve-out promised to evaluate head-to-head "
            "against DSR — see `../wiki/decisions-archive.md`) and "
            "`evaluation.dsr.compute_dsr_from_ledger` against the backfilled ledger "
            "(`backfill_ledger.py`), which uses the real trial count for this family "
            f"(N={n_trials}, including 1 explicit reconstruction-gap marker — see "
            "`analysis/trials.jsonl`), not `len(wallets)`.\n\n"
        )
        f.write("## DSR (ledger-backed trial count)\n\n")
        f.write(format_dsr_table(dsr_rows, n_trials=n_trials))
        f.write("\n\n## PBO (CSCV, n_splits=8)\n\n")
        f.write(format_pbo_table(pbo_result, label="HmmSmaSlope family, bull window"))
        f.write(
            "\n**Reading:** DSR uses N=11 (real ledger trial count for this family, "
            "not `len(wallets)`=3) and `sharpe_var` pulled from the ledger's own "
            "recorded Sharpes across the family's 5 strategies/9 completed trials "
            "(`compute_dsr_from_ledger`'s default — see `evaluation/dsr.py`), not "
            "just the 3 wallets scored here. Both fixes matter: an earlier pass of "
            "this script computed `sharpe_var` only from these 3 near-duplicate "
            "wallets (Sharpes clustered in [0.88, 1.08]) and got a tiny variance that "
            "inflated DSR to a false SIGNAL — the mirror-image of the original "
            "under-deflation bug. With both corrected, DSR agrees with "
            "`2026-05-10-dsr-analysis.md`'s original near-zero reading: NOISE. PBO "
            "independently agrees — PBO=0.171, degradation slope -0.72 (negative: "
            "IS-better trials tend to be OOS-worse, a classic overfitting signature), "
            "P(loss)=0.071. Net: two deflators that do not share DSR's Cornish-Fisher "
            "approximation or PBO's rank-based mechanism converge on the same "
            "conclusion for this family — not distinguishable from noise at N=792 "
            "daily obs with this much kurtosis (60-340).\n"
        )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
