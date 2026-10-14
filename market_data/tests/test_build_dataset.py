from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_dataset import daily_from_hourly, utc_timestamp  # noqa: E402


def test_timestamp_unit_handles_binance_milliseconds_and_microseconds() -> None:
    milliseconds = utc_timestamp(pd.Series([1_704_067_200_000]))
    microseconds = utc_timestamp(pd.Series([1_704_067_200_000_000]))
    assert milliseconds.iloc[0] == pd.Timestamp("2024-01-01", tz="UTC")
    assert microseconds.iloc[0] == pd.Timestamp("2024-01-01", tz="UTC")


def test_timestamp_unit_handles_mixed_binance_archive_eras() -> None:
    mixed = utc_timestamp(pd.Series([1_704_067_200_000, 1_735_689_600_000_000]))
    assert mixed.iloc[0] == pd.Timestamp("2024-01-01", tz="UTC")
    assert mixed.iloc[1] == pd.Timestamp("2025-01-01", tz="UTC")


def test_daily_aggregation_uses_utc_ohlcv_semantics() -> None:
    hourly = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"]),
            "symbol": ["BTC", "BTC"],
            "pair": ["BTCUSDT", "BTCUSDT"],
            "quote": ["USDT", "USDT"],
            "venue": ["binance", "binance"],
            "market": ["spot", "spot"],
            "open": [10.0, 12.0],
            "high": [13.0, 15.0],
            "low": [9.0, 11.0],
            "close": [12.0, 14.0],
            "volume_base": [2.0, 3.0],
            "quote_volume": [22.0, 39.0],
            "trade_count": [4, 5],
            "taker_buy_volume_base": [1.0, 2.0],
            "taker_buy_volume_quote": [11.0, 26.0],
        }
    )
    row = daily_from_hourly(hourly).iloc[0]
    assert row["open"] == 10.0
    assert row["high"] == 15.0
    assert row["low"] == 9.0
    assert row["close"] == 14.0
    assert row["volume_base"] == 5.0
