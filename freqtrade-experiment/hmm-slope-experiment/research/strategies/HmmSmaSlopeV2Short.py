"""
HmmSmaSlopeV2Short — short-side mirror of HmmSmaSlopeV2. BACKTEST-ONLY DRAFT.

V2 is long-only: HMM bull_prob crossing up gates entry, slope_pct scales
size, exit on bull_prob dropping or slope flipping negative. This variant
mirrors that structure onto shorts rather than reusing V2's long logic with
`can_short` flipped — the entry/exit conditions are genuinely different
events, not sign-flips of the same signal.

Hypothesis: define bear_prob = 1 - bull_prob (HMM posterior mass on
non-bull states). Enter short when bear_prob crosses up through
BEAR_THRESHOLD; size by NEGATIVE slope strength (strong downtrend = full
size, flat/positive slope = skip); exit on bear_prob dropping below
EXIT_THRESHOLD or slope flipping positive.

Untested. Needs its own backtest pass before any paper deployment — Hyperliquid
funding was running +10.95% annualised on all 6 pairs at the V2 live-run start
(2026-05-21), which changes short-side expectancy independently of signal
quality (see execution/records/results/2026-05-21-hl-paper-start.md). Not
directly comparable to V2's live numbers on that basis alone.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

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

# HMM block (matches HmmRegime4Rolling / V2 / V3)
RETURN_WINDOW = 24
N_COMPONENTS = 4
BEAR_THRESHOLD = 0.65   # bear_prob crossing this from below triggers short entry
EXIT_THRESHOLD = 0.45   # bear_prob dropping below this triggers short exit
FIT_WINDOW = 1000
REFIT_EVERY = 168

# SMA-slope block (matches SmaRegime180 / V2 / V3)
SMA_PERIOD = 180
SLOPE_LOOKBACK = 6

# Size scaling, mirrored: strong NEGATIVE slope -> full size, slope >= 0 -> skip.
SLOPE_STRONG = 0.005
MIN_SIZE_FACTOR = 0.0


class HmmSmaSlopeV2Short(IStrategy):
    INTERFACE_VERSION = 3
    can_short = True

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
                "hmmlearn is required for HmmSmaSlopeV2Short. "
                "Activate the freqtrade venv and run: pip install hmmlearn"
            )

        # ---- SMA slope (matches SmaRegime180) ----
        dataframe["sma180"] = ta.SMA(dataframe, timeperiod=SMA_PERIOD)
        dataframe["sma180_slope"] = (
            dataframe["sma180"] - dataframe["sma180"].shift(SLOPE_LOOKBACK)
        )
        dataframe["slope_pct"] = dataframe["sma180_slope"] / dataframe["sma180"]
        # Mirrored sizing: strong negative slope -> full size, slope >= 0 -> 0.
        dataframe["size_factor"] = (
            (-dataframe["slope_pct"] / SLOPE_STRONG)
            .clip(lower=MIN_SIZE_FACTOR, upper=1.0)
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
        dataframe["bear_prob"] = np.nan

        valid_idx = np.where(valid_mask.values)[0]
        if len(valid_idx) < FIT_WINDOW + REFIT_EVERY:
            return dataframe

        X_full = dataframe[["_log_return", "_log_vol_z"]].values

        first_refit = valid_idx[0] + FIT_WINDOW
        last_row = len(dataframe)
        bear_prob = np.full(last_row, np.nan)

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

            # bear_states = states with non-positive mean return (mirrors V2's
            # bull_states = mean return > 0).
            bear_states = [i for i in range(N_COMPONENTS) if model.means_[i, 0] <= 0]
            if not bear_states:
                bear_states = [int(np.argmin(model.means_[:, 0]))]

            seg_end = min(r + REFIT_EVERY, last_row)
            for t in range(r, seg_end):
                if np.isnan(X_full[t]).any():
                    continue
                X_score = X_full[fit_start:t + 1]
                try:
                    post = model.predict_proba(X_score)[-1]
                except Exception:
                    continue
                bear_prob[t] = post[bear_states].sum()

        dataframe["bear_prob"] = bear_prob
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["bear_prob"] >= BEAR_THRESHOLD)
            & (dataframe["bear_prob"].shift(1) < BEAR_THRESHOLD),
            "enter_short",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["bear_prob"] < EXIT_THRESHOLD)
            | (dataframe["sma180_slope"] >= 0),
            "exit_short",
        ] = 1
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
        """Scale short size by downtrend strength; skip when slope is nonnegative."""
        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if df is None or df.empty:
            return proposed_stake

        size_factor = df["size_factor"].iloc[-1]
        if pd.isna(size_factor) or size_factor <= 0:
            return 0.0

        return proposed_stake * float(size_factor)
