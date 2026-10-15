"""Rolling-origin evaluation for point, quantile, and naive forecasts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
import pandas as pd

from forecast_evaluation.data import ReturnSeries


class Forecaster(Protocol):
    """Minimal interface implemented by TimesFM and deterministic test doubles."""

    def predict(
        self, targets: np.ndarray, *, horizon: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return point forecasts and q10..q90 arrays for one or more targets."""


@dataclass(frozen=True)
class Segment:
    name: str
    max_horizon: int
    stride_hours: int
    scored_leads: tuple[int, ...]
    start: str | None = None
    end: str | None = None
    target_cutoff_exclusive: str | None = None


def origin_indices(series: ReturnSeries, *, context_length: int, segment: Segment) -> list[int]:
    """Choose origins with enough finite context and complete future outcomes."""
    if context_length < 1 or segment.max_horizon < 1 or segment.stride_hours < 1:
        raise ValueError("context, horizon, and origin stride must be positive")
    timestamps = series.timestamps
    first_index = context_length
    last_index = len(series.values) - segment.max_horizon - 1
    if last_index < first_index:
        return []

    start = pd.Timestamp(segment.start) if segment.start else None
    end = pd.Timestamp(segment.end) if segment.end else None
    cutoff = pd.Timestamp(segment.target_cutoff_exclusive) if segment.target_cutoff_exclusive else None
    if start is not None and start.tzinfo is None:
        start = start.tz_localize("UTC")
    if end is not None and end.tzinfo is None:
        end = end.tz_localize("UTC")
    if cutoff is not None and cutoff.tzinfo is None:
        cutoff = cutoff.tz_localize("UTC")
    if start is not None:
        first_index = max(first_index, int(timestamps.searchsorted(start, side="left")))

    selected: list[int] = []
    for index in range(first_index, last_index + 1, segment.stride_hours):
        origin_time = timestamps[index]
        final_target_time = timestamps[index + segment.max_horizon]
        if start is not None and origin_time < start:
            continue
        if end is not None and origin_time > end:
            continue
        if cutoff is not None and final_target_time >= cutoff:
            continue
        context = series.values[index - context_length + 1 : index + 1]
        if len(context) != context_length or not np.isfinite(context).all():
            raise ValueError(f"{series.symbol}: origin has invalid or incomplete context")
        selected.append(index)
    return selected


def _normalize_prediction(
    point: np.ndarray,
    quantiles: np.ndarray,
    *,
    target_count: int,
    horizon: int,
) -> tuple[np.ndarray, np.ndarray]:
    point_values = np.asarray(point, dtype=np.float64)
    quantile_values = np.asarray(quantiles, dtype=np.float64)
    if point_values.ndim == 1:
        point_values = point_values[None, :]
    if quantile_values.ndim == 2:
        quantile_values = quantile_values[None, :, :]
    if point_values.shape != (target_count, horizon):
        raise ValueError(f"unexpected point forecast shape: {point_values.shape}")
    if quantile_values.shape != (target_count, horizon, 9):
        raise ValueError(f"expected q10..q90 forecast shape {(target_count, horizon, 9)}")
    if not np.isfinite(point_values).all() or not np.isfinite(quantile_values).all():
        raise ValueError("forecasts must be finite")
    if np.any(np.diff(quantile_values, axis=-1) < -1e-10):
        raise ValueError("TimesFM quantiles must be sorted before scoring")
    if not np.allclose(point_values, quantile_values[:, :, 4], rtol=1e-5, atol=1e-8):
        raise ValueError("TimesFM point forecast must match its q50 output")
    return point_values, quantile_values


def evaluate_segment(
    series: Mapping[str, ReturnSeries],
    forecaster: Forecaster,
    *,
    segment: Segment,
    context_length: int,
    mode: str = "univariate",
) -> pd.DataFrame:
    """Forecast one segment and preserve every origin/lead outcome."""
    if not series:
        raise ValueError("at least one return series is required")
    symbols = tuple(sorted(series))
    if mode not in {"univariate", "multivariate"}:
        raise ValueError("mode must be univariate or multivariate")
    if mode == "multivariate" and len(symbols) < 2:
        raise ValueError("multivariate mode needs at least two aligned targets")
    if mode == "multivariate" and any(
        not series[symbol].timestamps.equals(series[symbols[0]].timestamps)
        for symbol in symbols[1:]
    ):
        raise ValueError("multivariate targets must share identical timestamps")

    records: list[dict[str, Any]] = []
    target_groups = [symbols] if mode == "multivariate" else [(symbol,) for symbol in symbols]
    for model_symbols in target_groups:
        indices_by_symbol = {
            symbol: origin_indices(
                series[symbol], context_length=context_length, segment=segment
            )
            for symbol in model_symbols
        }
        if len({tuple(indices) for indices in indices_by_symbol.values()}) != 1:
            raise ValueError("multivariate targets must have the same origin schedule")
        origins = indices_by_symbol[model_symbols[0]]
        if not origins:
            raise ValueError(f"no eligible origins for segment {segment.name!r}")

        for origin_index in origins:
            contexts = [
                series[symbol].values[origin_index - context_length + 1 : origin_index + 1]
                for symbol in model_symbols
            ]
            target_context = (
                np.stack(contexts, axis=0)
                if mode == "multivariate"
                else contexts[0]
            ).astype(np.float32)
            raw_point, raw_quantiles = forecaster.predict(
                target_context, horizon=segment.max_horizon
            )
            point, quantiles = _normalize_prediction(
                raw_point, raw_quantiles,
                target_count=len(model_symbols),
                horizon=segment.max_horizon,
            )

            for target_index, (symbol, context) in enumerate(
                zip(model_symbols, contexts, strict=True)
            ):
                target_series = series[symbol]
                origin_time = target_series.timestamps[origin_index]
                for lead in segment.scored_leads:
                    if lead < 1 or lead > segment.max_horizon:
                        raise ValueError(f"scored lead {lead} is outside forecast horizon")
                    actual = float(target_series.values[origin_index + lead])
                    model_point = float(point[target_index, lead - 1])
                    q_values = quantiles[target_index, lead - 1]
                    records.append({
                        "segment": segment.name,
                        "mode": mode,
                        "symbol": symbol,
                        "origin": origin_time.isoformat(),
                        "lead": int(lead),
                        "actual": actual,
                        "model": "timesfm3",
                        "point": model_point,
                        **{
                            f"q{quantile_index + 1}0": float(q_values[quantile_index])
                            for quantile_index in range(9)
                        },
                    })

                    baselines = {
                        "zero_return": 0.0,
                        "last_return": float(context[-1]),
                    }
                    for baseline, baseline_point in baselines.items():
                        records.append({
                            "segment": segment.name,
                            "mode": mode,
                            "symbol": symbol,
                            "origin": origin_time.isoformat(),
                            "lead": int(lead),
                            "actual": actual,
                            "model": baseline,
                            "point": baseline_point,
                            **{f"q{quantile_index + 1}0": np.nan for quantile_index in range(9)},
                        })
    return pd.DataFrame.from_records(records)
