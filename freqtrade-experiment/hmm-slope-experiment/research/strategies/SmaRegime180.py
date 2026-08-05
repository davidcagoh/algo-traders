"""
SmaRegime180 — SmaRegime720 scaled for 4h bars.

Identical logic to SmaRegime720; constants adjusted so the time-equivalent
windows are preserved:
  - SMA_PERIOD 720 → 180  (720h / 4 = 180 × 4h bars = 30d)
  - SLOPE_LOOKBACK 24 → 6  (24h / 4 = 6 × 4h bars = 24h)
  - timeframe 1h → 4h

Purpose: bull-window validation for the SmaRegime family. 4h data covers
Jan 2024 → Apr 2026 (~833 days), including the 2024–2025 bull run. H7 in
learnings.md requires positive closed-trade Calmar in BOTH bull and bear
windows before live consideration.
"""
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy

SMA_PERIOD = 180
SLOPE_LOOKBACK = 6  # bars; 6 × 4h = 24h


class SmaRegime180(IStrategy):
    INTERFACE_VERSION = 3
    can_short = False

    timeframe = "4h"
    startup_candle_count = SMA_PERIOD + SLOPE_LOOKBACK

    minimal_roi = {"0": 100}  # disabled — exit purely on regime break
    stoploss = -0.10
    trailing_stop = False

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sma180"] = ta.SMA(dataframe, timeperiod=SMA_PERIOD)
        dataframe["sma180_slope"] = dataframe["sma180"] - dataframe["sma180"].shift(SLOPE_LOOKBACK)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] > dataframe["sma180"])
            & (dataframe["close"].shift(1) <= dataframe["sma180"].shift(1))
            & (dataframe["sma180_slope"] > 0),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] < dataframe["sma180"])
            & (dataframe["close"].shift(1) >= dataframe["sma180"].shift(1)),
            "exit_long",
        ] = 1
        return dataframe
