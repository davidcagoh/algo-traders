from __future__ import annotations

import pytest

from evaluation.intervals import format_markdown_table_with_ci, metrics_with_ci


def test_metrics_with_ci_returns_all_three(gaussian_wallet):
    metrics, cis = metrics_with_ci(gaussian_wallet, n_boot=500, seed=0)
    assert set(cis.keys()) == {"sharpe", "cagr_pct", "calmar"}
    assert metrics.sharpe == pytest.approx(cis["sharpe"].point)


def test_format_markdown_table_with_ci_contains_bounds(gaussian_wallet):
    metrics, cis = metrics_with_ci(gaussian_wallet, n_boot=500, seed=0)
    table = format_markdown_table_with_ci(metrics, cis, title="x")
    assert "block-bootstrap CIs" in table
    assert "Sharpe:" in table
