"""
TrendFilter200 — long only when price is above the 200-period SMA.

Thesis: crypto has persistent regimes at multi-day+ timeframes. A trend filter
should sit in cash through bear markets (where the placeholder SMA-cross
strategy gets chopped up) and only hold during up-trends. Over the 2025-10 →
2026-04 baseline window the market fell ~37%, so the filter should mostly be
flat and heavily outperform buy-and-hold on Calmar / MDD.
"""
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy


class TrendFilter200(IStrategy):
    INTERFACE_VERSION = 3
    can_short = False

    timeframe = "5m"
    startup_candle_count = 200

    minimal_roi = {"0": 100}  # effectively disabled; exit on trend break
    stoploss = -0.10
    trailing_stop = False

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sma_200"] = ta.SMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] > dataframe["sma_200"])
            & (dataframe["close"].shift(1) <= dataframe["sma_200"].shift(1)),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] < dataframe["sma_200"])
            & (dataframe["close"].shift(1) >= dataframe["sma_200"].shift(1)),
            "exit_long",
        ] = 1
        return dataframe
