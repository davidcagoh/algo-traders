"""
Minimal long-only placeholder strategy — restores the `LongOnlyStrategy` name
referenced in the original `notes.md`. Enters on a simple SMA cross, exits
on the reverse cross. Replace with real logic before trusting any results.
"""
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy


class LongOnlyStrategy(IStrategy):
    INTERFACE_VERSION = 3
    can_short = False

    timeframe = "5m"
    startup_candle_count = 200

    minimal_roi = {"0": 0.05}
    stoploss = -0.05
    trailing_stop = False

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sma_fast"] = ta.SMA(dataframe, timeperiod=20)
        dataframe["sma_slow"] = ta.SMA(dataframe, timeperiod=50)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["sma_fast"] > dataframe["sma_slow"])
            & (dataframe["sma_fast"].shift(1) <= dataframe["sma_slow"].shift(1)),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["sma_fast"] < dataframe["sma_slow"])
            & (dataframe["sma_fast"].shift(1) >= dataframe["sma_slow"].shift(1)),
            "exit_long",
        ] = 1
        return dataframe
