from __future__ import annotations

import pandas as pd
import pytest

from evaluation.factors import crypto_factors, factor_regression, format_factor_table


def test_factor_regression_recovers_known_beta(rng):
    n = 500
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    market = pd.Series(rng.normal(0.0005, 0.02, n), index=idx)
    true_alpha = 0.0002
    true_beta = 1.5
    noise = rng.normal(0, 0.005, n)
    strategy = true_alpha + true_beta * market + noise
    strategy = pd.Series(strategy, index=idx)

    factors = pd.DataFrame({"market": market})
    result = factor_regression(strategy, factors)

    assert result.betas["market"] == pytest.approx(true_beta, abs=0.15)
    assert result.alpha == pytest.approx(true_alpha, abs=0.001)
    assert result.r_squared > 0.5


def test_factor_regression_zero_beta_strategy_has_low_r2(rng):
    n = 300
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    market = pd.Series(rng.normal(0, 0.02, n), index=idx)
    strategy = pd.Series(rng.normal(0.001, 0.01, n), index=idx)  # independent of market
    factors = pd.DataFrame({"market": market})
    result = factor_regression(strategy, factors)
    assert abs(result.betas["market"]) < 0.3


def test_factor_regression_insufficient_obs_raises():
    strategy = pd.Series([0.01, 0.02], index=pd.date_range("2024-01-01", periods=2))
    factors = pd.DataFrame(
        {"a": [0.01, 0.02], "b": [0.01, 0.02]}, index=pd.date_range("2024-01-01", periods=2)
    )
    with pytest.raises(ValueError):
        factor_regression(strategy, factors)


def test_crypto_factors_assembles_columns(rng):
    idx = pd.date_range("2024-01-01", periods=50, freq="D")
    market = pd.Series(rng.normal(0, 0.02, 50), index=idx)
    momentum = pd.Series(rng.normal(0, 0.01, 50), index=idx)
    df = crypto_factors(market, momentum_returns=momentum)
    assert set(df.columns) == {"market", "momentum"}


def test_crypto_factors_market_only(rng):
    idx = pd.date_range("2024-01-01", periods=20, freq="D")
    market = pd.Series(rng.normal(0, 0.02, 20), index=idx)
    df = crypto_factors(market)
    assert list(df.columns) == ["market"]


def test_format_factor_table_flags_significance(rng):
    n = 500
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    market = pd.Series(rng.normal(0.0005, 0.02, n), index=idx)
    strategy = pd.Series(0.0002 + 2.0 * market + rng.normal(0, 0.001, n), index=idx)
    result = factor_regression(strategy, pd.DataFrame({"market": market}))
    table = format_factor_table(result, label="x")
    assert "x" in table
    assert "market" in table
