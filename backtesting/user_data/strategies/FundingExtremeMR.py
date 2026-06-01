"""
FundingExtremeMR — counter-funding mean-reversion on Binance perps.

For each coin, load the funding-rate history, compute a z-score against the
rolling 90d mean, and enter a counter-funding position when |z| > 2:
  - funding > 0 (longs paying shorts): short
  - funding < 0 (shorts paying longs): long

Exit at z = 0, time-stop after 3 bars (12h at 4h), or stop at |z| > 4.

Hypothesis: funding extremes mean-revert on ~8h half-life per Le 2026
(arXiv 2605.06405). The strategy harvests the spike. See
`wiki/decisions/008-kill-criteria-funding-mr.md` for pre-registered kill
criteria.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy


FUNDING_DIR_ENV = "CARRY_FUNDING_EXCHANGE"  # "binance" or "hyperliquid"
ZSCORE_WINDOW = 90 * 6   # 90 days at 4h = 540 bars
ENTRY_Z = 2.0
EXIT_Z = 0.0
STOP_Z = 4.0
TIME_STOP_BARS = 3


def _funding_dir() -> Path:
    exch = os.environ.get(FUNDING_DIR_ENV, "binance")
    return Path(f"user_data/data/{exch}/funding")


def _load_funding(coin: str) -> pd.DataFrame:
    """Load coin funding rate as a UTC-indexed series. Returns empty DF if missing."""
    path = _funding_dir() / f"{coin}-funding.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    if "time" not in df.columns or "funding_rate" not in df.columns:
        return pd.DataFrame()
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df[["time", "funding_rate"]].sort_values("time").drop_duplicates("time")


class FundingExtremeMR(IStrategy):
    INTERFACE_VERSION = 3
    can_short = True

    timeframe = "4h"
    startup_candle_count = ZSCORE_WINDOW + 10

    minimal_roi = {"0": 100}
    stoploss = -0.05  # tighter than other strategies; this is a sharp-edge strategy
    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = True

    # -----------------------------------------------------------------
    # Indicators
    # -----------------------------------------------------------------

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        coin = metadata["pair"].split("/")[0]
        funding = _load_funding(coin)
        if funding.empty:
            dataframe["funding_z"] = np.nan
            dataframe["funding_bars_since_entry"] = 0
            return dataframe

        df = dataframe.copy()
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.set_index("date")

        # Resample funding to 4h grid (forward-fill).
        f4h = funding.set_index("time")["funding_rate"].resample("4h").last().ffill()
        # Reindex onto the bar grid.
        f_aligned = f4h.reindex(df.index, method="ffill")

        # Rolling z-score with 90-day window.
        mu = f_aligned.rolling(ZSCORE_WINDOW, min_periods=ZSCORE_WINDOW // 4).mean()
        sd = f_aligned.rolling(ZSCORE_WINDOW, min_periods=ZSCORE_WINDOW // 4).std()
        df["funding_z"] = (f_aligned - mu) / sd.replace(0, np.nan)

        df = df.reset_index()
        return df

    # -----------------------------------------------------------------
    # Entry / exit
    # -----------------------------------------------------------------

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        z = dataframe.get("funding_z")
        if z is None:
            dataframe["enter_long"] = 0
            dataframe["enter_short"] = 0
            return dataframe

        # Counter-funding: funding > 0 → longs paying → take SHORT (revert).
        # funding < 0 → shorts paying → take LONG (revert).
        # Z-score captures "is funding unusually high vs its 90d mean".
        dataframe["enter_short"] = (z > ENTRY_Z) & (z < STOP_Z)
        dataframe["enter_long"] = (z < -ENTRY_Z) & (z > -STOP_Z)
        dataframe["enter_long"] = dataframe["enter_long"].astype(int)
        dataframe["enter_short"] = dataframe["enter_short"].astype(int)
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        z = dataframe.get("funding_z")
        if z is None:
            dataframe["exit_long"] = 0
            dataframe["exit_short"] = 0
            return dataframe
        # Exit long when z reverts above EXIT_Z (=0); exit short when z reverts below 0.
        dataframe["exit_long"] = (z >= EXIT_Z).astype(int)
        dataframe["exit_short"] = (z <= EXIT_Z).astype(int)
        return dataframe

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        """Time-stop at TIME_STOP_BARS = 3 bars (12h at 4h)."""
        bars_in = (current_time - trade.open_date_utc).total_seconds() / (4 * 3600)
        if bars_in >= TIME_STOP_BARS:
            return f"time_stop_{TIME_STOP_BARS}_bars"
        return None
