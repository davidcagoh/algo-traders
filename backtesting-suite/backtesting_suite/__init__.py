"""Platform-agnostic research backtesting."""

from backtesting_suite.config import RunConfig, load_config
from backtesting_suite.data import DataBundle, load_data_bundle
from backtesting_suite.execution.bar import BarExecutionModel
from backtesting_suite.result import BacktestResult
from backtesting_suite.runner import run_backtest
from backtesting_suite.strategy import Strategy, load_strategy

__all__ = [
    "BacktestResult",
    "BarExecutionModel",
    "DataBundle",
    "RunConfig",
    "Strategy",
    "load_config",
    "load_data_bundle",
    "load_strategy",
    "run_backtest",
]
