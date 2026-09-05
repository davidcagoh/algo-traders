"""Execution protocol shared by built-in and user-supplied simulators."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd

from backtesting_suite.config import ExecutionConfig
from backtesting_suite.data import DataBundle
from backtesting_suite.result import BacktestResult


@runtime_checkable
class ExecutionModel(Protocol):
    def simulate(
        self,
        data: DataBundle,
        targets: pd.DataFrame,
        config: ExecutionConfig,
    ) -> BacktestResult: ...
