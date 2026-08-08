import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "evaluation-framework"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))

from forward_state import (
    advance_one_day,
    backfill_from_simulation,
    cumulative_metrics,
    load_daily_log,
    load_state,
    save_state,
    write_daily_log,
)

COINS = ["A", "B"]


def _flat_window(n_days: int, start: str = "2026-01-01") -> tuple[pd.DataFrame, pd.DataFrame]:
    idx = pd.date_range(start, periods=n_days, freq="D", tz="UTC")
    price_returns = pd.DataFrame(0.0, index=idx, columns=COINS)
    funding = pd.DataFrame(0.0, index=idx, columns=COINS)
    return price_returns, funding


def test_load_state_returns_empty_when_missing(tmp_path):
    state = load_state(tmp_path / "nope.json", COINS)

    assert state["signed"]["equity"] == 1.0
    assert state["signed"]["day_counter"] == 0
    assert state["signed"]["last_date"] is None
    assert set(state["signed"]["notional"]) == set(COINS)


def test_save_and_load_state_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    state = {
        "signed": {"equity": 1.05, "notional": {"A": 0.5, "B": 0.5}, "day_counter": 3, "last_date": "2026-01-03"},
        "baseline": {"equity": 1.0, "notional": {"A": 0.5, "B": 0.5}, "day_counter": 3, "last_date": "2026-01-03"},
    }

    save_state(path, state)
    loaded = load_state(path, COINS)

    assert loaded == state


def test_daily_log_roundtrip(tmp_path):
    path = tmp_path / "log.jsonl"
    rows = [{"date": "2026-01-01", "signed_return": 0.01}, {"date": "2026-01-02", "signed_return": -0.02}]

    write_daily_log(path, rows)

    assert load_daily_log(path) == rows


def test_advance_one_day_increments_day_counter_and_grows_notional_on_gain():
    price_returns, funding = _flat_window(65)
    price_returns.iloc[-1] = 0.10  # today's row: +10% for both coins

    state = {
        "signed": {"equity": 1.0, "notional": {"A": 0.5, "B": 0.5}, "day_counter": 5, "last_date": "2026-02-01"},
        "baseline": {"equity": 1.0, "notional": {"A": 0.5, "B": 0.5}, "day_counter": 5, "last_date": "2026-02-01"},
    }

    new_state, log_row = advance_one_day(
        state, COINS, price_returns, funding,
        lookback=60, rebalance_days=7, fee=0.0, cap=1.0, gross_limit=1.0,
        mean_shrink=0.5, risk_aversion=1.0, turnover_penalty=0.0,
        signed_method="equal_weight_long", baseline_method="equal_weight_long",
    )

    assert new_state["signed"]["day_counter"] == 6
    assert new_state["signed"]["equity"] > 1.0
    assert log_row["signed_return"] == pytest.approx(0.10)
    assert log_row["date"] == price_returns.index[-1].date().isoformat()


def test_advance_one_day_rebalance_cadence_survives_constant_window_length():
    """
    The bug this module fixes: if rebalance timing were derived from the
    window-relative index instead of a persisted day_counter, a window that
    stays a constant length every day (Hyperliquid's cap) would freeze the
    rebalance decision for "today" forever. day_counter must drive it instead.
    """
    price_returns, funding = _flat_window(65)

    state = {
        "signed": {"equity": 1.0, "notional": {c: 0.0 for c in COINS}, "day_counter": 6, "last_date": "d"},
        "baseline": {"equity": 1.0, "notional": {c: 0.0 for c in COINS}, "day_counter": 6, "last_date": "d"},
    }

    new_state, _ = advance_one_day(
        state, COINS, price_returns, funding,
        lookback=60, rebalance_days=7, fee=0.0, cap=1.0, gross_limit=1.0,
        mean_shrink=0.5, risk_aversion=1.0, turnover_penalty=0.0,
        signed_method="equal_weight_long", baseline_method="equal_weight_long",
    )

    # day_counter=6 % 7 == 6 (not a rebalance day) -> notional stays zero
    assert new_state["signed"]["notional"]["A"] == 0.0

    state["signed"]["day_counter"] = 7
    new_state2, _ = advance_one_day(
        state, COINS, price_returns, funding,
        lookback=60, rebalance_days=7, fee=0.0, cap=1.0, gross_limit=1.0,
        mean_shrink=0.5, risk_aversion=1.0, turnover_penalty=0.0,
        signed_method="equal_weight_long", baseline_method="equal_weight_long",
    )

    # day_counter=7 % 7 == 0 -> rebalance fires, notional becomes non-zero
    assert new_state2["signed"]["notional"]["A"] != 0.0


def test_backfill_from_simulation_seeds_day_counter_and_log_length():
    idx = pd.date_range("2026-01-01", periods=5, freq="D", tz="UTC")
    signed_returns = pd.Series([0.01, 0.02, -0.01, 0.03, 0.0], index=idx)
    signed_weights = pd.DataFrame({"A": [0.5] * 5, "B": [0.5] * 5}, index=idx)
    signed_costs = pd.Series(0.0, index=idx)
    signed_funding = pd.Series(0.0, index=idx)

    state, rows = backfill_from_simulation(
        COINS,
        signed_returns, signed_weights, signed_costs, signed_funding,
        signed_returns, signed_weights, signed_costs, signed_funding,
    )

    assert len(rows) == 5
    assert state["signed"]["day_counter"] == 5
    assert state["signed"]["last_date"] == "2026-01-05"
    assert state["signed"]["equity"] == pytest.approx(float((1.0 + signed_returns).cumprod().iloc[-1]))


def test_cumulative_metrics_grows_with_appended_rows():
    idx = pd.date_range("2026-01-01", periods=3, freq="D", tz="UTC")
    rows = [
        {
            "date": d.date().isoformat(),
            "signed_return": 0.01, "signed_cost": 0.0, "signed_funding": 0.0,
            "signed_weights": {"A": 0.5, "B": 0.5},
            "baseline_return": 0.0, "baseline_cost": 0.0, "baseline_funding": 0.0,
            "baseline_weights": {"A": 0.5, "B": 0.5},
        }
        for d in idx
    ]

    signed_metrics, baseline_metrics = cumulative_metrics(rows, COINS, rebalance_days=7)

    assert signed_metrics["days"] == 3
    assert baseline_metrics["days"] == 3
