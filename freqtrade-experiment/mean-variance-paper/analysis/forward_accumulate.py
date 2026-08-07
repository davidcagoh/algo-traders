#!/usr/bin/env python3
"""
Independent forward accumulation for `shrunk_mean_variance_signed`, run
locally instead of depending on Ethan's broken Vercel monitor.

Originally re-ran `run_portfolio_short_funding.simulate()` over the current
price/funding window each day, on the assumption that a re-fetch is
"mathematically identical" to a persistent incremental tick. That assumption
was wrong: Hyperliquid's public API only ever returns the most recent ~208
days (5000 hourly candles), so the window slides forward ~1 day per day
instead of growing — one day gained at the front, one lost at the back.
Confirmed empirically 2026-08-06/07: two consecutive daily runs both landed
on exactly N=148 (208 - 60 lookback), not N=148 then N=149. That construction
can never reach N=250.

Fixed by moving to `forward_state.py`: equity/notional/day_counter persist
in a checkpoint file and advance one real day at a time
(`forward_state.advance_one_day`), decoupled from whatever raw window
Hyperliquid happens to return that day. A one-time backfill
(`forward_state.backfill_from_simulation`) seeds the log from today's still-
available ~208-day window before it starts sliding away tomorrow, so the 148
days already observed aren't thrown out.

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
from forward_state import (  # noqa: E402
    advance_one_day,
    backfill_from_simulation,
    cumulative_metrics,
    load_daily_log,
    load_state,
    save_state,
    write_daily_log,
)
from run_portfolio_baselines import UNIVERSE_JSON, load_daily_prices, load_universe  # noqa: E402
from run_portfolio_short_funding import load_daily_funding, simulate  # noqa: E402

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
STATE_PATH = Path(__file__).resolve().parent / "forward_state.json"
DAILY_LOG_PATH = Path(__file__).resolve().parent / "forward_daily_log.jsonl"


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

    today_str = price_returns.index[-1].date().isoformat()
    state = load_state(STATE_PATH, coins)
    log_rows = load_daily_log(DAILY_LOG_PATH)

    if state["signed"]["last_date"] is None:
        # One-time migration: capture the days still visible in today's
        # ~208-day window before it slides away tomorrow.
        signed_returns, signed_weights, signed_costs, signed_funding_pnl = simulate(
            price_returns, funding, SIGNED_METHOD, LOOKBACK, REBALANCE_DAYS,
            FEE, CAP, GROSS_LIMIT, MEAN_SHRINK, RISK_AVERSION, TURNOVER_PENALTY,
        )
        baseline_returns, baseline_weights, baseline_costs, baseline_funding_pnl = simulate(
            price_returns, funding, BASELINE_METHOD, LOOKBACK, REBALANCE_DAYS,
            FEE, CAP, GROSS_LIMIT, MEAN_SHRINK, RISK_AVERSION, TURNOVER_PENALTY,
        )
        state, log_rows = backfill_from_simulation(
            coins,
            signed_returns, signed_weights, signed_costs, signed_funding_pnl,
            baseline_returns, baseline_weights, baseline_costs, baseline_funding_pnl,
        )
        save_state(STATE_PATH, state)
        write_daily_log(DAILY_LOG_PATH, log_rows)
        print(f"backfilled {len(log_rows)} days from today's window into {DAILY_LOG_PATH}")
    elif state["signed"]["last_date"] == today_str:
        print(f"already accumulated {today_str}, skipping (N={len(log_rows)})")
        n_days = len(log_rows)
        signed_metrics, baseline_metrics = cumulative_metrics(log_rows, coins, REBALANCE_DAYS)
        print(f"N={n_days} days (DSR binding: {check_dsr_binding(n_days)}, need {DSR_BINDING_N_DAYS})")
        print(f"sharpe={signed_metrics['sharpe']:.3f} vs baseline={baseline_metrics['sharpe']:.3f}")
        return 0
    else:
        state, log_row = advance_one_day(
            state, coins, price_returns, funding, LOOKBACK, REBALANCE_DAYS,
            FEE, CAP, GROSS_LIMIT, MEAN_SHRINK, RISK_AVERSION, TURNOVER_PENALTY,
            SIGNED_METHOD, BASELINE_METHOD,
        )
        log_rows.append(log_row)
        save_state(STATE_PATH, state)
        write_daily_log(DAILY_LOG_PATH, log_rows)
        print(f"advanced one day → {DAILY_LOG_PATH}")

    signed_metrics, baseline_metrics = cumulative_metrics(log_rows, coins, REBALANCE_DAYS)
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
