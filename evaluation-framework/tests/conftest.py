"""Shared synthetic fixtures. Seeded for determinism."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _wallet_from_returns(returns: np.ndarray, start: float = 100.0) -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=len(returns) + 1, freq="D", tz="UTC")
    levels = start * np.concatenate([[1.0], np.cumprod(1.0 + returns)])
    return pd.Series(levels, index=idx)


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(0)


@pytest.fixture
def gaussian_wallet(rng: np.random.Generator) -> pd.Series:
    """~2 years of daily returns, mild positive drift, near-Gaussian."""
    r = rng.normal(0.0008, 0.02, 500)
    return _wallet_from_returns(r)


@pytest.fixture
def fat_tailed_wallet(rng: np.random.Generator) -> pd.Series:
    """Student-t returns, excess kurtosis roughly 6."""
    df = 4.5
    raw = rng.standard_t(df, 500)
    scale = 0.02 / np.sqrt(df / (df - 2))
    r = 0.0005 + raw * scale
    return _wallet_from_returns(r)


@pytest.fixture
def trending_wallet(rng: np.random.Generator) -> pd.Series:
    """Strong, near-deterministic uptrend — used as a known-edge case."""
    r = np.full(500, 0.002) + rng.normal(0.0, 0.001, 500)
    return _wallet_from_returns(r)


@pytest.fixture
def flat_wallet() -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=100, freq="D", tz="UTC")
    return pd.Series(100.0, index=idx)


@pytest.fixture
def noise_trial_matrix(rng: np.random.Generator) -> pd.DataFrame:
    """T=1000 obs x N=20 trials, all pure zero-mean noise (known null)."""
    data = rng.normal(0.0, 0.01, size=(1000, 20))
    idx = pd.date_range("2022-01-01", periods=1000, freq="D", tz="UTC")
    cols = [f"trial_{i}" for i in range(20)]
    return pd.DataFrame(data, index=idx, columns=cols)


@pytest.fixture
def regime_switching_returns(rng: np.random.Generator) -> pd.Series:
    """250 up-trend days followed by 250 down-trend days."""
    up = rng.normal(0.0015, 0.015, 250)
    down = rng.normal(-0.0015, 0.02, 250)
    r = np.concatenate([up, down])
    idx = pd.date_range("2023-01-01", periods=len(r), freq="D", tz="UTC")
    return pd.Series(r, index=idx)
