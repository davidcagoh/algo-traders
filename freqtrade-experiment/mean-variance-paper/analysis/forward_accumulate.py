#!/usr/bin/env python3
"""
Independent forward accumulation for `shrunk_mean_variance_signed`, run
locally instead of depending on Ethan's broken Vercel monitor. Re-runs
`run_portfolio_short_funding.simulate()` — unchanged, already proven in the
2026-08-06 liquid-majors proxy backtest — over the real, growing Hyperliquid
price/funding history each day; `simulate()` is a pure deterministic
function of the whole history array (rebalance computed via
`(day_index - lookback) % rebalance_days == 0`), so re-running it daily and
reading the latest metrics is mathematically identical to what a persistent
incremental tick would produce, with no external state store needed.

Two thresholds pre-registered before any data collection started (see
`wiki/decisions-archive.md` 2026-08-06), checked on every run:
  - Kill If (decision-012): no minimum sample required.
  - DSR-binding checkpoint at N=250 daily observations (`wiki/learnings-archive.md`
    2026-05-20) — before that, any Sharpe/DSR read is a running number, not
    evidence. Neither check answers the cross-cycle gate question, which
    requires observing a second, structurally different regime and cannot
    be resolved by any amount of within-regime accumulation.

Usage:
  ./.venv/bin/python analysis/forward_accumulate.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "evaluation-framework"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluation.ledger import TrialLedger, TrialRecord  # noqa: E402
from run_portfolio_baselines import UNIVERSE_JSON, load_daily_prices, load_universe  # noqa: E402
from run_portfolio_short_funding import load_daily_funding, metrics, simulate  # noqa: E402

DSR_BINDING_N_DAYS = 250
REGIME_START = "2025-10-01"  # post-BTC-October-2025-peak regime scope

# TON is delisted from Hyperliquid (confirmed via /info meta 2026-08-06,
# isDelisted=true; its OHLCV data stops 2026-06-15) and cannot be part of a
# forward-tradable book regardless of what this script does. Excluded from
# the original 9-coin universe (mean_variance_hl_universe.json) for forward
# accumulation only — that file is left unmodified as a historical backtest
# record.
EXCLUDED_COINS = {"TON"}

LOOKBACK = 60
REBALANCE_DAYS = 7
FEE = 0.00035
CAP = 0.20
GROSS_LIMIT = 1.0
MEAN_SHRINK = 0.50
RISK_AVERSION = 1.0
TURNOVER_PENALTY = 0.05
SIGNED_METHOD = "shrunk_mean_variance_signed"
BASELINE_METHOD = "equal_weight_long"

LEDGER_PATH = Path(__file__).resolve().parent / "forward_accumulation_ledger.jsonl"


def check_dsr_binding(n_days: int) -> bool:
    return n_days >= DSR_BINDING_N_DAYS


def check_kill_criteria(signed: dict, baseline: dict) -> dict:
    reasons = []
    if signed["sharpe"] <= baseline["sharpe"]:
        reasons.append("sharpe does not beat equal-weight baseline")
    if signed["calmar"] <= baseline["calmar"]:
        reasons.append("calmar does not beat equal-weight baseline")
    if signed["max_drawdown_pct"] < baseline["max_drawdown_pct"]:
        reasons.append("max drawdown worse than equal-weight baseline")
    if signed["avg_effective_assets"] < 3:
        reasons.append("average effective assets below 3")
    if signed["avg_turnover_per_rebalance"] > 1.25:
        reasons.append("average turnover per rebalance above 1.25")
    return {"killed": len(reasons) > 0, "reasons": reasons}


def to_trial_record(
    metrics: dict,
    run_date: str,
    n_days: int,
    dsr_binding: bool,
    kill_check: dict,
) -> TrialRecord:
    gate_outcome = "killed" if kill_check["killed"] else "pending"
    notes = (
        f"forward accumulation, regime-scoped to {REGIME_START}; "
        f"dsr_binding={dsr_binding} (N={n_days}/{DSR_BINDING_N_DAYS}); "
        f"killed={kill_check['killed']}"
    )
    if kill_check["reasons"]:
        notes += "; reasons=" + ", ".join(kill_check["reasons"])

    return TrialRecord(
        trial_id=f"forward-{SIGNED_METHOD}-{run_date}",
        created_at=datetime.now(timezone.utc).isoformat(),
        family="MeanVariancePortfolioSigned",
        strategy=SIGNED_METHOD,
        params={
            "lookback": LOOKBACK,
            "rebalance_days": REBALANCE_DAYS,
            "fee": FEE,
            "cap": CAP,
            "gross_limit": GROSS_LIMIT,
            "mean_shrink": MEAN_SHRINK,
            "risk_aversion": RISK_AVERSION,
            "turnover_penalty": TURNOVER_PENALTY,
            "regime_start": REGIME_START,
        },
        dataset_id=f"hyperliquid-9coin-forward-{run_date}",
        split_id="forward",
        status="completed",
        sharpe=metrics["sharpe"],
        n_obs=n_days,
        notes=notes,
        project="mean-variance-paper",
        venue="hyperliquid",
        evidence_stage="paper",
        gate_outcome=gate_outcome,
    )


def main() -> int:
    coins = [c for c in load_universe(UNIVERSE_JSON) if c not in EXCLUDED_COINS]
    prices = load_daily_prices(coins)
    price_returns = prices.pct_change().dropna()
    price_returns = price_returns[price_returns.index >= REGIME_START]
    funding = load_daily_funding(coins, price_returns.index)

    signed_returns, signed_weights, signed_costs, signed_funding_pnl = simulate(
        price_returns,
        funding,
        SIGNED_METHOD,
        LOOKBACK,
        REBALANCE_DAYS,
        FEE,
        CAP,
        GROSS_LIMIT,
        MEAN_SHRINK,
        RISK_AVERSION,
        TURNOVER_PENALTY,
    )
    baseline_returns, baseline_weights, baseline_costs, baseline_funding_pnl = simulate(
        price_returns,
        funding,
        BASELINE_METHOD,
        LOOKBACK,
        REBALANCE_DAYS,
        FEE,
        CAP,
        GROSS_LIMIT,
        MEAN_SHRINK,
        RISK_AVERSION,
        TURNOVER_PENALTY,
    )

    signed_metrics = metrics(
        signed_returns, signed_weights, signed_costs, signed_funding_pnl, REBALANCE_DAYS
    )
    baseline_metrics = metrics(
        baseline_returns, baseline_weights, baseline_costs, baseline_funding_pnl, REBALANCE_DAYS
    )

    n_days = signed_metrics["days"]
    dsr_binding = check_dsr_binding(n_days)
    kill_check = check_kill_criteria(signed_metrics, baseline_metrics)

    run_date = datetime.now(timezone.utc).date().isoformat()
    record = to_trial_record(signed_metrics, run_date, n_days, dsr_binding, kill_check)

    ledger = TrialLedger(LEDGER_PATH)
    ledger.append(record, allow_rerun=True)

    print(f"N={n_days} days (DSR binding: {dsr_binding}, need {DSR_BINDING_N_DAYS})")
    print(f"sharpe={signed_metrics['sharpe']:.3f} vs baseline={baseline_metrics['sharpe']:.3f}")
    print(f"killed={kill_check['killed']}" + (f" ({'; '.join(kill_check['reasons'])})" if kill_check["reasons"] else ""))
    print(f"wrote {LEDGER_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
