"""Adapters for reading standard Freqtrade backtest ZIP archives.

This module deliberately contains no experiment-specific strategy names or
output paths. It provides the small amount of I/O needed by research drivers;
metric calculations remain in :mod:`evaluation.layers` and :mod:`evaluation.dsr`.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


def load_wallet_curve(zip_path: Path) -> pd.Series:
    """Load a daily total-quote wallet curve from a Freqtrade ZIP."""
    with zipfile.ZipFile(zip_path) as archive:
        wallet_files = [name for name in archive.namelist() if name.endswith("_wallet.feather")]
        if not wallet_files:
            raise FileNotFoundError(f"no wallet feather in {zip_path.name}")
        with archive.open(wallet_files[0]) as stream:
            frame = pd.read_feather(stream)
    frame = frame[["date", "total_quote"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    return frame.set_index("date")["total_quote"].resample("1D").last().dropna()


def load_daily_returns(zip_path: Path) -> pd.Series:
    """Load daily log returns from a Freqtrade wallet curve."""
    wallet = load_wallet_curve(zip_path)
    return np.log(wallet / wallet.shift(1)).dropna()


def load_trade_returns(zip_path: Path) -> pd.Series:
    """Load per-trade profit ratios from a Freqtrade backtest ZIP."""
    with zipfile.ZipFile(zip_path) as archive:
        result_files = [
            name for name in archive.namelist()
            if name.endswith(".json") and "config" not in name and "meta" not in name
        ]
        if not result_files:
            raise FileNotFoundError(f"no result JSON in {zip_path.name}")
        payload = json.loads(archive.read(result_files[0]))
    strategy = next(iter(payload["strategy"].values()))
    trades = pd.DataFrame(strategy["trades"])
    if trades.empty:
        return pd.Series(dtype=float)
    return trades["profit_ratio"]


def build_returns_matrix(zip_paths: dict[str, Path]) -> pd.DataFrame:
    """Join daily log returns from multiple ZIPs on a common date index."""
    return pd.DataFrame({code: load_daily_returns(path) for code, path in zip_paths.items()}).fillna(0.0)
