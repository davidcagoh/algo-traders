"""Paired, dependence-aware comparisons for saved rolling forecasts."""

from __future__ import annotations

from collections.abc import Iterable
import importlib.util
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

_BOOTSTRAP_PATH = Path(__file__).resolve().parents[3] / "evaluation-framework/evaluation/bootstrap.py"
_BOOTSTRAP_SPEC = importlib.util.spec_from_file_location("shared_evaluation_bootstrap", _BOOTSTRAP_PATH)
if _BOOTSTRAP_SPEC is None or _BOOTSTRAP_SPEC.loader is None:
    raise ImportError(f"cannot load shared bootstrap utilities from {_BOOTSTRAP_PATH}")
_BOOTSTRAP_MODULE = importlib.util.module_from_spec(_BOOTSTRAP_SPEC)
sys.modules[_BOOTSTRAP_SPEC.name] = _BOOTSTRAP_MODULE
_BOOTSTRAP_SPEC.loader.exec_module(_BOOTSTRAP_MODULE)
stationary_bootstrap_indices = _BOOTSTRAP_MODULE.stationary_bootstrap_indices


_KEYS = ["segment", "mode", "symbol", "origin", "lead"]
_MODELS = {"timesfm3", "zero_return", "last_return"}


def validate_forecasts(forecasts: pd.DataFrame) -> None:
    """Fail closed on duplicate, incomplete, or misaligned saved forecast rows."""
    required = set(_KEYS + ["model", "actual", "point"])
    if missing := required - set(forecasts.columns):
        raise ValueError(f"forecast rows are missing columns: {sorted(missing)}")
    key = _KEYS + ["model"]
    if forecasts.duplicated(key).any():
        raise ValueError("duplicate forecast rows found for an origin and lead")
    if not set(forecasts["model"].unique()) <= _MODELS:
        raise ValueError("unexpected model found in forecast rows")
    if not np.isfinite(forecasts[["actual", "point"]].to_numpy(dtype=float)).all():
        raise ValueError("actuals and point forecasts must be finite")

    pivot = forecasts.pivot(index=_KEYS, columns="model", values=["actual", "point"])
    if set(pivot.columns.get_level_values("model")) != _MODELS:
        raise ValueError("every forecast origin must include TimesFM and both baselines")
    actuals = pivot["actual"]
    if actuals.isna().any().any():
        raise ValueError("paired forecast rows are incomplete")
    if not (actuals.nunique(axis=1) == 1).all():
        raise ValueError("paired models must have identical realized targets")
    if pivot["point"].isna().any().any():
        raise ValueError("paired model forecasts are incomplete")
    if "q10" in forecasts:
        quantiles = [f"q{level}" for level in range(10, 100, 10)]
        timesfm = forecasts.loc[forecasts["model"] == "timesfm3", quantiles]
        if not np.isfinite(timesfm.to_numpy(dtype=float)).all():
            raise ValueError("TimesFM quantile forecasts must be finite")
        if np.any(np.diff(timesfm.to_numpy(dtype=float), axis=1) < -1e-10):
            raise ValueError("TimesFM quantiles must be ordered")


def _comparison_rows(
    forecasts: pd.DataFrame, cumulative_horizons: Iterable[int]
) -> pd.DataFrame:
    long_rows = forecasts.loc[forecasts["model"].isin(["timesfm3", "zero_return", "last_return"])]
    rows: list[dict[str, Any]] = []
    common = ["segment", "mode", "symbol", "origin"]
    for (segment, mode, symbol, origin, lead), group in long_rows.groupby(
        common + ["lead"], sort=True
    ):
        indexed = group.set_index("model")
        actual = float(indexed.loc["timesfm3", "actual"])
        model_loss = abs(float(indexed.loc["timesfm3", "point"]) - actual)
        for baseline in ("zero_return", "last_return"):
            baseline_loss = abs(float(indexed.loc[baseline, "point"]) - actual)
            rows.append({
                "segment": str(segment), "mode": str(mode), "symbol": str(symbol),
            "origin": str(origin), "kind": "lead",
                "horizon": int(lead), "baseline": baseline,
                "model_loss": model_loss, "baseline_loss": baseline_loss,
                "loss_diff": model_loss - baseline_loss,
            })

    for horizon in sorted(set(int(item) for item in cumulative_horizons)):
        if horizon == 1:
            # The one-hour cumulative target is the same observation as lead 1.
            continue
        eligible = long_rows.loc[long_rows["lead"] <= horizon]
        for keys, unsorted_group in eligible.groupby(
            ["segment", "mode", "symbol", "model", "origin"], sort=True
        ):
            group = unsorted_group.sort_values("lead")
            leads = group["lead"].to_numpy(dtype=int)
            if len(leads) != horizon or not np.array_equal(leads, np.arange(1, horizon + 1)):
                continue
            segment, mode, symbol, model, origin = keys
            actual = float(group["actual"].sum())
            point = float(group["point"].sum())
            # Keep per-model cumulative losses until all three forecasts are paired.
            rows.append({
                "segment": str(segment), "mode": str(mode), "symbol": str(symbol),
                "origin": str(origin), "kind": "cumulative_component",
                "horizon": horizon, "baseline": str(model),
                "model_loss": abs(actual - point), "baseline_loss": np.nan,
                "loss_diff": np.nan,
            })
    result = pd.DataFrame(rows)
    components = result.loc[result["kind"] == "cumulative_component"]
    if not components.empty:
        for (segment, mode, symbol, origin, horizon), group in components.groupby(
            ["segment", "mode", "symbol", "origin", "horizon"], sort=True
        ):
            by_model = group.set_index("baseline")["model_loss"]
            for baseline in ("zero_return", "last_return"):
                rows.append({
                    "segment": segment, "mode": mode, "symbol": symbol,
                    "origin": origin, "kind": "cumulative", "horizon": horizon,
                    "baseline": baseline, "model_loss": float(by_model["timesfm3"]),
                    "baseline_loss": float(by_model[baseline]),
                    "loss_diff": float(by_model["timesfm3"] - by_model[baseline]),
                })
    return pd.DataFrame([row for row in rows if row["kind"] != "cumulative_component"])


