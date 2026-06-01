"""
FundingCarry — threshold-gated long-only funding-rate carry on Hyperliquid perps.

Signal: 24-hour rolling mean of the hourly funding rate. When the rolling mean
goes sufficiently negative (shorts paying longs), enter long — collecting
funding payments while waiting for a mean-reversion bounce. Exit when funding
turns positive again or when the rolling mean crosses an exit band.

Hypothesis (Inan 2025, "Predictability of Funding Rates"):
  - Sustained negative funding indicates short crowdedness on the venue.
  - Crowded shorts revert: either price bounces, or shorts pay longs to hold,
    or both. Both scenarios pay the long-only carry trader.

Long-only by repo convention (Freqtrade `can_short=False`). A symmetric
short-leg version is the natural follow-up if this signal works.

Funding data:
  Hyperliquid hourly funding rates collected by `scripts/download_hyperliquid.py`,
  written to `user_data/data/hyperliquid/funding/<COIN>-funding.parquet`.
  Columns: time (UTC), coin, funding_rate, premium.
"""
from __future__ import annotations

import os
from pathlib import Path
import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy

# Funding-rate thresholds (per hour, decimal):
#   Hyperliquid floor / typical baseline: ~0.00125% / hour ≈ +0.0000125
#   "Sustained negative" entry: rolling 24h mean < ENTRY_THRESHOLD
#   Exit when rolling mean crosses back above EXIT_THRESHOLD.
ENTRY_THRESHOLD = -0.00001   # roughly the 5th-percentile of 24h rolling mean
EXIT_THRESHOLD = 0.00002      # ~25th percentile — exit once funding normalises
ROLLING_WINDOW_HOURS = 24


def _funding_dir() -> Path:
    # Resolve per-call so backtests can switch venues via env without reimporting.
    exchange = os.environ.get("CARRY_FUNDING_EXCHANGE", "hyperliquid")
    return Path(f"user_data/data/{exchange}/funding")


def _load_funding(coin: str) -> pd.DataFrame:
    path = _funding_dir() / f"{coin}-funding.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df[["time", "funding_rate"]].sort_values("time").drop_duplicates("time")
    return df


def _coin_from_pair(pair: str) -> str:
    # "BTC/USDC:USDC" -> "BTC"
    return pair.split("/")[0]


class FundingCarry(IStrategy):
    INTERFACE_VERSION = 3
    can_short = False

    timeframe = "1h"
    startup_candle_count = ROLLING_WINDOW_HOURS + 5

    minimal_roi = {"0": 100}  # exit on signal only
    stoploss = -0.10
    trailing_stop = False

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        coin = _coin_from_pair(metadata["pair"])
        funding = _load_funding(coin)

        if funding.empty:
            dataframe["funding_rate"] = np.nan
            dataframe["funding_roll"] = np.nan
            return dataframe

        # Align hourly funding to the OHLCV index. Both are 1h but funding
        # timestamps drift by milliseconds — floor both to the hour and merge.
        hours = pd.to_datetime(dataframe["date"], utc=True).dt.floor("h")
        funding["_hour"] = funding["time"].dt.floor("h")
        funding_by_hour = (
            funding.groupby("_hour")["funding_rate"].mean()
        )
        aligned = hours.map(funding_by_hour).ffill()

        dataframe["funding_rate"] = aligned.values
        dataframe["funding_roll"] = (
            aligned.rolling(ROLLING_WINDOW_HOURS, min_periods=ROLLING_WINDOW_HOURS).mean().values
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Enter when 24h rolling funding crosses below ENTRY_THRESHOLD.
        cond = (
            (dataframe["funding_roll"] < ENTRY_THRESHOLD)
            & (dataframe["funding_roll"].shift(1) >= ENTRY_THRESHOLD)
        )
        dataframe.loc[cond, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit when rolling funding rises back above EXIT_THRESHOLD.
        dataframe.loc[
            dataframe["funding_roll"] >= EXIT_THRESHOLD, "exit_long"
        ] = 1
        return dataframe
