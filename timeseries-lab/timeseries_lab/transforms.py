"""Small, explicit transform language for interactive series queries."""

from __future__ import annotations

import numpy as np
import pandas as pd


class TransformError(ValueError):
    """Raised when a pipe transform is unknown or malformed."""


def split_query(query: str) -> tuple[str, list[str]]:
    parts = [part.strip() for part in query.split("|")]
    return parts[0], [part for part in parts[1:] if part]


def apply_transforms(series: pd.Series, transforms: list[str]) -> pd.Series:
    result = series.copy()
    for expression in transforms:
        parts = [part.strip() for part in expression.split(":")]
        operation = parts[0].lower()
        arguments = parts[1:]
        if operation in {"pct_change", "returns"}:
            periods = int(arguments[0]) if arguments else 1
            result = result.pct_change(periods, fill_method=None)
        elif operation == "log_return":
            periods = int(arguments[0]) if arguments else 1
            result = np.log(result.where(result > 0)).diff(periods)
        elif operation == "log":
            result = np.log(result.where(result > 0))
        elif operation == "diff":
            result = result.diff(int(arguments[0]) if arguments else 1)
        elif operation == "lag":
            result = result.shift(int(arguments[0]) if arguments else 1)
        elif operation == "shift_time":
            if len(arguments) != 1:
                raise TransformError("shift_time requires a duration, e.g. shift_time:1D")
            result.index = result.index + pd.Timedelta(arguments[0])
        elif operation == "rolling_mean":
            result = result.rolling(_window(arguments, operation)).mean()
        elif operation == "rolling_std":
            result = result.rolling(_window(arguments, operation)).std()
        elif operation == "rolling_zscore":
            window = _window(arguments, operation)
            rolling = result.rolling(window)
            result = (result - rolling.mean()) / rolling.std()
        elif operation == "zscore":
            result = (result - result.mean()) / result.std()
        elif operation in {"normalize", "rebase"}:
            valid = result.dropna()
            result = result / valid.iloc[0] * 100.0 if not valid.empty else result
        elif operation == "resample":
            if not arguments:
                raise TransformError("resample requires a frequency, e.g. resample:W:last")
            method = arguments[1].lower() if len(arguments) > 1 else "last"
            sampler = result.resample(arguments[0])
            if method not in {"last", "first", "mean", "sum", "max", "min"}:
                raise TransformError(f"unsupported resample method {method!r}")
            result = getattr(sampler, method)()
        else:
            raise TransformError(f"unknown transform {operation!r}")
    return result


def _window(arguments: list[str], operation: str) -> int:
    if len(arguments) != 1 or int(arguments[0]) <= 0:
        raise TransformError(f"{operation} requires a positive window")
    return int(arguments[0])
