"""
CrossSectionalMomentum — long top-1 coin by trailing 7d return.

Multi-asset strategy: at each 4h bar, the strategy ranks the configured
universe by their trailing 7d return (42 bars at 4h) and enters long on the
coin currently in rank-1 position, provided its momentum > 0. Holds until the
next rebalance (every 24 bars = 4d) or a stop. Single position at a time —
the strategy emits enter_long only for the pair currently ranked #1.

Each coin's signal depends on cross-sectional comparison with all others.
Implemented by computing the rank inside populate_indicators using on-disk
data for the partner coins.

This is a degenerate 1-factor model where the factor is "return rank." The
simplest test of the cross-sectional thesis on the project's smallest basket.
See `wiki/decisions/007-kill-criteria-cross-sectional.md` for pre-registered
kill criteria.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy


UNIVERSE = ["BTC", "ETH", "SOL", "AVAX", "DOGE"]
LOOKBACK_BARS = 42      # 7 days at 4h
REBALANCE_BARS = 24     # 4 days at 4h
MIN_MOMENTUM = 0.0      # trailing return must be > this for any entry


def _data_dir() -> Path:
    return Path("user_data/data/binance/futures")


def _load_close(coin: str, timeframe: str) -> pd.Series:
    f = _data_dir() / f"{coin}_USDT_USDT-{timeframe}-futures.feather"
    if not f.exists():
        return pd.Series(dtype=float)
    df = pd.read_feather(f)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df.set_index("date")["close"].sort_index()


def _compute_ranks(timeframe: str) -> pd.DataFrame:
    """For each timestamp, compute the rank of each coin by trailing 7d return.

    Returns DataFrame indexed by date with one column per coin in UNIVERSE; values
    are integer ranks (1 = highest momentum) or NaN where not enough data.
    """
    series = {c: _load_close(c, timeframe) for c in UNIVERSE}
    df = pd.DataFrame(series).dropna(how="all")
    rets = (df / df.shift(LOOKBACK_BARS) - 1.0)
    # Rank per row: 1 = highest momentum.
    ranks = rets.rank(axis=1, ascending=False, method="min")
    # Zero out coins whose momentum is below threshold (no rank-1 if all negative).
    ranks = ranks.where(rets > MIN_MOMENTUM)
    return ranks


class CrossSectionalMomentum(IStrategy):
    INTERFACE_VERSION = 3
    can_short = False

    timeframe = "4h"
    startup_candle_count = LOOKBACK_BARS + REBALANCE_BARS

    minimal_roi = {"0": 100}
    stoploss = -0.10
    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = True

    # -----------------------------------------------------------------
    # Indicators
    # -----------------------------------------------------------------

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # Pair name like "BTC/USDT:USDT" → coin "BTC".
        coin = metadata["pair"].split("/")[0]
        if coin not in UNIVERSE:
            dataframe["rank"] = np.nan
            dataframe["rebalance_anchor"] = np.nan
            return dataframe

        ranks = _compute_ranks(self.timeframe)
        if coin not in ranks.columns:
            dataframe["rank"] = np.nan
            dataframe["rebalance_anchor"] = np.nan
            return dataframe

        df = dataframe.copy()
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.set_index("date")

        coin_rank = ranks[coin].reindex(df.index)

        # Rebalance anchor: only allow signals at every REBALANCE_BARS index.
        # We compute "is this bar a rebalance point" by checking if the bar's index
        # position % REBALANCE_BARS == 0.
        df["rank"] = coin_rank
        df["bar_idx"] = np.arange(len(df))
        df["rebalance_anchor"] = (df["bar_idx"] % REBALANCE_BARS == 0).astype(int)

        df = df.reset_index()
        return df

    # -----------------------------------------------------------------
    # Entry / exit
    # -----------------------------------------------------------------

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        r = dataframe.get("rank")
        anchor = dataframe.get("rebalance_anchor")
        if r is None or anchor is None:
            dataframe["enter_long"] = 0
            return dataframe
        # Enter only when this coin is rank #1 at a rebalance point.
        dataframe["enter_long"] = ((r == 1) & (anchor == 1)).astype(int)
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        r = dataframe.get("rank")
        anchor = dataframe.get("rebalance_anchor")
        if r is None or anchor is None:
            dataframe["exit_long"] = 0
            return dataframe
        # Exit when this coin is no longer rank #1 at a rebalance point.
        dataframe["exit_long"] = ((r > 1) & (anchor == 1)).astype(int) | r.isna().astype(int)
        return dataframe
