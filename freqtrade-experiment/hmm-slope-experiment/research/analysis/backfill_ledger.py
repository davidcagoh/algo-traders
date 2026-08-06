#!/usr/bin/env python3
"""Backfill a TrialLedger for the HmmSmaSlope family from dated result cards.

Reconstructed from `research/analysis/reports/_dsr_table.json` (daily-wallet
Sharpe/skew/kurt/n_obs for V1/V2/V3, bull+bear) and the 2026-08-06 short/
long-short result card. This is a FLOOR, not the true search size: the
result cards' own "next-test" sections reference parameter variants (e.g.
slope-sizing exponents between V2's linear and V3's sqrt) that were
discussed but have no surviving result card, and are therefore NOT counted
here. See the `notes` field on the `reconstruction-gap` entry below.

Usage:
    ./.venv/bin/python research/analysis/backfill_ledger.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "evaluation-framework"))
from evaluation.ledger import TrialLedger, TrialRecord

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS = REPO_ROOT / "analysis" / "reports"
LEDGER_PATH = REPO_ROOT / "analysis" / "trials.jsonl"

FAMILY = "HmmSmaSlope"
DATASET_BULL = "binance-6coin-bull-2023-2025"
DATASET_BEAR = "hyperliquid-7coin-bear-2025-2026"

# (strategy, window, dataset_id, sizing) for the three sizing variants,
# read from _dsr_table.json's daily_wallet rows.
SIZING = {
    "HmmSmaSlope": "binary-gate",
    "HmmSmaSlopeV2": "linear-slope",
    "HmmSmaSlopeV3": "sqrt-slope",
}


def main() -> None:
    ledger = TrialLedger(LEDGER_PATH)
    if LEDGER_PATH.exists():
        print(f"{LEDGER_PATH} already exists; refusing to double-backfill. Delete it first.")
        return

    dsr_table = json.loads((REPORTS / "_dsr_table.json").read_text())
    daily = {row["strategy"]: row for row in dsr_table["daily_wallet"]}

    created_bull = "2026-05-10T00:00:00Z"
    created_bear = "2026-05-10T00:00:00Z"

    for strategy, sizing in SIZING.items():
        for window, dataset_id, created_at in (
            ("bull", DATASET_BULL, created_bull),
            ("bear", DATASET_BEAR, created_bear),
        ):
            key = f"{strategy} ({window})"
            row = daily.get(key)
            ledger.append(
                TrialRecord(
                    trial_id=f"{strategy.lower()}-{window}",
                    created_at=created_at,
                    family=FAMILY,
                    strategy=strategy,
                    params={"sizing": sizing, "window": window},
                    dataset_id=dataset_id,
                    split_id="full",
                    status="completed",
                    sharpe=row["sharpe"] if row else None,
                    n_obs=row["n_obs"] if row else None,
                    notes=f"backfilled from _dsr_table.json daily_wallet[{key!r}]" if row
                    else "backfilled; row missing from _dsr_table.json",
                )
            )

    # 2026-08-06 short-side and combined long+short variants.
    short_long = [
        ("HmmSmaSlopeV2Short", "bull", DATASET_BULL, -0.20, None),
        ("HmmSmaSlopeV2Short", "bear", DATASET_BEAR, -2.61, None),
        ("HmmSmaSlopeV2LongShort", "bull", DATASET_BULL, None, None),
        ("HmmSmaSlopeV2LongShort", "bear", DATASET_BEAR, None, None),
    ]
    for strategy, window, dataset_id, sharpe, n_obs in short_long:
        ledger.append(
            TrialRecord(
                trial_id=f"{strategy.lower()}-{window}",
                created_at="2026-08-06T00:00:00Z",
                family=FAMILY,
                strategy=strategy,
                params={"sizing": "linear-slope", "side": "short-or-longshort", "window": window},
                dataset_id=dataset_id,
                split_id="full",
                status="completed",
                sharpe=sharpe,
                n_obs=n_obs,
                notes=(
                    "backfilled from 2026-08-06 result card"
                    if sharpe is not None
                    else "backfilled from 2026-08-06 result card; Sharpe not reported "
                    "there (card gives only total return/MDD) — n_obs/sharpe left null, "
                    "counted toward n_trials() but excluded from sharpe_variance()"
                ),
            )
        )

    # Explicit floor marker: reconstruction is known-incomplete. This entry
    # documents the gap rather than silently omitting it (Jadouli 2026 —
    # missing artifacts should be visible, not absent).
    ledger.append(
        TrialRecord(
            trial_id="reconstruction-gap-marker",
            created_at="2026-08-06T00:00:00Z",
            family=FAMILY,
            strategy="(none — marker record)",
            params={},
            dataset_id="n/a",
            split_id="n/a",
            status="discarded",
            notes=(
                "Result cards reference parameter-sweep ideas (e.g. slope-sizing "
                "exponents strictly between V2's linear=1.0 and V3's sqrt=0.5, "
                "alternative slope reference thresholds) that were discussed in "
                "'next steps' sections but have no surviving result card or wallet "
                "ZIP. The 10 real trial records above are a FLOOR on the true "
                "search size, not a complete count. Any DSR/PBO computed from "
                "this ledger under-deflates to the extent this gap is nonzero."
            ),
        ),
        allow_rerun=True,
    )

    n = ledger.n_trials()
    print(f"wrote {LEDGER_PATH} with {n} records (including 1 gap marker)")
    problems = ledger.validate()
    if problems:
        print("VALIDATION PROBLEMS:")
        for p in problems:
            print(" ", p)
    else:
        print("ledger validates cleanly")


if __name__ == "__main__":
    main()
