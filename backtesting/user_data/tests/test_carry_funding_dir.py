"""
Verify FundingCarry / HmmCarry resolve the funding-data directory via
CARRY_FUNDING_EXCHANGE at call time, so the same strategy code can read
either user_data/data/hyperliquid/funding/ or user_data/data/binance/funding/
depending on which venue the backtest is running on.

Regression target: the previously hardcoded `FUNDING_DIR = Path(
"user_data/data/hyperliquid/funding")` blocked cross-venue runs.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGIES_DIR = REPO_ROOT / "user_data" / "strategies"


def _write_funding(parquet_path: Path, rate: float) -> None:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        {
            "time": pd.to_datetime(
                ["2024-01-01T00:00:00Z", "2024-01-01T08:00:00Z"], utc=True
            ),
            "coin": ["BTC", "BTC"],
            "funding_rate": [rate, rate],
            "premium": [0.0, 0.0],
        }
    )
    df.to_parquet(parquet_path, index=False)


def _import_strategy(module_name: str):
    if str(STRATEGIES_DIR) not in sys.path:
        sys.path.insert(0, str(STRATEGIES_DIR))
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


@pytest.mark.parametrize("module_name", ["FundingCarry", "HmmCarry"])
def test_default_routes_to_hyperliquid(monkeypatch, tmp_path, module_name):
    monkeypatch.delenv("CARRY_FUNDING_EXCHANGE", raising=False)
    monkeypatch.chdir(tmp_path)
    _write_funding(
        tmp_path / "user_data/data/hyperliquid/funding/BTC-funding.parquet", 0.0001
    )
    _write_funding(
        tmp_path / "user_data/data/binance/funding/BTC-funding.parquet", 0.0009
    )

    mod = _import_strategy(module_name)
    df = mod._load_funding("BTC")

    assert not df.empty, f"{module_name} returned empty frame for default venue"
    assert df["funding_rate"].iloc[0] == pytest.approx(0.0001), (
        f"{module_name} default should read hyperliquid, got {df['funding_rate'].iloc[0]}"
    )


@pytest.mark.parametrize("module_name", ["FundingCarry", "HmmCarry"])
def test_env_routes_to_binance(monkeypatch, tmp_path, module_name):
    monkeypatch.setenv("CARRY_FUNDING_EXCHANGE", "binance")
    monkeypatch.chdir(tmp_path)
    _write_funding(
        tmp_path / "user_data/data/hyperliquid/funding/BTC-funding.parquet", 0.0001
    )
    _write_funding(
        tmp_path / "user_data/data/binance/funding/BTC-funding.parquet", 0.0009
    )

    mod = _import_strategy(module_name)
    df = mod._load_funding("BTC")

    assert not df.empty, f"{module_name} returned empty frame for binance"
    assert df["funding_rate"].iloc[0] == pytest.approx(0.0009), (
        f"{module_name} should read binance when env set, got {df['funding_rate'].iloc[0]}"
    )


@pytest.mark.parametrize("module_name", ["FundingCarry", "HmmCarry"])
def test_missing_file_returns_empty(monkeypatch, tmp_path, module_name):
    monkeypatch.setenv("CARRY_FUNDING_EXCHANGE", "binance")
    monkeypatch.chdir(tmp_path)
    # no parquet files written

    mod = _import_strategy(module_name)
    df = mod._load_funding("BTC")

    assert df.empty, f"{module_name} should return empty frame when funding file missing"
