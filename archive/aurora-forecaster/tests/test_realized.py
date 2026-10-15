import pandas as pd
import pytest

from aurora_forecaster.forecast_ledger import ForecastRecord
from aurora_forecaster.realized import RealizedDataError, align_forecast_to_prices


def make_record(lookback=3, horizon=2, origin_timestamp="1970-01-01T00:00:05+00:00"):
    return ForecastRecord(
        forecast_id="f-1",
        created_at="2026-08-07T00:00:00+00:00",
        asset="BTC",
        modality="unimodal",
        model_id="DecisionIntelligence/Aurora",
        origin_timestamp=origin_timestamp,
        lookback=lookback,
        horizon=horizon,
        num_samples=10,
        sample_mean=[0.0] * horizon,
        sample_std=[1.0] * horizon,
    )


def make_price_df(n_rows: int, step_s: int = 1) -> pd.DataFrame:
    # timestamps in ms epoch, one row per step_s seconds starting at epoch 0
    timestamps = [i * step_s * 1000 for i in range(n_rows)]
    closes = [100.0 + i for i in range(n_rows)]
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * n_rows,
        }
    )


def test_align_forecast_to_prices_happy_path():
    # origin_timestamp = epoch 5s -> row index 5, close = 105.0
    record = make_record(lookback=3, horizon=2, origin_timestamp="1970-01-01T00:00:05+00:00")
    price_df = make_price_df(n_rows=10)

    window = align_forecast_to_prices(record, price_df)

    # lookback = last 3 closes up to and including index 5: rows 3,4,5 -> 103,104,105
    assert window.lookback_closes == [103.0, 104.0, 105.0]
    # realized horizon = rows 6,7 -> 106,107
    assert window.realized_closes == [106.0, 107.0]


def test_align_forecast_to_prices_missing_origin_timestamp_raises():
    record = make_record(origin_timestamp="1970-01-01T00:05:00+00:00")  # not in price_df
    price_df = make_price_df(n_rows=10)

    with pytest.raises(RealizedDataError):
        align_forecast_to_prices(record, price_df)


def test_align_forecast_to_prices_insufficient_lookback_raises():
    # origin at index 1, but lookback=3 needs rows starting at index -1
    record = make_record(lookback=3, horizon=1, origin_timestamp="1970-01-01T00:00:01+00:00")
    price_df = make_price_df(n_rows=10)

    with pytest.raises(RealizedDataError):
        align_forecast_to_prices(record, price_df)


def test_align_forecast_to_prices_insufficient_horizon_raises():
    # origin at last row (index 9), horizon=2 needs 2 more rows that don't exist
    record = make_record(lookback=1, horizon=2, origin_timestamp="1970-01-01T00:00:09+00:00")
    price_df = make_price_df(n_rows=10)

    with pytest.raises(RealizedDataError):
        align_forecast_to_prices(record, price_df)
