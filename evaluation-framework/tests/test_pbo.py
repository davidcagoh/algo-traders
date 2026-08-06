from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from evaluation.pbo import cscv_pbo, format_pbo_table


def test_pbo_near_half_on_known_null(noise_trial_matrix):
    """All-noise trials: PBO should be near 0.5 — no genuine edge to overfit to."""
    result = cscv_pbo(noise_trial_matrix, n_splits=8)
    assert 0.3 <= result.pbo <= 0.7


def test_pbo_low_on_known_edge(rng, noise_trial_matrix):
    """One trial has genuine persistent edge; PBO should be well below the null."""
    edge = pd.Series(
        rng.normal(0.003, 0.01, len(noise_trial_matrix)), index=noise_trial_matrix.index
    )
    df = noise_trial_matrix.copy()
    df["edge_trial"] = edge
    result = cscv_pbo(df, n_splits=8)
    assert result.pbo < 0.3


def test_pbo_rejects_odd_n_splits(noise_trial_matrix):
    with pytest.raises(ValueError):
        cscv_pbo(noise_trial_matrix, n_splits=7)


def test_pbo_rejects_large_n_splits_without_flag(noise_trial_matrix):
    with pytest.raises(ValueError):
        cscv_pbo(noise_trial_matrix, n_splits=22)


def test_pbo_rejects_single_trial(noise_trial_matrix):
    with pytest.raises(ValueError):
        cscv_pbo(noise_trial_matrix.iloc[:, :1], n_splits=8)


def test_pbo_rejects_too_few_obs():
    df = pd.DataFrame(np.random.default_rng(0).normal(0, 0.01, size=(10, 3)))
    with pytest.raises(ValueError):
        cscv_pbo(df, n_splits=8)


def test_pbo_result_shape(noise_trial_matrix):
    result = cscv_pbo(noise_trial_matrix, n_splits=8)
    from math import comb

    assert result.n_combinations == comb(8, 4)
    assert len(result.logits) == result.n_combinations
    assert 0.0 <= result.probability_of_loss <= 1.0


def test_format_pbo_table_contains_pbo_value(noise_trial_matrix):
    result = cscv_pbo(noise_trial_matrix, n_splits=8)
    table = format_pbo_table(result, label="test")
    assert "test" in table
    assert f"{result.pbo:.3f}" in table
