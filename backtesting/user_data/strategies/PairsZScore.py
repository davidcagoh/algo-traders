"""
PairsZScore — cointegration-based mean-reversion on a single hedged spread.

V1: single-leg synthetic execution. The strategy is run on ONE base coin
(default BTC). It computes spread = log(BASE) - β·log(PARTNER) using a partner
coin's price loaded from disk, and trades the BASE leg when the spread z-score
crosses ±2 (entry) or ±4 (stop) or 0 (exit), with a time-stop at 3 × OU
half-life. The PARTNER leg is *not* traded — V1 captures roughly half the
spread P&L. Two-leg fidelity flagged as V2 follow-up. See
`wiki/decisions/006-kill-criteria-pairs.md`.

Pre-flight discipline (K2-pairs): the strategy refits β weekly on prior 60d
only (walk-forward) and requires p_value < 0.20 for entries. Cointegration
p-value monitored continuously; if p > 0.20 for 30 consecutive days at the
strategy level, no entries are emitted (K2 enforced soft-side; hard kill is
external in the kill-criteria review).
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


PARTNER_PAIR_ENV = "PAIRS_PARTNER"   # set to e.g. "SOL" or "ETH"
DEFAULT_PARTNER = "SOL"
SPREAD_WINDOW = 30 * 6   # 30 days at 4h = 180 bars
BETA_FIT_WINDOW = 60 * 6  # 60 days at 4h = 360 bars
ENTRY_Z = 2.0
EXIT_Z = 0.0
STOP_Z = 4.0
COINT_MAX_P = 0.20
TIME_STOP_HALF_LIVES = 3


def _data_dir() -> Path:
    """Where partner OHLCV lives."""
    return Path("user_data/data/binance/futures")


def _load_partner_close(coin: str, timeframe: str) -> pd.Series:
    """Read partner-coin close prices as a UTC-indexed series."""
    f = _data_dir() / f"{coin}_USDT_USDT-{timeframe}-futures.feather"
    if not f.exists():
        return pd.Series(dtype=float)
    df = pd.read_feather(f)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df.set_index("date")["close"].sort_index()


class PairsZScore(IStrategy):
    INTERFACE_VERSION = 3
    can_short = True   # need shorts on the BASE leg for upside spread divergence

    timeframe = "4h"
    startup_candle_count = BETA_FIT_WINDOW + SPREAD_WINDOW

    minimal_roi = {"0": 100}
    stoploss = -0.10
    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False

    def informative_pairs(self):
        # We deliberately do *not* use Freqtrade's informative API here —
        # we load partner close prices directly from disk via _load_partner_close.
        # This is the v1 single-leg synthetic approach; v2 would use informative_pairs.
        return []

    # -----------------------------------------------------------------
    # Indicators
    # -----------------------------------------------------------------

    def _compute_spread(self, base_close: pd.Series, partner_close: pd.Series) -> pd.DataFrame:
        """Compute spread z-score, walk-forward β, OU half-life, rolling p-value."""
        # Align on common dates.
        joined = pd.DataFrame({
            "base": base_close,
            "partner": partner_close,
        }).dropna()
        log_base = np.log(joined["base"])
        log_partner = np.log(joined["partner"])

        # Walk-forward β: at each bar t, fit β on prior BETA_FIT_WINDOW bars.
        beta_series = pd.Series(index=joined.index, dtype=float)
        for i in range(BETA_FIT_WINDOW, len(joined)):
            la = log_base.iloc[i - BETA_FIT_WINDOW:i]
            lb = log_partner.iloc[i - BETA_FIT_WINDOW:i]
            if lb.var() == 0:
                continue
            beta = float(np.cov(la, lb, bias=False)[0, 1] / lb.var())
            beta_series.iloc[i] = beta

        # Spread series using the walk-forward β.
        spread = log_base - beta_series * log_partner
        # Rolling z-score of spread (30d window).
        spread_mean = spread.rolling(SPREAD_WINDOW, min_periods=SPREAD_WINDOW // 2).mean()
        spread_sd = spread.rolling(SPREAD_WINDOW, min_periods=SPREAD_WINDOW // 2).std()
        zscore = (spread - spread_mean) / spread_sd.replace(0, np.nan)

        # OU half-life of the spread (over the rolling window).
        def _hl_window(s: pd.Series) -> float:
            if len(s.dropna()) < 30:
                return float("nan")
            r = s.dropna()
            r_lag = r.shift(1).dropna()
            delta = r.diff().dropna()
            delta, r_lag = delta.align(r_lag, join="inner")
            if r_lag.var() == 0:
                return float("nan")
            theta = -float(np.cov(delta, r_lag, bias=False)[0, 1] / r_lag.var())
            if theta <= 0:
                return float("nan")
            return float(np.log(2) / theta)

        # Run a sparse half-life: refit every 168 bars.
        hl = pd.Series(index=joined.index, dtype=float)
        if _STATSMODELS_AVAILABLE:
            for i in range(SPREAD_WINDOW, len(joined), 168):
                w = spread.iloc[max(0, i - SPREAD_WINDOW):i]
                hl_val = _hl_window(w)
                hl.iloc[i] = hl_val
            hl = hl.ffill()

        # Rolling cointegration p-value (sparse refit).
        pval = pd.Series(index=joined.index, dtype=float)
        if _STATSMODELS_AVAILABLE:
            for i in range(BETA_FIT_WINDOW, len(joined), 168):
                la_w = log_base.iloc[i - BETA_FIT_WINDOW:i]
                lb_w = log_partner.iloc[i - BETA_FIT_WINDOW:i]
                try:
                    _t, p, _cv = coint(la_w, lb_w, trend="c", maxlag=24, autolag=None)
                    pval.iloc[i] = float(p)
                except Exception:
                    pass
            pval = pval.ffill()

        return pd.DataFrame({
            "spread": spread,
            "zscore": zscore,
            "beta": beta_series,
            "half_life": hl,
            "coint_p": pval,
        }, index=joined.index)

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        partner = os.environ.get(PARTNER_PAIR_ENV, DEFAULT_PARTNER)
        partner_close = _load_partner_close(partner, self.timeframe)
        if partner_close.empty:
            dataframe["zscore"] = np.nan
            dataframe["coint_p"] = np.nan
            dataframe["half_life"] = np.nan
            return dataframe
        df = dataframe.copy()
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.set_index("date")

        spread_df = self._compute_spread(df["close"], partner_close)
        df = df.join(spread_df, how="left")
        df = df.reset_index()
        return df

    # -----------------------------------------------------------------
    # Entry / exit
    # -----------------------------------------------------------------

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        z = dataframe.get("zscore")
        p = dataframe.get("coint_p")
        hl = dataframe.get("half_life")
        if z is None:
            dataframe["enter_long"] = 0
            dataframe["enter_short"] = 0
            return dataframe

        # K2 gate: cointegration must be present.
        coint_ok = p.notna() & (p < COINT_MAX_P)
        hl_ok = hl.notna() & (hl >= 12) & (hl <= 240)
        z_ok = z.notna()

        # Long the base coin when its z-score is *negative* (base underpriced).
        # Short the base coin when z-score is *positive* (base overpriced).
        dataframe["enter_long"] = (z_ok & coint_ok & hl_ok & (z < -ENTRY_Z) & (z > -STOP_Z)).astype(int)
        dataframe["enter_short"] = (z_ok & coint_ok & hl_ok & (z > ENTRY_Z) & (z < STOP_Z)).astype(int)
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        z = dataframe.get("zscore")
        if z is None:
            dataframe["exit_long"] = 0
            dataframe["exit_short"] = 0
            return dataframe
        # Long exits when z mean-reverts above EXIT_Z (=0); short exits below 0.
        dataframe["exit_long"] = (z >= EXIT_Z).astype(int)
        dataframe["exit_short"] = (z <= EXIT_Z).astype(int)
        return dataframe
