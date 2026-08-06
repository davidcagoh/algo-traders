#!/usr/bin/env python3
"""Backfill a TrialLedger for mean-variance-paper from dated result cards.

Reconstructed from the Markdown tables in `analysis/results/`:
`portfolio_baselines_hl_1h_current.md`, `portfolio_mv_param_sweep_hl_1h_current.md`,
`portfolio_short_funding_hl_1h_current.md`, `pc_neutral_alt_strategies_hl_1h_current.md`.
This is a FLOOR, not the true search size: only the surviving result-card
tables are counted, not every parameterization that was tried and not
written up.

`gate_outcome` is derived mechanically from the pre-registered thresholds in
`analysis/results/2026-06-02-decision-011-kill-criteria-mean-variance-portfolio.md`
(long-only baseline/sweep) and `...-012-kill-criteria-signed-mean-variance-portfolio.md`
(signed), both benchmarked against that table's own equal-weight row:

    kill if: Sharpe <= equal_weight Sharpe
          or Calmar <= equal_weight Calmar
          or MDD worse (more negative) than equal_weight MDD
          or avg effective assets < 3
          or avg turnover per rebalance > 1.25
    useful (passed) if, in addition: avg effective assets >= 4
          and avg exposure/gross >= 0.50 and turnover <= 0.75
    otherwise (kill condition absent but useful bar not cleared): pending

The `pc_neutral_alt_strategies` family has no pre-registered kill-criteria
decision doc, so its rows are left `evidence_stage="backtest"`,
`gate_outcome="pending"` rather than asserting a verdict no written rule
backs.

Usage:
    ./.venv/bin/python analysis/backfill_ledger.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "evaluation-framework"))
from evaluation.ledger import TrialLedger, TrialRecord

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = REPO_ROOT / "analysis" / "trials.jsonl"

PROJECT = "mean-variance-paper"
VENUE = "hyperliquid"
DATASET_LONG = "hyperliquid-9coin-2026-01-05_2026-06-01"
DATASET_PC = "hyperliquid-pc-neutral-alts-2025-12-07_2026-06-03"

CREATED_AT = "2026-06-02T00:00:00Z"

EW_SHARPE, EW_CALMAR, EW_MDD = 1.77, 5.03, -25.98  # long-only equal-weight benchmark
EW_LONG_SHARPE, EW_LONG_CALMAR, EW_LONG_MDD = 1.82, 5.31, -25.92  # signed benchmark


def _gate(sharpe, calmar, mdd, eff_assets, gross=None, turnover=None) -> str:
    """Decision 011/012 mechanical thresholds, long-only vs long-only EW."""
    if sharpe is None or (isinstance(sharpe, float) and sharpe != sharpe):  # nan
        return "n/a"
    kill = (
        sharpe <= EW_SHARPE
        or calmar <= EW_CALMAR
        or mdd < EW_MDD
        or eff_assets < 3
        or (turnover is not None and turnover > 1.25)
    )
    if kill:
        return "killed"
    useful = (
        eff_assets >= 4
        and (gross is None or gross >= 0.50)
        and (turnover is None or turnover <= 0.75)
    )
    return "passed" if useful else "pending"


def _gate_signed(sharpe, calmar, mdd, eff_assets, gross=None) -> str:
    kill = (
        sharpe <= EW_LONG_SHARPE
        or calmar <= EW_LONG_CALMAR
        or mdd < EW_LONG_MDD
        or eff_assets < 3
    )
    if kill:
        return "killed"
    useful = eff_assets >= 4 and (gross is None or gross >= 0.50)
    return "passed" if useful else "pending"


def main() -> None:
    ledger = TrialLedger(LEDGER_PATH)
    if LEDGER_PATH.exists():
        print(f"{LEDGER_PATH} already exists; refusing to double-backfill. Delete it first.")
        return

    # --- portfolio_baselines_hl_1h_current.md ---
    # (strategy, sharpe, calmar, mdd, eff_assets, gross)
    baselines = [
        ("btc", -0.95, -1.30, -35.11, 1.00, 1.00),
        ("equal_weight", 1.77, 5.03, -25.98, 8.99, 1.00),
        ("inverse_vol", 1.41, 3.01, -22.44, 7.46, 1.00),
        ("minimum_variance", 0.94, 1.72, -20.04, 5.82, 1.00),
        ("shrunk_mean_variance", 2.33, 4.41, -6.76, 2.74, 0.16),
    ]
    for strategy, sharpe, calmar, mdd, eff, gross in baselines:
        is_benchmark = strategy in ("btc", "equal_weight", "inverse_vol", "minimum_variance")
        ledger.append(
            TrialRecord(
                trial_id=f"baseline-{strategy}",
                created_at=CREATED_AT,
                family="PortfolioBaseline",
                strategy=strategy,
                params={"table": "portfolio_baselines"},
                dataset_id=DATASET_LONG,
                split_id="full",
                status="completed",
                sharpe=sharpe,
                project=PROJECT,
                venue=VENUE,
                evidence_stage="backtest",
                gate_outcome="n/a" if is_benchmark else _gate(sharpe, calmar, mdd, eff, gross),
                notes="backfilled from portfolio_baselines_hl_1h_current.md"
                + ("; reference benchmark, not a kill-criteria candidate" if is_benchmark else ""),
            )
        )

    # --- portfolio_mv_param_sweep_hl_1h_current.md ---
    # (mean_shrink, risk_aversion, sharpe, calmar, mdd, eff_assets, turnover)
    sweep = [
        (0.50, 1.00, 3.65, 30.35, -21.47, 4.25, 0.25),
        (1.00, 1.00, 3.61, 30.54, -23.23, 4.55, 0.27),
        (1.00, 3.00, 3.40, 23.04, -21.10, 3.88, 0.27),
        (0.20, 1.00, 2.94, 13.51, -18.92, 3.46, 0.25),
        (0.50, 3.00, 2.82, 11.23, -17.82, 3.31, 0.24),
        (0.10, 1.00, 2.60, 7.98, -13.51, 3.01, 0.16),
        (1.00, 10.00, 2.56, 7.90, -13.42, 2.98, 0.17),
        (0.05, 1.00, 2.51, 5.70, -8.50, 2.81, 0.10),
        (0.20, 3.00, 2.51, 6.49, -10.14, 2.86, 0.13),
        (0.50, 10.00, 2.49, 5.66, -8.45, 2.79, 0.11),
        (0.10, 3.00, 2.33, 4.41, -6.76, 2.74, 0.08),
        (0.02, 1.00, 2.24, 3.91, -4.30, 2.76, 0.04),
        (0.05, 3.00, 2.18, 3.65, -3.76, 2.73, 0.04),
        (0.02, 3.00, 2.18, 3.51, -1.52, 2.73, 0.02),
        (0.20, 10.00, 2.16, 3.61, -4.58, 2.73, 0.05),
        (0.10, 10.00, 2.15, 3.47, -2.31, 2.73, 0.03),
        (0.05, 10.00, 2.15, 3.40, -1.16, 2.73, 0.01),
        (0.02, 10.00, 2.15, 3.36, -0.47, 2.73, 0.01),
        (0.00, 1.00, float("nan"), float("nan"), 0.00, 0.00, 0.00),
        (0.00, 3.00, float("nan"), float("nan"), 0.00, 0.00, 0.00),
        (0.00, 10.00, float("nan"), float("nan"), 0.00, 0.00, 0.00),
    ]
    for rank, (shrink, risk_av, sharpe, calmar, mdd, eff, turnover) in enumerate(sweep, start=1):
        degenerate = shrink == 0.00
        gate = "n/a" if degenerate else _gate(sharpe, calmar, mdd, eff, turnover=turnover)
        ledger.append(
            TrialRecord(
                trial_id=f"mv-sweep-shrink{shrink}-risk{risk_av}",
                created_at=CREATED_AT,
                family="MeanVariancePortfolio",
                strategy="shrunk_mean_variance",
                params={"mean_shrink": shrink, "risk_aversion": risk_av, "table_rank": rank},
                dataset_id=DATASET_LONG,
                split_id="full",
                status="discarded" if degenerate else "completed",
                sharpe=None if degenerate else sharpe,
                project=PROJECT,
                venue=VENUE,
                evidence_stage="backtest",
                gate_outcome=gate,
                notes="backfilled from portfolio_mv_param_sweep_hl_1h_current.md"
                + ("; degenerate zero-allocation parameterization" if degenerate else ""),
            )
        )

    # --- portfolio_short_funding_hl_1h_current.md ---
    # (strategy, sharpe, calmar, mdd, eff_assets, gross)
    signed = [
        ("shrunk_mean_variance_signed", 3.86, 35.97, -17.23, 5.42, 1.01),
        ("minimum_variance_signed", 2.92, 12.13, -7.04, 7.16, 1.01),
        ("equal_weight_long", 1.82, 5.31, -25.92, 8.99, 1.00),
        ("inverse_vol_long", 1.42, 3.05, -22.31, 7.47, 1.00),
        ("btc_long", -1.00, -1.33, -35.32, 1.00, 1.00),
    ]
    for strategy, sharpe, calmar, mdd, eff, gross in signed:
        is_benchmark = strategy == "equal_weight_long"
        ledger.append(
            TrialRecord(
                trial_id=f"signed-{strategy}",
                created_at=CREATED_AT,
                family="MeanVariancePortfolioSigned",
                strategy=strategy,
                params={"table": "portfolio_short_funding", "signed": True},
                dataset_id=DATASET_LONG,
                split_id="full",
                status="completed",
                sharpe=sharpe,
                project=PROJECT,
                venue=VENUE,
                evidence_stage="backtest",
                gate_outcome="n/a" if is_benchmark else _gate_signed(sharpe, calmar, mdd, eff, gross),
                notes="backfilled from portfolio_short_funding_hl_1h_current.md"
                + ("; reference benchmark, not a kill-criteria candidate" if is_benchmark else ""),
            )
        )

    # --- pc_neutral_alt_strategies_hl_1h_current.md ---
    # (name, sharpe, calmar, mdd)
    pc_neutral = [
        ("PAIR_L720_PC1_Z2.5_C0.3_N3", 0.71, 1.59, -0.58),
        ("PAIR_L720_PC1_Z2.5_C0.3_N6", 0.71, 1.59, -0.58),
        ("PAIR_L720_PC1_Z2.5_C0.5_N3", 0.71, 1.59, -0.58),
        ("PAIR_L720_PC1_Z2.5_C0.5_N6", 0.71, 1.59, -0.58),
        ("PAIR_L336_PC1_Z1.5_C0.5_N3", 0.61, 1.01, -2.32),
        ("PAIR_L336_PC1_Z1.5_C0.5_N6", 0.61, 1.01, -2.32),
        ("PAIR_L720_PC2_Z2_C0.1_N3", 0.55, 1.20, -2.38),
        ("PAIR_L720_PC2_Z2_C0.1_N6", 0.54, 1.17, -2.38),
        ("PAIR_L336_PC3_Z1.5_C0.3_N3", 0.52, 0.60, -1.02),
        ("PAIR_L336_PC3_Z1.5_C0.3_N6", 0.52, 0.60, -1.02),
        ("PAIR_L336_PC1_Z2.5_C0.3_N3", 0.31, 0.68, -1.00),
        ("PAIR_L336_PC1_Z2.5_C0.3_N6", 0.31, 0.68, -1.00),
    ]
    for rank, (name, sharpe, calmar, mdd) in enumerate(pc_neutral, start=1):
        ledger.append(
            TrialRecord(
                trial_id=f"pc-neutral-{name.lower()}",
                created_at="2026-06-03T00:00:00Z",
                family="PCPairStatArb",
                strategy=name,
                params={"table_rank": rank},
                dataset_id=DATASET_PC,
                split_id="full",
                status="completed",
                sharpe=sharpe,
                project=PROJECT,
                venue=VENUE,
                evidence_stage="backtest",
                gate_outcome="pending",
                notes=(
                    "backfilled from pc_neutral_alt_strategies_hl_1h_current.md; "
                    "no pre-registered kill-criteria decision doc exists for this "
                    "family, so no pass/kill verdict is asserted"
                ),
            )
        )

    # Explicit floor marker, same discipline as hmm-slope-experiment's.
    ledger.append(
        TrialRecord(
            trial_id="reconstruction-gap-marker",
            created_at=CREATED_AT,
            family="(none — marker record)",
            strategy="(none — marker record)",
            params={},
            dataset_id="n/a",
            split_id="n/a",
            status="discarded",
            project=PROJECT,
            venue="n/a",
            evidence_stage="backtest",
            gate_outcome="n/a",
            notes=(
                "Only the 4 surviving result-card tables are counted. Any "
                "parameterizations tried but not written up (or superseded "
                "sweep runs) are not represented. This ledger is a FLOOR on "
                "the true search size, not a complete count."
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
