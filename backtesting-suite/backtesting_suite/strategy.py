"""Minimal strategy contract: research logic in, ideal target weights out."""

from __future__ import annotations

import importlib
from typing import Any, Mapping, Protocol, runtime_checkable

import numpy as np
import pandas as pd

from backtesting_suite.data import DataBundle


class StrategyError(ValueError):
    """Raised when strategy loading or output validation fails."""


@runtime_checkable
class Strategy(Protocol):
    def generate_targets(
        self, data: DataBundle, params: Mapping[str, Any]
    ) -> pd.DataFrame: ...


def load_strategy(import_path: str) -> Strategy:
    module_name, object_name = import_path.split(":", 1)
    module = importlib.import_module(module_name)
    strategy_object = getattr(module, object_name)
    strategy = strategy_object() if isinstance(strategy_object, type) else strategy_object
    if not isinstance(strategy, Strategy):
        raise StrategyError(f"{import_path} does not implement generate_targets(data, params)")
    return strategy


def normalize_targets(targets: pd.DataFrame, data: DataBundle) -> pd.DataFrame:
    if not isinstance(targets, pd.DataFrame):
        raise StrategyError("generate_targets must return a pandas DataFrame")
    unknown = set(targets.columns) - set(data.symbols)
    if unknown:
        raise StrategyError(f"strategy returned unknown symbols {sorted(unknown)}")
    if not isinstance(targets.index, pd.DatetimeIndex):
        raise StrategyError("target weights must use a DatetimeIndex")
    index = targets.index
    index = index.tz_localize("UTC") if index.tz is None else index.tz_convert("UTC")
    targets = targets.copy()
    targets.index = index
    if targets.index.has_duplicates:
        raise StrategyError("target weights contain duplicate timestamps")
    result = targets.reindex(index=data.index, columns=data.symbols).fillna(0.0).astype(float)
    if not np.isfinite(result.to_numpy()).all():
        raise StrategyError("target weights contain non-finite values")
    return result


def assert_no_lookahead(
    strategy: Strategy,
    data: DataBundle,
    params: Mapping[str, Any],
    full_targets: pd.DataFrame,
    checkpoints: int = 2,
) -> None:
    """Check that truncating future data does not alter earlier target weights."""
    if len(data.index) < 20:
        return
    fractions = np.linspace(0.55, 0.85, checkpoints)
    for fraction in fractions:
        position = max(1, min(len(data.index) - 2, int(len(data.index) * fraction)))
        cutoff = data.index[position]
        sliced = data.slice(cutoff)
        partial = normalize_targets(strategy.generate_targets(sliced, params), sliced)
        expected = full_targets.loc[:cutoff]
        try:
            pd.testing.assert_frame_equal(partial, expected, check_exact=False, rtol=1e-12, atol=1e-12)
        except AssertionError as exc:
            raise StrategyError(
                f"look-ahead check failed at {cutoff}: targets changed when future data was removed"
            ) from exc
