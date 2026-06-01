"""
HmmSmaSlopeV2 — HmmSmaSlope with continuous slope-based position sizing.

V1 used a binary slope gate (`sma180_slope > 0` blocks entry). Bull-window
result on the 6-coin Binance basket showed the gate cost 15pp of return
(+65.36% → +50.47%) by filtering 46% of HMM-bull entries.

V2 replaces the binary gate with a continuous size multiplier derived from
the slope strength. HMM's entry signal still fires unchanged; the slope's
sign and magnitude scale the *size* of the position, not its existence.

Hypothesis: weak/negative slopes during bears get small sizes (limiting bleed),
strong slopes during bulls get full size (preserving capture). If correct,
the bull cost shrinks below 15pp while bear MDD stays under HMM-multi's 14.7%.

Per `wiki/decisions/004-kill-criteria-sma-regime-180.md` continuous-shrinkage
framing (Davies–Ravagnani style): position size is a smooth function of the
regime evidence, not a binary kill switch.
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


class HmmSmaSlopeV2(IStrategy):
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
                "hmmlearn is required for HmmSmaSlopeV2. "
                "Activate the freqtrade venv and run: pip install hmmlearn"
            )

        # ---- SMA slope (matches SmaRegime180) ----
        dataframe["sma180"] = ta.SMA(dataframe, timeperiod=SMA_PERIOD)
        dataframe["sma180_slope"] = (
            dataframe["sma180"] - dataframe["sma180"].shift(SLOPE_LOOKBACK)
        )
        # Slope as a fraction of the SMA itself — scale-free across coins.
        dataframe["slope_pct"] = dataframe["sma180_slope"] / dataframe["sma180"]
        # Size factor in [MIN_SIZE_FACTOR, 1.0]. clip handles weak/negative slope.
        dataframe["size_factor"] = (
            (dataframe["slope_pct"] / SLOPE_STRONG)
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
