"""
HmmRegime4Rolling — walk-forward refit version of HmmRegime4.

Same 4-state Gaussian HMM, same features (24-bar log return + log-volume z-score),
same entry/exit thresholds. The only change: the HMM is re-fit every REFIT_EVERY
bars on the trailing FIT_WINDOW bars, and the bull-state posterior at bar t is
computed using only data through bar t. No look-ahead.

This isolates the variable that the original HmmRegime4 result conflated:
"is the HMM regime structure stable enough to be useful out-of-sample?"

Compare back-to-back vs HmmRegime4 (same window, same params) — if win rate
holds above ~35%, the signal is real. If it collapses, the look-ahead was the
alpha.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy

try:
    from hmmlearn.hmm import GaussianHMM
    _HMM_AVAILABLE = True
except ImportError:
    _HMM_AVAILABLE = False

RETURN_WINDOW = 24
N_COMPONENTS = 4
BULL_THRESHOLD = 0.65
EXIT_THRESHOLD = 0.45

FIT_WINDOW = 1000      # trailing bars used to fit the HMM at each refit point
REFIT_EVERY = 168      # refit cadence (1h bars → ~weekly)


class HmmRegime4Rolling(IStrategy):
    INTERFACE_VERSION = 3
    can_short = False

    timeframe = "1h"
    startup_candle_count = FIT_WINDOW + RETURN_WINDOW

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
                "hmmlearn is required for HmmRegime4Rolling. "
                "Activate the freqtrade venv and run: pip install hmmlearn"
            )

        log_return = np.log(
            dataframe["close"] / dataframe["close"].shift(RETURN_WINDOW)
        )
        log_vol = np.log(dataframe["volume"].clip(lower=1e-9))
        # NB: z-score is computed on full series — this is feature normalisation,
        # not a regime label. The HMM itself never sees future bars.
        log_vol_z = (log_vol - log_vol.mean()) / max(log_vol.std(), 1e-9)

        dataframe["_log_return"] = log_return
        dataframe["_log_vol_z"] = log_vol_z

        valid_mask = dataframe[["_log_return", "_log_vol_z"]].notna().all(axis=1)
        dataframe["bull_prob"] = np.nan

        valid_idx = np.where(valid_mask.values)[0]
        if len(valid_idx) < FIT_WINDOW + REFIT_EVERY:
            return dataframe

        X_full = dataframe[["_log_return", "_log_vol_z"]].values

        # Walk forward: at each refit point r (in original-row index space),
        # fit on X[r-FIT_WINDOW:r], then score bars [r, r+REFIT_EVERY).
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
            # Score bars [r, seg_end). For each, posterior uses data through that
            # bar only (no look-ahead): we run predict_proba on the trailing
            # window up to and including the bar, take the last entry.
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
            & (dataframe["bull_prob"].shift(1) < BULL_THRESHOLD),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            dataframe["bull_prob"] < EXIT_THRESHOLD,
            "exit_long",
        ] = 1
        return dataframe
