from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from evaluation.spa import format_spa_table, spa_test


def _zero_benchmark(index: pd.Index) -> pd.Series:
    return pd.Series(0.0, index=index)


def test_spa_p_value_high_on_known_null(noise_trial_matrix):
    """All-noise trials vs. a zero benchmark: no trial should look better than chance."""
    result = spa_test(
        noise_trial_matrix, _zero_benchmark(noise_trial_matrix.index), n_boot=1000, seed=0
    )
    assert result.p_value_consistent > 0.05


def test_spa_p_value_low_on_known_edge(rng, noise_trial_matrix):
    """One trial has genuine persistent edge; SPA should reject the null."""
    edge = pd.Series(
        rng.normal(0.003, 0.01, len(noise_trial_matrix)), index=noise_trial_matrix.index
    )
    df = noise_trial_matrix.copy()
    df["edge_trial"] = edge
    result = spa_test(df, _zero_benchmark(df.index), n_boot=1000, seed=0)
    assert result.p_value_consistent < 0.1
    assert result.best_trial == "edge_trial"


def test_spa_more_powerful_than_rc_on_known_edge(rng, noise_trial_matrix):
    """Reproduces the paper's headline claim: SPA (consistent) rejects at least
    as easily as White's Reality Check on the same known-edge fixture."""
    edge = pd.Series(
        rng.normal(0.003, 0.01, len(noise_trial_matrix)), index=noise_trial_matrix.index
    )
    df = noise_trial_matrix.copy()
    df["edge_trial"] = edge
    result = spa_test(df, _zero_benchmark(df.index), n_boot=2000, seed=0)
    assert result.p_value_consistent <= result.rc_p_value + 1e-9


def test_spa_p_values_ordered_liberal_le_consistent_le_upper(noise_trial_matrix):
    result = spa_test(
        noise_trial_matrix, _zero_benchmark(noise_trial_matrix.index), n_boot=1000, seed=0
    )
    assert result.p_value_liberal <= result.p_value_consistent + 1e-9
    assert result.p_value_consistent <= result.p_value_upper + 1e-9


def test_spa_rejects_mismatched_index(noise_trial_matrix):
    bad_benchmark = pd.Series(0.0, index=pd.RangeIndex(len(noise_trial_matrix)))
    with pytest.raises(ValueError):
        spa_test(noise_trial_matrix, bad_benchmark)


def test_spa_rejects_too_few_obs():
    idx = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    df = pd.DataFrame(np.random.default_rng(0).normal(0, 0.01, size=(5, 3)), index=idx)
    with pytest.raises(ValueError):
        spa_test(df, pd.Series(0.0, index=idx))


def test_format_spa_table_contains_values(noise_trial_matrix):
    result = spa_test(
        noise_trial_matrix, _zero_benchmark(noise_trial_matrix.index), n_boot=1000, seed=0
    )
    table = format_spa_table(result, label="test")
    assert "test" in table
    assert result.best_trial in table
