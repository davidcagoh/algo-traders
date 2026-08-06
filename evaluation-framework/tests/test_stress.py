from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from evaluation.stress import (
    capacity_curve,
    depth_from_ohlcv,
    flash_crash_scenario,
    slippage_at_risk,
)


@pytest.fixture
def ohlcv(rng) -> pd.DataFrame:
    n = 100
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    close = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    high = close * 1.01
    low = close * 0.99
    volume = rng.uniform(1000, 5000, n)
    return pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume}, index=idx)


def test_depth_from_ohlcv_positive(ohlcv):
    depth = depth_from_ohlcv(ohlcv)
    assert (depth > 0).all()
    assert not depth.isna().any()


def test_slippage_at_risk_increases_with_order_size(ohlcv):
    depth = depth_from_ohlcv(ohlcv)
    small = slippage_at_risk(1_000, depth)
    large = slippage_at_risk(1_000_000, depth)
    assert large.slippage_bps > small.slippage_bps
    assert small.is_proxy is True


def test_slippage_at_risk_rejects_empty_depth():
    with pytest.raises(ValueError):
        slippage_at_risk(1000, pd.Series(dtype=float))


def test_flash_crash_scenario_amplifies_worst_return():
    r = pd.Series([0.01, -0.05, 0.02, -0.01])
    stressed = flash_crash_scenario(r, multiplier=3.0)
    assert stressed.min() == pytest.approx(-0.15)
    assert stressed.drop(stressed.idxmin()).equals(r.drop(r.idxmin()))


def test_capacity_curve_monotonic(ohlcv):
    depth = depth_from_ohlcv(ohlcv)
    curve = capacity_curve([1_000, 10_000, 100_000], depth)
    assert curve["slippage_bps"].is_monotonic_increasing
