"""
Persistent day-by-day forward-accumulation state.

`simulate()` in `run_portfolio_short_funding.py` recomputes an entire
equity/notional path from scratch over whatever price/funding window is
passed in. That's correct for a fixed backtest, but Hyperliquid's public API
only ever returns the most recent ~208 days (5000 hourly candles) — the
window slides forward by ~1 day every day, so re-running `simulate()` over
"the latest window" each day burns one day of history off the back for
every new day gained at the front. Post-lookback N stays pinned at
window_length - lookback forever and can never reach the DSR-binding floor
(confirmed empirically: two consecutive daily runs both landed on N=148).

This module carries `equity` / `notional` / `day_counter` forward in a
checkpoint file and applies one day's price/funding tick at a time, using
the same per-step arithmetic as `simulate()`'s loop body. Each day's
realized return is appended to an independent, strictly-growing log —
decoupled from whatever raw window Hyperliquid happens to return that day.
`day_counter` (not the window-relative index) drives the rebalance-day
modulo, so weekly rebalancing cadence stays correct indefinitely.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from run_portfolio_short_funding import metrics, target_weights


def _empty_leg_state(coins: list[str]) -> dict:
    return {
        "equity": 1.0,
        "notional": {c: 0.0 for c in coins},
        "day_counter": 0,
        "last_date": None,
    }


def load_state(path: Path, coins: list[str]) -> dict:
    if not path.exists():
        return {"signed": _empty_leg_state(coins), "baseline": _empty_leg_state(coins)}
    return json.loads(path.read_text())


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, sort_keys=True))


def load_daily_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_daily_log(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n")


def append_daily_log(path: Path, row: dict) -> None:
    with path.open("a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")


def _step_leg(
    leg_state: dict,
    method: str,
    coins: list[str],
    hist: pd.DataFrame,
    today_price: np.ndarray,
    today_funding: np.ndarray,
    rebalance_days: int,
    fee: float,
    cap: float,
    gross_limit: float,
    mean_shrink: float,
    risk_aversion: float,
    turnover_penalty: float,
) -> tuple[dict, dict]:
    equity = leg_state["equity"]
    notional = np.array([leg_state["notional"][c] for c in coins])
    day_counter = leg_state["day_counter"]

    start_equity = equity
    current_weights = notional / equity if equity > 0 else np.zeros_like(notional)
    cost_frac = 0.0

    if day_counter % rebalance_days == 0:
        new_weights = target_weights(
            method, hist, current_weights, cap, gross_limit,
            mean_shrink, risk_aversion, turnover_penalty,
        )
        turnover = float(np.abs(new_weights - current_weights).sum())
        cost = fee * turnover * equity
        equity -= cost
        cost_frac = cost / start_equity if start_equity > 0 else 0.0
        notional = new_weights * equity

    fund_pnl = float(np.sum(notional * -today_funding))
    price_pnl = float(np.sum(notional * today_price))
    notional = notional * (1.0 + today_price)
    equity += price_pnl + fund_pnl
    day_return = equity / start_equity - 1.0 if start_equity > 0 else 0.0
    weights_today = notional / equity if equity > 0 else np.zeros_like(notional)
    funding_frac = fund_pnl / start_equity if start_equity > 0 else 0.0

    new_leg_state = {
        "equity": float(equity),
        "notional": {c: float(v) for c, v in zip(coins, notional)},
        "day_counter": day_counter + 1,
        "last_date": None,  # set by caller
    }
    day_fields = {
        "return": day_return,
        "cost": cost_frac,
        "funding": funding_frac,
        "weights": {c: float(w) for c, w in zip(coins, weights_today)},
    }
    return new_leg_state, day_fields


def advance_one_day(
    state: dict,
    coins: list[str],
    price_returns: pd.DataFrame,
    funding: pd.DataFrame,
    lookback: int,
    rebalance_days: int,
    fee: float,
    cap: float,
    gross_limit: float,
    mean_shrink: float,
    risk_aversion: float,
    turnover_penalty: float,
    signed_method: str,
    baseline_method: str,
) -> tuple[dict, dict]:
    today = price_returns.index[-1]
    hist = price_returns.iloc[-lookback - 1:-1] - funding.iloc[-lookback - 1:-1]
    today_price = price_returns.loc[today].to_numpy()
    today_funding = funding.loc[today].to_numpy()

    signed_state, signed_day = _step_leg(
        state["signed"], signed_method, coins, hist, today_price, today_funding,
        rebalance_days, fee, cap, gross_limit, mean_shrink, risk_aversion, turnover_penalty,
    )
    baseline_state, baseline_day = _step_leg(
        state["baseline"], baseline_method, coins, hist, today_price, today_funding,
        rebalance_days, fee, cap, gross_limit, mean_shrink, risk_aversion, turnover_penalty,
    )

    date_str = today.date().isoformat()
    signed_state["last_date"] = date_str
    baseline_state["last_date"] = date_str

    log_row = {
        "date": date_str,
        "signed_return": signed_day["return"],
        "signed_cost": signed_day["cost"],
        "signed_funding": signed_day["funding"],
        "signed_weights": signed_day["weights"],
        "baseline_return": baseline_day["return"],
        "baseline_cost": baseline_day["cost"],
        "baseline_funding": baseline_day["funding"],
        "baseline_weights": baseline_day["weights"],
    }
    new_state = {"signed": signed_state, "baseline": baseline_state}
    return new_state, log_row


def backfill_from_simulation(
    coins: list[str],
    signed_returns: pd.Series,
    signed_weights: pd.DataFrame,
    signed_costs: pd.Series,
    signed_funding: pd.Series,
    baseline_returns: pd.Series,
    baseline_weights: pd.DataFrame,
    baseline_costs: pd.Series,
    baseline_funding: pd.Series,
) -> tuple[dict, list[dict]]:
    """
    One-time migration: seed the persistent log/state from a classic
    full-window `simulate()` call, so the days still visible in today's
    ~208-day window aren't lost when the window slides tomorrow. From the
    next run onward, `advance_one_day` takes over and N grows for real.
    """
    rows = []
    for date in signed_returns.index:
        date_str = date.date().isoformat()
        rows.append({
            "date": date_str,
            "signed_return": float(signed_returns.loc[date]),
            "signed_cost": float(signed_costs.loc[date]),
            "signed_funding": float(signed_funding.loc[date]),
            "signed_weights": {c: float(signed_weights.loc[date, c]) for c in coins},
            "baseline_return": float(baseline_returns.loc[date]),
            "baseline_cost": float(baseline_costs.loc[date]),
            "baseline_funding": float(baseline_funding.loc[date]),
            "baseline_weights": {c: float(baseline_weights.loc[date, c]) for c in coins},
        })

    signed_equity = float((1.0 + signed_returns).cumprod().iloc[-1])
    baseline_equity = float((1.0 + baseline_returns).cumprod().iloc[-1])
    last_date_str = signed_returns.index[-1].date().isoformat()

    state = {
        "signed": {
            "equity": signed_equity,
            "notional": {c: float(signed_weights.iloc[-1][c] * signed_equity) for c in coins},
            "day_counter": len(signed_returns),
            "last_date": last_date_str,
        },
        "baseline": {
            "equity": baseline_equity,
            "notional": {c: float(baseline_weights.iloc[-1][c] * baseline_equity) for c in coins},
            "day_counter": len(baseline_returns),
            "last_date": last_date_str,
        },
    }
    return state, rows


def cumulative_metrics(log_rows: list[dict], coins: list[str], rebalance_days: int) -> tuple[dict, dict]:
    dates = pd.to_datetime([row["date"] for row in log_rows])

    def _series(key: str) -> pd.Series:
        return pd.Series([row[key] for row in log_rows], index=dates)

    def _weights(key: str) -> pd.DataFrame:
        return pd.DataFrame([row[key] for row in log_rows], index=dates).reindex(columns=coins, fill_value=0.0)

    signed_metrics = metrics(
        _series("signed_return"), _weights("signed_weights"),
        _series("signed_cost"), _series("signed_funding"), rebalance_days,
    )
    baseline_metrics = metrics(
        _series("baseline_return"), _weights("baseline_weights"),
        _series("baseline_cost"), _series("baseline_funding"), rebalance_days,
    )
    return signed_metrics, baseline_metrics
