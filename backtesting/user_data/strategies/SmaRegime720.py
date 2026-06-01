"""
SmaRegime720 — long only inside confirmed uptrend on 1h data.

Hypothesis: TrendFilter200 failed because 200 periods on 1h (~8 days) is too
short to define a crypto regime — every bear-market bounce triggers a bull-trap
entry. Two fixes applied here:
  1. Window = 720 periods (≈30d) — stable enough to survive short bounces.
  2. Slope gate — SMA must itself be rising (sma720 > sma720 24 bars ago)
     before an entry is accepted. This blocks entries when price pops above a
     still-declining SMA.

Entry:  close crosses above sma720  AND  sma720 is rising (slope > 0).
Exit:   close crosses below sma720 (regime ends — exit immediately).
"""
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy

SMA_PERIOD = 720
SLOPE_LOOKBACK = 24  # bars; 24h on 1h data


class SmaRegime720(IStrategy):
    INTERFACE_VERSION = 3
    can_short = False

    timeframe = "1h"
    startup_candle_count = SMA_PERIOD + SLOPE_LOOKBACK

    minimal_roi = {"0": 100}  # disabled — exit purely on regime break
    stoploss = -0.10
    trailing_stop = False

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sma720"] = ta.SMA(dataframe, timeperiod=SMA_PERIOD)
        dataframe["sma720_slope"] = dataframe["sma720"] - dataframe["sma720"].shift(SLOPE_LOOKBACK)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] > dataframe["sma720"])
            & (dataframe["close"].shift(1) <= dataframe["sma720"].shift(1))
            & (dataframe["sma720_slope"] > 0),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] < dataframe["sma720"])
            & (dataframe["close"].shift(1) >= dataframe["sma720"].shift(1)),
            "exit_long",
        ] = 1
        return dataframe
