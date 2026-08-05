"""
HmmSmaSlope — HmmRegime4Rolling entry signal gated by SmaRegime180's slope filter.

Thesis: HmmRegime4Rolling-multi captures bulls beautifully (+65% 2023-25 CEX bull
window, all 6 pairs positive, Calmar 27.73) but is bear-blind (−5.6% in bears
with the "regime-4 bull state" mis-firing). SmaRegime180's slope gate has the
opposite shape — it stays flat through bears at the cost of low signal density.

Hypothesis: gating HMM entries by `sma180_slope > 0` should suppress HMM's
bear-window false-positives without sacrificing most of the bull capture.

If this works, the two-segment Pareto frontier (Sma bear-resilient, HMM-multi
bull-amplifying) collapses to a single point that dominates both endpoints.

Parameters are identical to HmmRegime4Rolling (HMM) and SmaRegime180 (slope
gate) — no tuning. This is a clean A/B; any improvement is from the gate, not
fresh parameter search.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy

try:
    from hmmlearn.hmm import GaussianHMM
    _HMM_AVAILABLE = True
except ImportError:
    _HMM_AVAILABLE = False

# HMM block (matches HmmRegime4Rolling)
RETURN_WINDOW = 24
N_COMPONENTS = 4
BULL_THRESHOLD = 0.65
EXIT_THRESHOLD = 0.45
FIT_WINDOW = 1000
REFIT_EVERY = 168

# SMA-slope block (matches SmaRegime180)
SMA_PERIOD = 180
SLOPE_LOOKBACK = 6


class HmmSmaSlope(IStrategy):
    INTERFACE_VERSION = 3
    can_short = False

    timeframe = "4h"
    startup_candle_count = max(FIT_WINDOW + RETURN_WINDOW, SMA_PERIOD + SLOPE_LOOKBACK)

    minimal_roi = {"0": 100}
    stoploss = -0.10
    trailing_stop = False

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if not _HMM_AVAILABLE:
            raise ImportError(
                "hmmlearn is required for HmmSmaSlope. "
                "Activate the freqtrade venv and run: pip install hmmlearn"
            )

        # ---- SMA slope (matches SmaRegime180) ----
        dataframe["sma180"] = ta.SMA(dataframe, timeperiod=SMA_PERIOD)
        dataframe["sma180_slope"] = (
            dataframe["sma180"] - dataframe["sma180"].shift(SLOPE_LOOKBACK)
        )

        # ---- Rolling HMM (matches HmmRegime4Rolling) ----
        log_return = np.log(
            dataframe["close"] / dataframe["close"].shift(RETURN_WINDOW)
        )
        log_vol = np.log(dataframe["volume"].clip(lower=1e-9))
        log_vol_z = (log_vol - log_vol.mean()) / max(log_vol.std(), 1e-9)

        dataframe["_log_return"] = log_return
        dataframe["_log_vol_z"] = log_vol_z

        valid_mask = dataframe[["_log_return", "_log_vol_z"]].notna().all(axis=1)
        dataframe["bull_prob"] = np.nan

        valid_idx = np.where(valid_mask.values)[0]
        if len(valid_idx) < FIT_WINDOW + REFIT_EVERY:
            return dataframe

        X_full = dataframe[["_log_return", "_log_vol_z"]].values

        first_refit = valid_idx[0] + FIT_WINDOW
        last_row = len(dataframe)
        bull_prob = np.full(last_row, np.nan)

        for r in range(first_refit, last_row, REFIT_EVERY):
            fit_start = r - FIT_WINDOW
            X_fit = X_full[fit_start:r]
            if np.isnan(X_fit).any():
                continue
            try:
                model = GaussianHMM(
                    n_components=N_COMPONENTS,
                    covariance_type="full",
                    n_iter=200,
                    random_state=42,
                )
                model.fit(X_fit)
            except Exception:
                continue

            bull_states = [i for i in range(N_COMPONENTS) if model.means_[i, 0] > 0]
            if not bull_states:
                bull_states = [int(np.argmax(model.means_[:, 0]))]

            seg_end = min(r + REFIT_EVERY, last_row)
            for t in range(r, seg_end):
                if np.isnan(X_full[t]).any():
                    continue
                X_score = X_full[fit_start:t + 1]
                try:
                    post = model.predict_proba(X_score)[-1]
                except Exception:
                    continue
                bull_prob[t] = post[bull_states].sum()

        dataframe["bull_prob"] = bull_prob
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["bull_prob"] >= BULL_THRESHOLD)
            & (dataframe["bull_prob"].shift(1) < BULL_THRESHOLD)
            & (dataframe["sma180_slope"] > 0),  # the gate
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit on EITHER HMM-low OR slope-flipped-negative. Slope exit catches
        # regime turns that the reactive HMM lags on.
        dataframe.loc[
            (dataframe["bull_prob"] < EXIT_THRESHOLD)
            | (dataframe["sma180_slope"] <= 0),
            "exit_long",
        ] = 1
        return dataframe
