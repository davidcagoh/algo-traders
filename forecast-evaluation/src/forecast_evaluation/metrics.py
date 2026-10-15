"""Forecast metrics with explicit marginal and cumulative-return semantics."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

QUANTILES = tuple((f"q{level}", level / 100) for level in range(10, 100, 10))


def _point_scores(actual: np.ndarray, forecast: np.ndarray) -> dict[str, float]:
    errors = forecast - actual
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(np.square(errors)))),
        "directional_accuracy": float(np.mean(np.sign(forecast) == np.sign(actual))),
    }


def _with_skill(rows: list[dict[str, Any]]) -> None:
    lookup = {
        (
            row["segment"], row.get("mode", "univariate"), row["symbol"],
            row["lead_hours"], row["model"],
        ): row
        for row in rows
    }
    for row in rows:
        if not row["model"].startswith("timesfm3"):
            continue
        for baseline, label in (("zero_return", "zero"), ("last_return", "last_return")):
            key = (
                row["segment"], row.get("mode", "univariate"), row["symbol"],
                row["lead_hours"], baseline,
            )
            other = lookup.get(key)
            if other is None:
                continue
            for metric in ("mae", "rmse"):
                denominator = other.get(metric)
                row[f"skill_vs_{label}_{metric}"] = (
                    float(1 - row[metric] / denominator)
                    if denominator is not None and denominator > 0
                    else None
                )


def score_by_lead(forecasts: pd.DataFrame) -> list[dict[str, Any]]:
    """Score one-hour returns separately at each forecast lead."""
    required = {"segment", "mode", "symbol", "model", "origin", "lead", "actual", "point"}
    if missing := required - set(forecasts.columns):
        raise ValueError(f"forecast rows are missing columns: {sorted(missing)}")
    rows: list[dict[str, Any]] = []
    keys = ["segment", "mode", "symbol", "lead", "model"]
    for (segment, mode, symbol, lead, model), group in forecasts.groupby(keys, sort=True):
        actual = group["actual"].to_numpy(dtype=float)
        point = group["point"].to_numpy(dtype=float)
        if not np.isfinite(actual).all() or not np.isfinite(point).all():
            raise ValueError("actuals and point forecasts must be finite")
        row: dict[str, Any] = {
            "segment": str(segment), "mode": str(mode), "symbol": str(symbol),
            "lead_hours": int(lead),
            "model": str(model), "n": int(len(group)), **_point_scores(actual, point),
        }
        if model == "timesfm3" and {name for name, _ in QUANTILES} <= set(group.columns):
            quantile_values = {
                name: group[name].to_numpy(dtype=float) for name, _ in QUANTILES
            }
            if not np.isfinite(np.column_stack(tuple(quantile_values.values()))).all():
                raise ValueError("quantile forecasts must be finite")
            ordered = np.column_stack(tuple(quantile_values.values()))
            if np.any(np.diff(ordered, axis=1) < -1e-10):
                raise ValueError("quantile forecasts must be ordered q10 <= ... <= q90")
            losses = []
            for name, quantile in QUANTILES:
                forecast = quantile_values[name]
                error = actual - forecast
                losses.append(np.maximum(quantile * error, (quantile - 1) * error))
            q10 = quantile_values["q10"]
            q90 = quantile_values["q90"]
            row.update(
                pinball_loss=float(np.mean(np.column_stack(losses))),
                nominal_80_coverage=float(np.mean((actual >= q10) & (actual <= q90))),
                nominal_80_width=float(np.mean(q90 - q10)),
            )
        rows.append(row)
    _with_skill(rows)
    return rows


def score_cumulative(
    forecasts: pd.DataFrame,
    horizons: Iterable[int],
) -> list[dict[str, Any]]:
    """Score summed point forecasts and realized returns at selected horizons."""
    required = {"segment", "mode", "symbol", "model", "origin", "lead", "actual", "point"}
    if missing := required - set(forecasts.columns):
        raise ValueError(f"forecast rows are missing columns: {sorted(missing)}")
    rows: list[dict[str, Any]] = []
    for (segment, mode, symbol, model, origin), group in forecasts.groupby(
        ["segment", "mode", "symbol", "model", "origin"], sort=True
    ):
        ordered = group.sort_values("lead")
        actual = ordered["actual"].to_numpy(dtype=float)
        point = ordered["point"].to_numpy(dtype=float)
        lead = ordered["lead"].to_numpy(dtype=int)
        for horizon in sorted(set(int(value) for value in horizons)):
            mask = lead <= horizon
            if int(mask.sum()) != horizon or not np.array_equal(lead[mask], np.arange(1, horizon + 1)):
                continue
            cumulative_actual = float(actual[mask].sum())
            cumulative_point = float(point[mask].sum())
            score = _point_scores(
                np.asarray([cumulative_actual]), np.asarray([cumulative_point])
            )
            rows.append({
                "segment": str(segment), "mode": str(mode), "symbol": str(symbol),
                "model": str(model),
                "origin": str(origin), "lead_hours": horizon,
                "actual": cumulative_actual, "point": cumulative_point, **score,
            })

    if not rows:
        return []
    aggregate: list[dict[str, Any]] = []
    for (segment, mode, symbol, lead, model), group in pd.DataFrame(rows).groupby(
        ["segment", "mode", "symbol", "lead_hours", "model"], sort=True
    ):
        aggregate.append({
            "segment": str(segment), "mode": str(mode), "symbol": str(symbol),
            "lead_hours": int(lead),
            "model": str(model), "n": int(len(group)),
            **_point_scores(group["actual"].to_numpy(float), group["point"].to_numpy(float)),
        })
    _with_skill(aggregate)
    return aggregate


def summarize(forecasts: pd.DataFrame, horizons: Iterable[int]) -> dict[str, Any]:
    """Return JSON-serializable lead and cumulative metric tables."""
    return {
        "lead_return_metrics": score_by_lead(forecasts),
        "cumulative_return_metrics": score_cumulative(forecasts, horizons),
    }
