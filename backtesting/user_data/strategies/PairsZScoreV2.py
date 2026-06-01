"""
PairsZScoreV2 — two-leg cointegration mean-reversion (proper market-neutral pairs).

Differences vs v1 (`PairsZScore.py`)
------------------------------------
v1 was single-leg synthetic: only the BASE coin's leg was traded; the partner
side was ignored. That made v1 effectively long-biased (positive z opens a
short on the base coin only) and recovered ~half of the theoretical spread P&L.

v2 trades **both legs** of the pair in Freqtrade's native multi-pair execution.
The pair is hardcoded as `PAIRS_PAIR_A` vs `PAIRS_PAIR_B` (defaults: SOL vs
DOGE — the only pair with non-trivial cointegration pass-rate in the 5-coin
preflight, 7.4% of windows passing p<0.05 + half-life-in-band).

Both legs share the SAME spread / z-score / cointegration p-value / OU half-life
(computed identically to v1 from the two coins' close prices loaded from disk).
Entry, exit and stop signals fire on the SAME bar on both legs:

    spread_t = log(P_A,t) - β_t · log(P_B,t)
    z_t = (spread_t - mean_30d(spread)) / sd_30d(spread)

    if z_t > +ENTRY_Z   →  short A (A is rich)   AND  long  B (B is cheap)
    if z_t < -ENTRY_Z   →  long  A (A is cheap)  AND  short B (B is rich)
    exit both legs when z crosses 0 (mean reverts)
    stop  both legs when |z| > STOP_Z  (mean-reversion failure)

Sizing
------
Freqtrade can't atomically size paired entries by β within one strategy call,
so v2 uses **equal dollar stakes** on both legs. This is an approximation of
true β-weighted sizing — fine when β is close to 1, but on the 5-coin universe
preflight β is in the ~0.4–1.3 range (rolling), so equal-dollar deviates from
β-weighted by up to ±30% of one leg's notional. Documented in the result card
as a v2 limitation, not a kill criterion. True β-weighted sizing requires
either `custom_stake_amount` per-leg with β passed through `self.custom_info`,
or post-hoc rebalancing. Both are mechanically possible but add execution
complexity that doesn't change the cointegration verdict — and the verdict is
the question this v2 is answering.

Gates
-----
Same as v1:
  - Cointegration p-value (refit every 168 bars on prior 60d) < 0.20
  - OU half-life in [12h, 240h] (= [3, 60] bars at 4h)
  - z-score finite

Cost discipline
---------------
4 × 0.035% = 0.14% per pair-cycle (round-trip both legs at taker). Strategy must
clear that floor net.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy

try:
    from statsmodels.tsa.stattools import coint
    _STATSMODELS_AVAILABLE = True
except ImportError:
    _STATSMODELS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Pair selection — hardcoded to top preflight pair
# ---------------------------------------------------------------------------
# From `scripts/cointegration_preflight.py` on the 5-coin Binance perp window
# (2020-09 → 2026-05, 4h, rolling 1000-bar Engle-Granger, pass = p<0.05 AND
# 12h≤HL≤240h):
#
#     pair       pass_rate
#     SOL-DOGE   0.074    ← chosen
#     ETH-DOGE   0.042
#     BTC-SOL    0.029
#     ETH-AVAX   0.029
#     BTC-AVAX   0.015
#     (others <= 0.015)
#
# Cointegration is essentially absent on this universe; SOL-DOGE is the best of
# a bad lot. Trading multiple pairs simultaneously would compound overlap
# (DOGE appears in ETH-DOGE too) without rescuing the cointegration premise.
PAIR_A_ENV = "PAIRS_V2_A"
PAIR_B_ENV = "PAIRS_V2_B"
DEFAULT_PAIR_A = "SOL"
DEFAULT_PAIR_B = "DOGE"

SPREAD_WINDOW = 30 * 6     # 30d at 4h
BETA_FIT_WINDOW = 60 * 6   # 60d at 4h
ENTRY_Z = 2.0
EXIT_Z = 0.0
STOP_Z = 4.0
COINT_MAX_P = 0.20
HL_MIN_BARS = 3            # 12h at 4h
HL_MAX_BARS = 60           # 240h at 4h


def _data_dir() -> Path:
    return Path("user_data/data/binance/futures")


def _load_close(coin: str, timeframe: str) -> pd.Series:
    f = _data_dir() / f"{coin}_USDT_USDT-{timeframe}-futures.feather"
    if not f.exists():
        return pd.Series(dtype=float)
    df = pd.read_feather(f)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df.set_index("date")["close"].sort_index()


def _compute_spread(close_a: pd.Series, close_b: pd.Series) -> pd.DataFrame:
    """Spread z-score, walk-forward β, OU half-life, rolling cointegration p.

    Walk-forward β: at each bar t, β fit on prior BETA_FIT_WINDOW bars.
    Cointegration p and half-life refit sparsely (every 168 bars) for cost.
    """
    joined = pd.DataFrame({"a": close_a, "b": close_b}).dropna()
    log_a = np.log(joined["a"])
    log_b = np.log(joined["b"])

    beta_series = pd.Series(index=joined.index, dtype=float)
    for i in range(BETA_FIT_WINDOW, len(joined)):
        la = log_a.iloc[i - BETA_FIT_WINDOW:i]
        lb = log_b.iloc[i - BETA_FIT_WINDOW:i]
        if lb.var() == 0:
            continue
        beta = float(np.cov(la, lb, bias=False)[0, 1] / lb.var())
        beta_series.iloc[i] = beta

    spread = log_a - beta_series * log_b
    spread_mean = spread.rolling(SPREAD_WINDOW, min_periods=SPREAD_WINDOW // 2).mean()
    spread_sd = spread.rolling(SPREAD_WINDOW, min_periods=SPREAD_WINDOW // 2).std()
    zscore = (spread - spread_mean) / spread_sd.replace(0, np.nan)

    # Sparse half-life refit (every 168 bars on prior 30d spread window)
    def _hl(s: pd.Series) -> float:
        r = s.dropna()
        if len(r) < 30:
            return float("nan")
        r_lag = r.shift(1).dropna()
        delta = r.diff().dropna()
        delta, r_lag = delta.align(r_lag, join="inner")
        if r_lag.var() == 0:
            return float("nan")
        theta = -float(np.cov(delta, r_lag, bias=False)[0, 1] / r_lag.var())
        if theta <= 0:
            return float("nan")
        return float(np.log(2) / theta)

    hl = pd.Series(index=joined.index, dtype=float)
    pval = pd.Series(index=joined.index, dtype=float)
    if _STATSMODELS_AVAILABLE:
        for i in range(BETA_FIT_WINDOW, len(joined), 168):
            w = spread.iloc[max(0, i - SPREAD_WINDOW):i]
            hl.iloc[i] = _hl(w)
            la_w = log_a.iloc[i - BETA_FIT_WINDOW:i]
            lb_w = log_b.iloc[i - BETA_FIT_WINDOW:i]
            try:
                _t, p, _cv = coint(la_w, lb_w, trend="c", maxlag=24, autolag=None)
                pval.iloc[i] = float(p)
            except Exception:
                pass
        hl = hl.ffill()
        pval = pval.ffill()

    return pd.DataFrame({
        "spread": spread,
        "zscore": zscore,
        "beta": beta_series,
        "half_life": hl,
        "coint_p": pval,
    }, index=joined.index)


class PairsZScoreV2(IStrategy):
    INTERFACE_VERSION = 3
    can_short = True

    timeframe = "4h"
    startup_candle_count = BETA_FIT_WINDOW + SPREAD_WINDOW

    minimal_roi = {"0": 100}
    stoploss = -0.10
    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False

    # Both legs cached after first compute so we don't recompute the spread
    # for each pair's populate_indicators call.
    _spread_cache: pd.DataFrame | None = None

    def informative_pairs(self):
        # The strategy loads both legs' closes directly from disk (the
        # informative API only supports same-timeframe-from-strategy joins
        # and we need a deterministic disk-backed load to match v1's path).
        return []

    # -----------------------------------------------------------------
    # Indicators
    # -----------------------------------------------------------------

    def _get_spread(self) -> pd.DataFrame:
        """Compute (or reuse) the shared spread/z-score DataFrame for the pair."""
        if self._spread_cache is not None:
            return self._spread_cache
        pair_a = os.environ.get(PAIR_A_ENV, DEFAULT_PAIR_A)
        pair_b = os.environ.get(PAIR_B_ENV, DEFAULT_PAIR_B)
        close_a = _load_close(pair_a, self.timeframe)
        close_b = _load_close(pair_b, self.timeframe)
        if close_a.empty or close_b.empty:
            self._spread_cache = pd.DataFrame()
            return self._spread_cache
        self._spread_cache = _compute_spread(close_a, close_b)
        return self._spread_cache

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        spread_df = self._get_spread()
        if spread_df.empty:
            dataframe["zscore"] = np.nan
            dataframe["coint_p"] = np.nan
            dataframe["half_life"] = np.nan
            return dataframe

        df = dataframe.copy()
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.set_index("date")
        df = df.join(spread_df, how="left")
        df = df.reset_index()
        return df

    # -----------------------------------------------------------------
    # Entry / exit — leg sign depends on which coin this is
    # -----------------------------------------------------------------

    def _is_leg_a(self, metadata: dict) -> bool:
        """True if this populate_* call is for leg A (the base of the spread)."""
        pair_a = os.environ.get(PAIR_A_ENV, DEFAULT_PAIR_A)
        return metadata["pair"].split("/")[0] == pair_a

    def _is_leg_b(self, metadata: dict) -> bool:
        pair_b = os.environ.get(PAIR_B_ENV, DEFAULT_PAIR_B)
        return metadata["pair"].split("/")[0] == pair_b

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        z = dataframe.get("zscore")
        p = dataframe.get("coint_p")
        hl = dataframe.get("half_life")
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0

        if z is None or p is None or hl is None:
            return dataframe
        if not (self._is_leg_a(metadata) or self._is_leg_b(metadata)):
            # Pair not in the active pair-of-coins; stay flat.
            return dataframe

        # Gates — shared across both legs (computed from the same spread).
        coint_ok = p.notna() & (p < COINT_MAX_P)
        hl_ok = hl.notna() & (hl >= HL_MIN_BARS) & (hl <= HL_MAX_BARS)
        z_ok = z.notna()

        # Spread = log(A) - β·log(B):
        #   z > 0  → A rich relative to B    → short A, long  B
        #   z < 0  → A cheap relative to B   → long  A, short B
        upper = z_ok & coint_ok & hl_ok & (z > ENTRY_Z) & (z < STOP_Z)
        lower = z_ok & coint_ok & hl_ok & (z < -ENTRY_Z) & (z > -STOP_Z)

        if self._is_leg_a(metadata):
            dataframe.loc[lower, "enter_long"] = 1
            dataframe.loc[upper, "enter_short"] = 1
        else:  # leg B — opposite direction
            dataframe.loc[lower, "enter_short"] = 1
            dataframe.loc[upper, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        z = dataframe.get("zscore")
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        if z is None:
            return dataframe
        if not (self._is_leg_a(metadata) or self._is_leg_b(metadata)):
            return dataframe

        # Mean-reversion exit (z crosses zero) OR widening stop (|z| > STOP_Z).
        # Exit conditions are SYMMETRIC on both legs — they exit together when
        # the spread mean-reverts.
        revert_from_upper = z <= EXIT_Z  # was short A / long B; spread fell
        revert_from_lower = z >= EXIT_Z  # was long A / short B; spread rose
        stop_widen = z.abs() > STOP_Z

        if self._is_leg_a(metadata):
            # Leg A: long-entry was on z<-Z; exit when z >= 0 OR stop
            dataframe.loc[revert_from_lower | stop_widen, "exit_long"] = 1
            # Leg A: short-entry was on z>+Z; exit when z <= 0 OR stop
            dataframe.loc[revert_from_upper | stop_widen, "exit_short"] = 1
        else:  # leg B — opposite signs
            dataframe.loc[revert_from_upper | stop_widen, "exit_long"] = 1
            dataframe.loc[revert_from_lower | stop_widen, "exit_short"] = 1
        return dataframe
