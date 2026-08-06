from __future__ import annotations

import math

import pandas as pd
import pytest

from evaluation.layers import (
    cagr,
    calmar,
    compute,
    cvar_5,
    format_markdown_table,
    kurt_excess,
    max_drawdown,
    sharpe,
    skew,
    sqn,
    tail_ratio,
)


def test_cagr_positive_drift(gaussian_wallet):
    c = cagr(gaussian_wallet)
    assert c > 0


def test_cagr_flat_wallet_is_zero(flat_wallet):
    """Flat wallet: total return ratio is 1, so CAGR is 0, not NaN."""
    assert cagr(flat_wallet) == 0.0


def test_sharpe_flat_wallet_nan(flat_wallet):
    assert math.isnan(sharpe(flat_wallet))


def test_max_drawdown_bounds(gaussian_wallet):
    mdd = max_drawdown(gaussian_wallet)
    assert 0 <= mdd <= 1


def test_calmar_zero_mdd_nan(flat_wallet):
    assert math.isnan(calmar(flat_wallet))


def test_sqn_short_series_nan():
    assert math.isnan(sqn(pd.Series([0.01])))


def test_sqn_zero_std_nan():
    assert math.isnan(sqn(pd.Series([0.01, 0.01, 0.01])))


def test_skew_short_series_zero():
    assert skew(pd.Series([0.01, 0.02])) == 0.0


def test_kurt_excess_short_series_zero():
    assert kurt_excess(pd.Series([0.01, 0.02, 0.03])) == 0.0


def test_tail_ratio_short_series_nan():
    assert math.isnan(tail_ratio(pd.Series(range(10), dtype=float)))


def test_cvar_5_short_series_nan():
    assert math.isnan(cvar_5(pd.Series(range(10), dtype=float)))


def test_fat_tailed_wallet_has_high_kurtosis(fat_tailed_wallet):
    from evaluation.layers import daily_log_returns

    r = daily_log_returns(fat_tailed_wallet)
    assert kurt_excess(r) > 1.0


def test_compute_returns_layered_metrics(gaussian_wallet):
    m = compute(gaussian_wallet)
    assert m.n_obs == len(gaussian_wallet) - 1
    assert m.annualisation == pytest.approx(252.0)
    assert not math.isnan(m.sharpe)


def test_compute_with_explicit_trade_returns(gaussian_wallet):
    trades = pd.Series([0.01, -0.02, 0.03, 0.015, -0.01])
    m = compute(gaussian_wallet, trade_returns=trades)
    assert not math.isnan(m.sqn)


def test_format_markdown_table_contains_all_layers(gaussian_wallet):
    m = compute(gaussian_wallet)
    table = format_markdown_table(m, title="test")
    assert "### test" in table
    for tag in ("L1", "L2", "L3", "L5"):
        assert f"| {tag} |" in table
