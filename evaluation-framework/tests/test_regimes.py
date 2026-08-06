from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from evaluation.regimes import label_regimes, regime_metrics, regime_stability


def test_label_regimes_drawdown_detects_bear(regime_switching_returns):
    wallet = 100.0 * (1 + regime_switching_returns).cumprod()
    labels = label_regimes(wallet, method="drawdown", dd_threshold=0.02)
    assert set(labels.unique()) <= {"bull", "bear"}
    assert "bear" in labels.values


def test_label_regimes_sma_method(regime_switching_returns):
    wallet = 100.0 * (1 + regime_switching_returns).cumprod()
    labels = label_regimes(wallet, method="sma", window=30)
    assert set(labels.unique()) <= {"bull", "bear"}


def test_label_regimes_vol_tercile_method(regime_switching_returns):
    wallet = 100.0 * (1 + regime_switching_returns).cumprod()
    labels = label_regimes(wallet, method="vol_tercile", window=20)
    assert set(labels.unique()) <= {"low_vol", "mid_vol", "high_vol"}


def test_label_regimes_unknown_method_raises():
    wallet = pd.Series([100.0, 101.0, 102.0])
    with pytest.raises(ValueError):
        label_regimes(wallet, method="bogus")


def test_regime_metrics_splits_by_label(regime_switching_returns):
    wallet = 100.0 * (1 + regime_switching_returns).cumprod()
    labels = label_regimes(wallet, method="drawdown", dd_threshold=0.02)
    result = regime_metrics(wallet, labels)
    assert len(result) > 0
    for m in result.values():
        assert m.n_obs > 0


def test_regime_metrics_skips_tiny_regimes():
    idx = pd.date_range("2024-01-01", periods=10, freq="D")
    wallet = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109], index=idx, dtype=float)
    labels = pd.Series(["a"] * 2 + ["b"] * 8, index=idx)
    result = regime_metrics(wallet, labels)
    assert "a" not in result  # only 2 obs, below the 3-obs floor


def test_regime_stability_sums_to_one_for_positive_regimes():
    from evaluation.layers import compute

    idx1 = pd.date_range("2024-01-01", periods=100, freq="D")
    idx2 = pd.date_range("2024-04-01", periods=100, freq="D")
    up_wallet = pd.Series(100 * (1.01 ** np.arange(100)), index=idx1)
    down_wallet = pd.Series(100 * (0.99 ** np.arange(100)), index=idx2)
    result = {"bull": compute(up_wallet), "bear": compute(down_wallet)}
    stability = regime_stability(result)
    assert stability["bull"] == pytest.approx(1.0)
    assert stability["bear"] == 0.0


def test_regime_stability_all_negative_returns_nan():
    from evaluation.layers import compute

    idx = pd.date_range("2024-01-01", periods=50, freq="D")
    wallet = pd.Series(100 * (0.99 ** np.arange(50)), index=idx)
    result = {"only": compute(wallet)}
    stability = regime_stability(result)
    import math

    assert math.isnan(stability["only"])
