"""
HmmSmaSlopeV3 — concave (sqrt) slope sizing.

V2 used linear sizing `clip(slope_pct / 0.005, 0, 1)`. Result: bear MDD
4.44% (passes kill rule) but bull return dropped to +33.44% — best/worst
trades matched V1 exactly, meaning the linear penalty was applied to entries
that were profitable in aggregate.

V3 hypothesis: the slope-strength magnitude carries no useful information
beyond sign — so the right sizing curve is **concave**, pulling weak-positive
slopes back toward full size while keeping the zero/negative cutoff. Using
`size_factor = clip((slope_pct / SLOPE_REF) ** 0.5, 0, 1)`:

    slope_pct = 0.001 → V2 size 0.20, V3 size 0.45 (2.25× the V2 size)
    slope_pct = 0.005 → V2 size 1.00, V3 size 1.00 (equal at the strong end)
    slope_pct = ≤ 0   → V2 size 0.00, V3 size 0.00 (both skip)

If the diagnosis is right, V3 should recover most of V2's lost bull return
while keeping bear MDD under the 5.5% kill threshold.
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

# Size scaling. SLOPE_STRONG = the slope-pct value (slope / sma180) at which
# we'd want full size. 0.005 = +0.5% drift of the SMA over the 24h lookback.
# For BTC at $50k that's ~$250 over a day — comfortable bull-trend threshold.
# MIN_SIZE_FACTOR = 0 means we skip the trade entirely when slope is
# nonpositive; the entry signal still triggers but the position never opens.
SLOPE_STRONG = 0.005
MIN_SIZE_FACTOR = 0.0
SIZING_EXPONENT = 0.5  # 0.5 = sqrt (concave); 1.0 = linear (V2); 2.0 = convex


class HmmSmaSlopeV3(IStrategy):
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
                "hmmlearn is required for HmmSmaSlopeV3. "
                "Activate the freqtrade venv and run: pip install hmmlearn"
            )

        # ---- SMA slope (matches SmaRegime180) ----
        dataframe["sma180"] = ta.SMA(dataframe, timeperiod=SMA_PERIOD)
        dataframe["sma180_slope"] = (
            dataframe["sma180"] - dataframe["sma180"].shift(SLOPE_LOOKBACK)
        )
        # Slope as a fraction of the SMA itself — scale-free across coins.
        dataframe["slope_pct"] = dataframe["sma180_slope"] / dataframe["sma180"]
        # Concave sizing: raise the slope ratio to SIZING_EXPONENT (< 1 = concave).
        # Negative slope clipped to 0 BEFORE the power to avoid complex numbers.
        ratio = (dataframe["slope_pct"] / SLOPE_STRONG).clip(lower=0.0)
        dataframe["size_factor"] = (
            (ratio ** SIZING_EXPONENT).clip(lower=MIN_SIZE_FACTOR, upper=1.0)
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
        # Entry signal is HMM-only — slope handled in custom_stake_amount.
        dataframe.loc[
            (dataframe["bull_prob"] >= BULL_THRESHOLD)
            & (dataframe["bull_prob"].shift(1) < BULL_THRESHOLD),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit on EITHER HMM-low OR slope-flipped-negative (matches V1).
        dataframe.loc[
            (dataframe["bull_prob"] < EXIT_THRESHOLD)
            | (dataframe["sma180_slope"] <= 0),
            "exit_long",
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
        """
        Scale position by the slope strength at the current bar.

        Returning 0 (or anything < min_stake) signals freqtrade to skip the
        trade — which is what we want when slope is nonpositive.
        """
        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if df is None or df.empty:
            return proposed_stake

        size_factor = df["size_factor"].iloc[-1]
        if pd.isna(size_factor) or size_factor <= 0:
            return 0.0  # freqtrade will skip — slope is nonpositive

        return proposed_stake * float(size_factor)
