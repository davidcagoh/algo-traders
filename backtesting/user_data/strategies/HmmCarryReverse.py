"""
HmmCarryReverse — reverse-sign variant of HmmCarry.

Hypothesis (2026-05-16):
  The 05-10 HmmCarry post-mortem found that HMM-bull AND funding-negative is
  *anti-complementary*: HMM is a reactive regime detector, funding is a
  forward-looking sentiment proxy, and their intersection systematically picks
  late-cycle bull lag against early-cycle bear lead — buying tops.

  Inverting the funding gate (require funding-POSITIVE instead of negative)
  recasts the conjunction as confirmation rather than contradiction:
    - HMM-bull says "trailing return-feature evidence agrees with bull."
    - funding-positive says "longs are paying shorts; positioning is healthy
      bull, traders willing to pay carry."
  Both pointing the same direction *should* be additive, not subtractive.

  If signals truly align as confirmation, expect higher win rate, fewer but
  cleaner trades, less BTC catastrophe. If still bad, the funding signal is
  just noise in this universe.

Long-only by repo convention. Walk-forward HMM refit identical to HmmCarry.
Only the funding-gate sign is flipped vs HmmCarry.
"""
from __future__ import annotations

import os
from pathlib import Path
import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy

try:
    from hmmlearn.hmm import GaussianHMM
    _HMM_AVAILABLE = True
except ImportError:
    _HMM_AVAILABLE = False

# HMM block (matches HmmRegime4Rolling / HmmCarry)
RETURN_WINDOW = 24
N_COMPONENTS = 4
BULL_THRESHOLD = 0.65
BULL_EXIT_THRESHOLD = 0.45
FIT_WINDOW = 1000
REFIT_EVERY = 168

# Carry block — REVERSED SIGN vs HmmCarry.
# HmmCarry: enter when funding_roll < -0.00001 (shorts paying, contrarian).
# HmmCarryReverse: enter when funding_roll > +0.00001 (longs paying = healthy bull, confirmation).
ENTRY_FUNDING = 0.00001
EXIT_FUNDING = -0.00002
ROLLING_WINDOW_HOURS = 24


def _funding_dir() -> Path:
    exchange = os.environ.get("CARRY_FUNDING_EXCHANGE", "hyperliquid")
    return Path(f"user_data/data/{exchange}/funding")


def _load_funding(coin: str) -> pd.DataFrame:
    path = _funding_dir() / f"{coin}-funding.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df[["time", "funding_rate"]].sort_values("time").drop_duplicates("time")


class HmmCarryReverse(IStrategy):
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
            raise ImportError("hmmlearn required: pip install hmmlearn")

        # ---- HMM block: walk-forward bull_prob (identical to HmmCarry) ----
        log_return = np.log(
            dataframe["close"] / dataframe["close"].shift(RETURN_WINDOW)
        )
        log_vol = np.log(dataframe["volume"].clip(lower=1e-9))
        log_vol_z = (log_vol - log_vol.mean()) / max(log_vol.std(), 1e-9)

        dataframe["_log_return"] = log_return
        dataframe["_log_vol_z"] = log_vol_z

        valid_mask = dataframe[["_log_return", "_log_vol_z"]].notna().all(axis=1)
        valid_idx = np.where(valid_mask.values)[0]
        bull_prob = np.full(len(dataframe), np.nan)

        if len(valid_idx) >= FIT_WINDOW + REFIT_EVERY:
            X_full = dataframe[["_log_return", "_log_vol_z"]].values
            first_refit = valid_idx[0] + FIT_WINDOW

            for r in range(first_refit, len(dataframe), REFIT_EVERY):
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

                seg_end = min(r + REFIT_EVERY, len(dataframe))
                for t in range(r, seg_end):
                    if np.isnan(X_full[t]).any():
                        continue
                    try:
                        post = model.predict_proba(X_full[fit_start:t + 1])[-1]
                    except Exception:
                        continue
                    bull_prob[t] = post[bull_states].sum()

        dataframe["bull_prob"] = bull_prob

        # ---- Carry block: funding_roll (identical computation to HmmCarry) ----
        coin = metadata["pair"].split("/")[0]
        funding = _load_funding(coin)
        if funding.empty:
            dataframe["funding_roll"] = np.nan
        else:
            hours = pd.to_datetime(dataframe["date"], utc=True).dt.floor("h")
            funding["_hour"] = funding["time"].dt.floor("h")
            by_hour = funding.groupby("_hour")["funding_rate"].mean()
            aligned = hours.map(by_hour).ffill()
            dataframe["funding_roll"] = (
                aligned.rolling(ROLLING_WINDOW_HOURS, min_periods=ROLLING_WINDOW_HOURS)
                .mean()
                .values
            )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Conjunction: bull regime AND POSITIVE carry (longs paying = trend confirmation),
        # entering on the bar where the joint regime newly turns on.
        joint = (
            (dataframe["bull_prob"] >= BULL_THRESHOLD)
            & (dataframe["funding_roll"] > ENTRY_FUNDING)
        )
        prev_joint = joint.shift(1).fillna(False)
        dataframe.loc[joint & ~prev_joint, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit when either signal flips: HMM leaves bull, or funding turns
        # negative beyond the exit band (longs no longer paying = momentum lost).
        exit_cond = (
            (dataframe["bull_prob"] < BULL_EXIT_THRESHOLD)
            | (dataframe["funding_roll"] <= EXIT_FUNDING)
        )
        dataframe.loc[exit_cond, "exit_long"] = 1
        return dataframe
