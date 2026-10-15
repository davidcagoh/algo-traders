"""Align a `ForecastRecord` to realized prices for scoring.

`origin_timestamp` is the timestamp of the *last lookback bar* (see
`forecast_ledger.py`'s docstring and `rolling_forecast_btc.py`'s
`origin_ts = timestamps[origin - 1]`), so the lookback window is the
`lookback` rows ending at and including that timestamp, and the realized
horizon is the `horizon` rows immediately after it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from aurora_forecaster.forecast_ledger import ForecastRecord


class RealizedDataError(ValueError):
    pass


@dataclass(frozen=True)
class RealizedWindow:
    lookback_closes: list[float]
    realized_closes: list[float]  # len == record.horizon


def align_forecast_to_prices(record: ForecastRecord, price_df: pd.DataFrame) -> RealizedWindow:
    origin_ms = int(datetime.fromisoformat(record.origin_timestamp).timestamp() * 1000)
    timestamps = price_df["timestamp"].to_numpy()
    matches = (timestamps == origin_ms).nonzero()[0]
    if len(matches) == 0:
        raise RealizedDataError(
            f"origin_timestamp {record.origin_timestamp} (epoch {origin_ms}) "
            "not found in price_df"
        )
    origin_idx = int(matches[0])

    lookback_start = origin_idx - record.lookback + 1
    if lookback_start < 0:
        raise RealizedDataError(
            f"price_df doesn't cover the lookback window: need {record.lookback} rows "
            f"ending at origin index {origin_idx}, only {origin_idx + 1} available"
        )

    horizon_end = origin_idx + record.horizon
    if horizon_end >= len(price_df):
        available = len(price_df) - origin_idx - 1
        raise RealizedDataError(
            f"price_df doesn't cover the realized horizon: need {record.horizon} rows "
            f"after origin index {origin_idx}, only {available} available"
        )

    closes = price_df["close"].to_numpy()
    lookback_closes = closes[lookback_start : origin_idx + 1].tolist()
    realized_closes = closes[origin_idx + 1 : horizon_end + 1].tolist()
    return RealizedWindow(lookback_closes=lookback_closes, realized_closes=realized_closes)