def _holm_adjust(p_values: np.ndarray) -> np.ndarray:
    """Holm step-down adjusted p-values, returned in original order."""
    if len(p_values) == 0:
        return p_values
    order = np.argsort(p_values)
    adjusted_sorted = np.maximum.accumulate(
        (len(p_values) - np.arange(len(p_values))) * p_values[order]
    ).clip(0, 1)
    adjusted = np.empty_like(adjusted_sorted)
    adjusted[order] = adjusted_sorted
    return adjusted


def compare_forecasts(
    forecasts: pd.DataFrame,
    cumulative_horizons: Iterable[int],
    *,
    n_boot: int = 10_000,
    block_len: int = 4,
    seed: int = 20261014,
) -> dict[str, Any]:
    """Compute paired MAE-loss differences, stationary-bootstrap CIs, and Holm p-values.

    Negative differences favor TimesFM. Origin vectors are resampled jointly
    within each segment so BTC/ETH and model-mode comparisons retain their
    contemporaneous dependence. The full fixed family of examined leads and
    cumulative horizons receives one Holm correction.
    """
    validate_forecasts(forecasts)
    comparisons = _comparison_rows(forecasts, cumulative_horizons)
    keys = ["segment", "kind", "horizon", "mode", "symbol", "baseline"]
    output: list[dict[str, Any]] = []
    rng = np.random.default_rng(seed)

    for segment, segment_rows in comparisons.groupby("segment", sort=True):
        origin_order = sorted(segment_rows["origin"].unique())
        columns: list[tuple[tuple[Any, ...], np.ndarray]] = []
        for identity, group in segment_rows.groupby(keys[1:], sort=True):
            by_origin = group.set_index("origin").reindex(origin_order)
            differences = by_origin["loss_diff"].to_numpy(dtype=float)
            if not np.isfinite(differences).all():
                raise ValueError("comparison family has missing or unpaired origin losses")
            columns.append(((segment, *identity), differences))

        matrix = np.column_stack([values for _, values in columns])
        block = min(max(1, int(block_len)), len(origin_order))
        indices = stationary_bootstrap_indices(len(origin_order), n_boot, block, rng)
        boot_means = np.empty((n_boot, matrix.shape[1]), dtype=float)
        # Limit temporary allocations while preserving joint origin resampling.
        for start in range(0, n_boot, 250):
            stop = min(start + 250, n_boot)
            boot_means[start:stop] = matrix[indices[start:stop]].mean(axis=1)
        observed = matrix.mean(axis=0)
        centered = matrix - observed
        centered_boot = np.empty_like(boot_means)
        for start in range(0, n_boot, 250):
            stop = min(start + 250, n_boot)
            centered_boot[start:stop] = centered[indices[start:stop]].mean(axis=1)
        for column_index, (identity, values) in enumerate(columns):
            _, kind, horizon, mode, symbol, baseline = identity
            model_mae = float(segment_rows.loc[
                (segment_rows["kind"] == kind)
                & (segment_rows["horizon"] == horizon)
                & (segment_rows["mode"] == mode)
                & (segment_rows["symbol"] == symbol)
                & (segment_rows["baseline"] == baseline), "model_loss"
            ].mean())
            baseline_mae = float(segment_rows.loc[
                (segment_rows["kind"] == kind)
                & (segment_rows["horizon"] == horizon)
                & (segment_rows["mode"] == mode)
                & (segment_rows["symbol"] == symbol)
                & (segment_rows["baseline"] == baseline), "baseline_loss"
            ].mean())
            point = float(observed[column_index])
            low, high = np.quantile(boot_means[:, column_index], [0.025, 0.975])
            null_samples = centered_boot[:, column_index]
            p_value = float((1 + np.count_nonzero(np.abs(null_samples) >= abs(point))) / (n_boot + 1))
            output.append({
                "segment": segment, "kind": kind, "horizon": int(horizon),
                "mode": mode, "symbol": symbol, "baseline": baseline,
                "n_origins": len(origin_order), "timesfm_mae": model_mae,
                "baseline_mae": baseline_mae, "mae_difference": point,
                "skill": float(1 - model_mae / baseline_mae) if baseline_mae else None,
                "ci95_low": float(low), "ci95_high": float(high),
                "p_value_two_sided": p_value, "block_length_origins": block,
                "bootstrap_replicates": n_boot,
            })

    adjusted = _holm_adjust(np.asarray([row["p_value_two_sided"] for row in output]))
    for row, value in zip(output, adjusted, strict=True):
        row["p_value_holm"] = float(value)
    return {
        "status": "exploratory_post_hoc",
        "estimand": "paired difference in per-origin absolute forecast loss (TimesFM minus baseline)",
        "interpretation": "negative differences favor TimesFM; intervals and p-values do not imply trading value",
        "resampling": {
            "method": "Politis-Romano stationary bootstrap",
            "block_length_origins": int(block_len),
            "origin_units": "weekly historical origins; daily post-release origins",
            "joint_resampling": "same origin indices across BTC/ETH and univariate/multivariate comparisons within segment",
            "replicates": int(n_boot), "seed": int(seed),
        },
        "multiplicity": {
            "method": "Holm step-down family-wise error correction",
            "family_size": len(output),
            "family": "all saved lead and cumulative-horizon MAE comparisons across segments, assets, modes, and baselines",
        },
        "comparisons": output,
    }
