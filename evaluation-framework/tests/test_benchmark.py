from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from evaluation.benchmark import (
    buy_and_hold,
    excess_metrics,
    format_benchmark_table,
    peer_benchmark,
)


def test_buy_and_hold_equal_weight(rng):
    idx = pd.date_range("2024-01-01", periods=100, freq="D")
    prices = pd.DataFrame(
        {
            "a": 100 * np.cumprod(1 + rng.normal(0.001, 0.02, 100)),
            "b": 100 * np.cumprod(1 + rng.normal(0.001, 0.02, 100)),
        },
        index=idx,
    )
    bh = buy_and_hold(prices)
    assert bh.iloc[0] == pytest.approx(100.0)
    assert len(bh) == 100


def test_peer_benchmark_equal_weight(rng):
    idx = pd.date_range("2024-01-01", periods=50, freq="D")
    returns = pd.DataFrame(
        {"s1": rng.normal(0.001, 0.01, 50), "s2": rng.normal(0.001, 0.01, 50)}, index=idx
    )
    peer = peer_benchmark(returns)
    assert len(peer) == 50
    assert peer.iloc[0] > 0


def test_peer_benchmark_empty_columns():
    empty = pd.DataFrame(index=pd.date_range("2024-01-01", periods=5))
    assert peer_benchmark(empty).empty


def test_peer_benchmark_unsupported_weights_raises():
    df = pd.DataFrame({"a": [0.01, 0.02]})
    with pytest.raises(ValueError):
        peer_benchmark(df, weights="risk_parity")


def test_excess_metrics_zero_when_identical(gaussian_wallet):
    m = excess_metrics(gaussian_wallet, gaussian_wallet)
    assert m.excess_cagr_pct == pytest.approx(0.0, abs=1e-6)
    assert m.excess_sharpe == pytest.approx(0.0, abs=1e-6)


def test_excess_metrics_positive_for_outperformer(gaussian_wallet, trending_wallet):
    m = excess_metrics(trending_wallet, gaussian_wallet)
    assert m.excess_cagr_pct > 0


def test_format_benchmark_table_contains_label(gaussian_wallet, trending_wallet):
    m = excess_metrics(trending_wallet, gaussian_wallet)
    table = format_benchmark_table(m, label="test")
    assert "test" in table
    assert "Excess CAGR" in table
