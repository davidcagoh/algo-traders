"""
HmmRegime4 — 4-state Gaussian HMM regime filter on BTC 1h bars.

Replaces the SMA slope gate in SmaRegime180 with a probabilistic regime
posterior from hmmlearn. Hypothesis: a 4-state HMM (low-vol bull, high-vol
bull, low-vol bear, high-vol bear) produces more adaptive regime labels than
a fixed SMA window, improving win rate from SmaRegime180's ~22% toward 40%+.

Features fed to the HMM:
  - rolling 24-bar log return  (price momentum)
  - log normalised volume      (participation / flow)

Entry:  P(any bull state) crosses above BULL_THRESHOLD (0.65).
Exit:   P(any bull state) falls below EXIT_THRESHOLD (0.45).

NOTE — look-ahead caveat: populate_indicators fits HMM on the full dataset
at once. This is valid for an initial comparison vs SmaRegime180 (which was
also fit on the same window). A production-grade implementation would use a
rolling walk-forward refit; that's a follow-up once we know whether HMM
signal quality justifies the added complexity.

Requires:  pip install hmmlearn
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

RETURN_WINDOW = 24     # rolling lookback for log return feature (bars = hours on 1h TF)
N_COMPONENTS = 4       # {low-vol bull, high-vol bull, low-vol bear, high-vol bear}
BULL_THRESHOLD = 0.65  # P(bull) to trigger entry
EXIT_THRESHOLD = 0.45  # P(bull) below which position is closed
MIN_FIT_BARS = 500     # minimum history before fitting; shorter series yield poor HMMs


class HmmRegime4(IStrategy):
    INTERFACE_VERSION = 3
    can_short = False

    timeframe = "1h"
    startup_candle_count = MIN_FIT_BARS + RETURN_WINDOW

    minimal_roi = {"0": 100}  # exit on regime signal only
    stoploss = -0.10
    trailing_stop = False

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if not _HMM_AVAILABLE:
            raise ImportError(
                "hmmlearn is required for HmmRegime4. "
                "Activate the freqtrade venv and run: pip install hmmlearn"
            )

        log_return = np.log(
            dataframe["close"] / dataframe["close"].shift(RETURN_WINDOW)
        )
        # Normalise volume to z-score within the available window to reduce
        # scale sensitivity; use log first to symmetrise the distribution.
        log_vol = np.log(dataframe["volume"].clip(lower=1e-9))
        log_vol_z = (log_vol - log_vol.mean()) / max(log_vol.std(), 1e-9)

        dataframe["_log_return"] = log_return
        dataframe["_log_vol_z"] = log_vol_z

        valid = dataframe[["_log_return", "_log_vol_z"]].notna().all(axis=1)
        dataframe["bull_prob"] = np.nan

        if valid.sum() < MIN_FIT_BARS:
            return dataframe

        X = dataframe.loc[valid, ["_log_return", "_log_vol_z"]].values

        model = GaussianHMM(
            n_components=N_COMPONENTS,
            covariance_type="full",
            n_iter=200,
            random_state=42,
        )
        try:
            model.fit(X)
        except Exception:
            # Some coins produce non-PD covariance under "full". Leave bull_prob
            # NaN so no entries fire on this pair.
            return dataframe

        # Identify bull states by positive mean log return.
        bull_states = [i for i in range(N_COMPONENTS) if model.means_[i, 0] > 0]
        if not bull_states:
            # Fallback: treat the single highest-mean state as bull.
            bull_states = [int(np.argmax(model.means_[:, 0]))]

        posteriors = model.predict_proba(X)  # shape (n_valid, N_COMPONENTS)
        bull_prob = posteriors[:, bull_states].sum(axis=1)

        dataframe.loc[valid, "bull_prob"] = bull_prob
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Enter on the bar where bull_prob crosses above BULL_THRESHOLD.
        dataframe.loc[
            (dataframe["bull_prob"] >= BULL_THRESHOLD)
            & (dataframe["bull_prob"].shift(1) < BULL_THRESHOLD),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit whenever bull_prob drops below EXIT_THRESHOLD.
        dataframe.loc[
            dataframe["bull_prob"] < EXIT_THRESHOLD,
            "exit_long",
        ] = 1
        return dataframe
