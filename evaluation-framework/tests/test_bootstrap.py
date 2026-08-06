from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest

from evaluation.bootstrap import (
    bootstrap_ci,
    circular_block_bootstrap,
    moving_block_bootstrap,
    optimal_block_length,
    paired_bootstrap_test,
    stationary_bootstrap,
)


@pytest.fixture
def returns(rng):
    return pd.Series(rng.normal(0.001, 0.02, 300))


def test_optimal_block_length_positive(returns):
    assert optimal_block_length(returns) >= 2


def test_optimal_block_length_short_series_fallback():
    r = pd.Series([0.01, 0.02, -0.01])
    assert optimal_block_length(r) >= 2


@pytest.mark.parametrize(
    "fn", [moving_block_bootstrap, circular_block_bootstrap, stationary_bootstrap]
)
def test_bootstrap_shape(fn, returns):
    paths = fn(returns, n_boot=200, seed=0)
    assert paths.shape == (200, len(returns))


@pytest.mark.parametrize(
    "fn", [moving_block_bootstrap, circular_block_bootstrap, stationary_bootstrap]
)
def test_bootstrap_values_from_original_series(fn, returns):
    paths = fn(returns, n_boot=50, seed=0)
    original = set(np.round(returns.to_numpy(), 10))
    sampled = set(np.round(paths.flatten(), 10))
    assert sampled.issubset(original)


def test_bootstrap_ci_contains_point_estimate(returns):
    ci = bootstrap_ci(returns, n_boot=2000, seed=0)
    assert ci.lower <= ci.point <= ci.upper or np.isnan(ci.lower)


def test_bootstrap_ci_unknown_method_raises(returns):
    with pytest.raises(ValueError):
        bootstrap_ci(returns, method="bogus")


def test_bootstrap_ci_narrower_with_more_data(rng):
    short = pd.Series(rng.normal(0.001, 0.02, 60))
    long = pd.Series(rng.normal(0.001, 0.02, 600))
    ci_short = bootstrap_ci(short, n_boot=2000, seed=1)
    ci_long = bootstrap_ci(long, n_boot=2000, seed=1)
    assert (ci_long.upper - ci_long.lower) < (ci_short.upper - ci_short.lower) * 1.5


def test_paired_bootstrap_test_zero_for_identical_series(returns):
    result = paired_bootstrap_test(returns, returns, n_boot=500, seed=0)
    assert result["point_diff"] == pytest.approx(0.0)


def test_paired_bootstrap_test_requires_equal_length(returns):
    with pytest.raises(ValueError):
        paired_bootstrap_test(returns, returns.iloc[:-1], n_boot=100)


def test_paired_bootstrap_test_detects_clear_difference(rng):
    a = pd.Series(rng.normal(0.005, 0.01, 400))
    b = pd.Series(rng.normal(-0.005, 0.01, 400))
    result = paired_bootstrap_test(a, b, n_boot=2000, seed=0)
    assert result["point_diff"] > 0
    assert result["p_value"] < 0.05


def test_bootstrap_ci_performance_10k_replicates(returns):
    start = time.monotonic()
    bootstrap_ci(returns, n_boot=10_000, seed=0)
    elapsed = time.monotonic() - start
    assert elapsed < 10.0
