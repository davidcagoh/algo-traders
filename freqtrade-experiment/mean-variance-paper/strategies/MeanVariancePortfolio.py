"""
MeanVariancePortfolio — long-only mean-variance weights on a fixed HL universe.

Universe (low-correlation basket from universe selection, 2026-06-01):
  BTC, HYPE, PAXG, TRX, WLFI, VVV, TON, ZRO, XPL

At each weekly rebalance (168 x 1h bars), estimate expected returns and the
covariance matrix from trailing daily close-to-close returns, then solve for
maximum Sharpe weights (long-only, fully invested). Weights are applied via
custom_stake_amount; positions are flattened and re-opened on rebalance bars.

Data: data/hyperliquid/futures/*-1h-futures.feather
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from pandas import DataFrame
from scipy.optimize import minimize

from freqtrade.strategy import IStrategy

UNIVERSE = ["BTC", "HYPE", "PAXG", "TRX", "WLFI", "VVV", "TON", "ZRO", "XPL"]
DATA_DIR = Path(__file__).resolve().parents[2] / "hmm-slope-experiment" / "research" / "data" / "hyperliquid" / "futures"

LOOKBACK_DAYS = 42
REBALANCE_BARS = 168
MIN_WEIGHT = 0.02
COV_RIDGE = 1e-5
RISK_FREE_DAILY = 0.0

_WEIGHTS_CACHE: pd.DataFrame | None = None


def _pair_to_coin(pair: str) -> str:
    return pair.split("/")[0]


def _load_hourly_close(coin: str) -> pd.Series:
    path = DATA_DIR / f"{coin}_USDC_USDC-1h-futures.feather"
    if not path.exists():
        return pd.Series(dtype=float)
    df = pd.read_feather(path)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df.set_index("date")["close"].sort_index()


def _max_sharpe_long_only(mu: np.ndarray, cov: np.ndarray) -> np.ndarray:
    n = len(mu)
    if n == 0:
        return np.array([])
    cov = cov + np.eye(n) * COV_RIDGE

    def neg_sharpe(w: np.ndarray) -> float:
        ret = float(w @ mu) - RISK_FREE_DAILY
        vol = float(np.sqrt(w @ cov @ w))
        if vol < 1e-12:
            return 0.0
        return -ret / vol

    w0 = np.ones(n) / n
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    bounds = [(0.0, 1.0)] * n
    res = minimize(
        neg_sharpe,
        w0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-9},
    )
    if not res.success or np.any(res.x < -1e-6):
        return w0
    w = np.clip(res.x, 0.0, 1.0)
    s = w.sum()
    return w / s if s > 0 else w0


def _solve_weights_at(rets: pd.DataFrame, as_of: pd.Timestamp) -> pd.Series:
    window = rets.loc[:as_of].iloc[-LOOKBACK_DAYS:]
    window = window.dropna(axis=1, how="any")
    if len(window) < LOOKBACK_DAYS // 2 or window.shape[1] < 2:
        return pd.Series(0.0, index=UNIVERSE)
    mu = window.mean().values
    cov = window.cov().values
    w = _max_sharpe_long_only(mu, cov)
    out = pd.Series(0.0, index=UNIVERSE)
    for coin, wt in zip(window.columns, w):
        out[coin] = float(wt)
    return out


def _build_hourly_weights() -> pd.DataFrame:
    closes = {c: _load_hourly_close(c) for c in UNIVERSE}
    hourly = pd.DataFrame(closes).dropna(how="all").sort_index()
    if hourly.empty:
        return pd.DataFrame(columns=UNIVERSE)

    daily = hourly.resample("1D").last().dropna(how="all")
    rets = daily.pct_change().dropna(how="all")

    rows: list[pd.Series] = []
    index: list[pd.Timestamp] = []
    last_w = pd.Series(0.0, index=UNIVERSE)

    for bar_idx, ts in enumerate(hourly.index):
        if bar_idx >= LOOKBACK_DAYS * 24 and bar_idx % REBALANCE_BARS == 0:
            day_ts = ts.floor("D")
            if day_ts in rets.index or day_ts > rets.index[0]:
                last_w = _solve_weights_at(rets, day_ts)
        rows.append(last_w.copy())
        index.append(ts)

    return pd.DataFrame(rows, index=index, columns=UNIVERSE).fillna(0.0)


def get_weights_schedule() -> pd.DataFrame:
    global _WEIGHTS_CACHE
    if _WEIGHTS_CACHE is None:
        _WEIGHTS_CACHE = _build_hourly_weights()
    return _WEIGHTS_CACHE


class MeanVariancePortfolio(IStrategy):
    INTERFACE_VERSION = 3
    can_short = False

    max_open_trades = 9

    timeframe = "1h"
    startup_candle_count = LOOKBACK_DAYS * 24 + REBALANCE_BARS

    minimal_roi = {"0": 100}
    stoploss = -0.25
    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False

    def _active_weights(self, current_time: datetime) -> dict[str, float]:
        sched = get_weights_schedule()
        ts = pd.Timestamp(current_time).tz_convert("UTC")
        if ts in sched.index:
            row = sched.loc[ts]
        else:
            prior = sched.index[sched.index <= ts]
            if len(prior) == 0:
                return {}
            row = sched.loc[prior[-1]]
        return {
            c: float(row[c])
            for c in UNIVERSE
            if c in row.index and float(row[c]) >= MIN_WEIGHT
        }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        coin = _pair_to_coin(metadata["pair"])
        if coin not in UNIVERSE:
            dataframe["target_weight"] = 0.0
            dataframe["rebalance_anchor"] = 0
            return dataframe

        weights = get_weights_schedule()
        if weights.empty or coin not in weights.columns:
            dataframe["target_weight"] = 0.0
            dataframe["rebalance_anchor"] = 0
            return dataframe

        df = dataframe.copy()
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.set_index("date")

        coin_w = weights[coin].reindex(df.index, method="ffill").fillna(0.0)
        df["target_weight"] = coin_w

        rebal = weights.diff().abs().sum(axis=1).fillna(1.0) > 1e-6
        first_pos = weights.sum(axis=1).gt(0)
        if first_pos.any():
            rebal.loc[first_pos.idxmax()] = True
        df["rebalance_anchor"] = rebal.reindex(df.index).fillna(False).astype(int)

        df = df.reset_index()
        return df

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        tw = dataframe.get("target_weight")
        anchor = dataframe.get("rebalance_anchor")
        if tw is None or anchor is None:
            dataframe["enter_long"] = 0
            return dataframe
        dataframe["enter_long"] = (
            (anchor == 1) & (tw >= MIN_WEIGHT)
        ).astype(int)
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        tw = dataframe.get("target_weight")
        anchor = dataframe.get("rebalance_anchor")
        if tw is None or anchor is None:
            dataframe["exit_long"] = 0
            return dataframe
        # Flatten every rebalance; re-enter below if still in the book.
        dataframe["exit_long"] = (
            (anchor == 1) & (tw.shift(1) >= MIN_WEIGHT)
        ).astype(int)
        return dataframe

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: Optional[float],
        max_stake: float,
        leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs,
    ) -> float:
        coin = _pair_to_coin(pair)
        active = self._active_weights(current_time)
        total_w = sum(active.values())
        w = active.get(coin, 0.0)
        if total_w <= 0 or w <= 0:
            return 0.0
        wallet = self.wallets.get_total_stake_amount()
        stake = wallet * (w / total_w)
        if min_stake is not None and stake < min_stake:
            return 0.0
        return float(min(stake, max_stake))
