from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from evaluation.dsr import (
    compute_dsr_table,
    deflated_sharpe,
    expected_max_sharpe,
    format_dsr_table,
    is_dsr_binding,
)


def test_expected_max_sharpe_grows_with_trials():
    small = expected_max_sharpe(sharpe_var=1.0, n_trials=5)
    large = expected_max_sharpe(sharpe_var=1.0, n_trials=500)
    assert large > small


def test_deflated_sharpe_short_series_zero():
    assert deflated_sharpe(1.0, 0.1, 0.0, 3.0, n_obs=2) == 0.0


def test_deflated_sharpe_in_unit_interval():
    d = deflated_sharpe(sharpe=1.5, sharpe_star=0.2, skew=0.1, kurt=3.5, n_obs=300)
    assert 0.0 <= d <= 1.0


def test_compute_dsr_table_requires_n_trials(gaussian_wallet):
    with pytest.raises(TypeError):
        compute_dsr_table({"a": gaussian_wallet})


def test_compute_dsr_table_rejects_n_trials_below_candidates(gaussian_wallet, trending_wallet):
    with pytest.raises(ValueError):
        compute_dsr_table({"a": gaussian_wallet, "b": trending_wallet}, n_trials=1)


def test_compute_dsr_table_under_deflates_less_with_more_trials(gaussian_wallet, trending_wallet):
    wallets = {"a": gaussian_wallet, "b": trending_wallet}
    low = compute_dsr_table(wallets, n_trials=2)
    high = compute_dsr_table(wallets, n_trials=1000)
    low_by_label = {r.label: r.dsr for r in low}
    high_by_label = {r.label: r.dsr for r in high}
    for label, low_dsr in low_by_label.items():
        assert high_by_label[label] <= low_dsr


def test_compute_dsr_table_empty_wallets():
    assert compute_dsr_table({}, n_trials=10) == []


def test_compute_dsr_table_explicit_sharpe_var_overrides_wallet_estimate(rng):
    """Regression: a narrow, near-duplicate family of wallets (near-identical
    Sharpes) understates cross-trial Sharpe variance and inflates DSR.
    Passing an explicit (wider-search) sharpe_var must be honored instead of
    the narrow wallets-only estimate."""

    def wallet(mean_r: float) -> pd.Series:
        idx = pd.date_range("2024-01-01", periods=501, freq="D", tz="UTC")
        r = rng.normal(mean_r, 0.02, 500)
        levels = 100.0 * np.concatenate([[1.0], np.cumprod(1.0 + r)])
        return pd.Series(levels, index=idx)

    # Two near-duplicate parameter variants: same drift, same noise scale.
    wallets = {"variant_a": wallet(0.0008), "variant_b": wallet(0.00082)}
    narrow = compute_dsr_table(wallets, n_trials=10)
    # A wide-search variance (as if drawn from a diverse candidate pool)
    # should raise SR* and push DSR down, not up.
    wide_var = compute_dsr_table(wallets, n_trials=10, sharpe_var=50.0)

    assert wide_var[0].sharpe_star > narrow[0].sharpe_star
    narrow_by_label = {r.label: r.dsr for r in narrow}
    wide_by_label = {r.label: r.dsr for r in wide_var}
    for label, narrow_dsr in narrow_by_label.items():
        assert wide_by_label[label] <= narrow_dsr


def test_format_dsr_table_reports_real_vs_reported_n(gaussian_wallet, trending_wallet):
    rows = compute_dsr_table({"a": gaussian_wallet, "b": trending_wallet}, n_trials=40)
    table = format_dsr_table(rows, n_trials=40)
    assert "N_trials=40" in table
    assert "N_reported=2" in table


def test_format_dsr_table_empty():
    assert format_dsr_table([], n_trials=0) == "_(no DSR rows)_"


def test_is_dsr_binding_low_n(flat_wallet):
    binding, reason = is_dsr_binding(flat_wallet.pct_change().dropna())
    assert binding is False
    assert "insufficient daily obs" in reason


def test_is_dsr_binding_fat_tails_still_binding(fat_tailed_wallet):
    """Regression: fat kurtosis alone must NOT demote DSR (2026-08-06 fix) —
    only insufficient N does. A 500-obs fat-tailed series stays binding."""
    from evaluation.layers import daily_log_returns

    r = daily_log_returns(fat_tailed_wallet)
    binding, reason = is_dsr_binding(r)
    assert binding is True
    assert "binding" in reason
