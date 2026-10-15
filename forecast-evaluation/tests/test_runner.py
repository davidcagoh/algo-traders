import numpy as np
import pandas as pd
import pytest

from forecast_evaluation.data import ReturnSeries
from forecast_evaluation.runner import Segment, _normalize_prediction, evaluate_segment, origin_indices


class RepeatLastForecaster:
    def __init__(self):
        self.contexts = []

    def predict(self, targets, *, horizon):
        values = np.asarray(targets)
        self.contexts.append(values.copy())
        if values.ndim == 1:
            values = values[None, :]
        point = np.repeat(values[:, -1, None], horizon, axis=1)
        quantiles = np.repeat(point[:, :, None], 9, axis=2)
        return point, quantiles


def make_series(symbol, offset=0):
    timestamps = pd.date_range("2026-01-01", periods=32, freq="h", tz="UTC")
    values = np.arange(32, dtype=float) / 1000 + offset
    values[0] = np.nan
    return ReturnSeries(symbol=symbol, timestamps=timestamps, values=values)


def test_origins_use_context_stride_and_exclusive_target_cutoff():
    series = make_series("BTC")
    segment = Segment(
        name="historical", max_horizon=3, stride_hours=4,
        scored_leads=(1, 3), target_cutoff_exclusive=series.timestamps[24].isoformat(),
    )

    assert origin_indices(series, context_length=4, segment=segment) == [4, 8, 12, 16, 20]


def test_freshness_origins_are_anchored_to_release_window_start():
    series = make_series("BTC")
    segment = Segment(
        name="fresh", max_horizon=2, stride_hours=4, scored_leads=(1, 2),
        start=series.timestamps[8].isoformat(), end=series.timestamps[16].isoformat(),
    )

    assert origin_indices(series, context_length=4, segment=segment) == [8, 12, 16]


def test_univariate_evaluation_runs_each_symbol_without_future_context():
    series = {"BTC": make_series("BTC"), "ETH": make_series("ETH", 0.1)}
    segment = Segment(name="fresh", max_horizon=2, stride_hours=24, scored_leads=(1, 2))
    model = RepeatLastForecaster()

    forecasts = evaluate_segment(series, model, segment=segment, context_length=4)

    assert set(forecasts.symbol) == {"BTC", "ETH"}
    assert set(forecasts.model) == {"timesfm3", "zero_return", "last_return"}
    assert len(model.contexts) == 4
    assert all(context.ndim == 1 and len(context) == 4 for context in model.contexts)
    assert forecasts.groupby(["symbol", "model"]).size().to_dict() == {
        (symbol, model_name): 4 for symbol in ("BTC", "ETH")
        for model_name in ("timesfm3", "zero_return", "last_return")
    }


def test_future_target_changes_do_not_change_forecaster_context():
    first = make_series("BTC")
    origin_time = first.timestamps[10].isoformat()
    segment = Segment(
        name="fresh", max_horizon=2, stride_hours=1, scored_leads=(1, 2),
        start=origin_time, end=origin_time,
    )
    model_a = RepeatLastForecaster()
    forecasts_a = evaluate_segment({"BTC": first}, model_a, segment=segment, context_length=4)

    changed_values = first.values.copy()
    changed_values[11:] += 10_000
    changed = ReturnSeries("BTC", first.timestamps, changed_values)
    model_b = RepeatLastForecaster()
    forecasts_b = evaluate_segment({"BTC": changed}, model_b, segment=segment, context_length=4)

    assert len(model_a.contexts) == len(model_b.contexts)
    assert all(
        np.array_equal(left, right)
        for left, right in zip(model_a.contexts, model_b.contexts, strict=True)
    )
    assert not forecasts_a["actual"].equals(forecasts_b["actual"])


def test_multivariate_evaluation_passes_aligned_targets_together():
    series = {"BTC": make_series("BTC"), "ETH": make_series("ETH", 0.1)}
    model = RepeatLastForecaster()
    segment = Segment(name="fresh", max_horizon=2, stride_hours=24, scored_leads=(1, 2))

    forecasts = evaluate_segment(
        series, model, segment=segment, context_length=4, mode="multivariate"
    )

    assert model.contexts[0].shape == (2, 4)
    assert set(forecasts.symbol) == {"BTC", "ETH"}
    assert set(forecasts["mode"]) == {"multivariate"}


def test_forecasts_reject_unsorted_quantiles_and_point_mismatch():
    point = np.full(3, 4.0)
    sorted_quantiles = np.tile(np.arange(9), (3, 1)).astype(float)
    _normalize_prediction(point, sorted_quantiles, target_count=1, horizon=3)

    unsorted = sorted_quantiles.copy()
    unsorted[1, 3], unsorted[1, 4] = unsorted[1, 4], unsorted[1, 3]
    with pytest.raises(ValueError, match="sorted"):
        _normalize_prediction(point, unsorted, target_count=1, horizon=3)

    with pytest.raises(ValueError, match="q50"):
        _normalize_prediction(np.ones(3), sorted_quantiles, target_count=1, horizon=3)

    nonfinite = sorted_quantiles.copy()
    nonfinite[1, 2] = np.nan
    with pytest.raises(ValueError, match="finite"):
        _normalize_prediction(point, nonfinite, target_count=1, horizon=3)


def test_multivariate_rejects_misaligned_time_grids():
    first = make_series("BTC")
    shifted = ReturnSeries(
        symbol="ETH", timestamps=first.timestamps + pd.Timedelta(hours=1), values=first.values
    )
    segment = Segment(name="fresh", max_horizon=2, stride_hours=24, scored_leads=(1, 2))

    with pytest.raises(ValueError, match="identical timestamps"):
        evaluate_segment(
            {"BTC": first, "ETH": shifted}, RepeatLastForecaster(),
            segment=segment, context_length=4, mode="multivariate",
        )
