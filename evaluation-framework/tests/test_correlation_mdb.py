from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from evaluation.correlation_mdb import (
    correlation_matrix,
    marginal_diversification_benefit,
    mdb_robust_flag,
    mdb_table,
    returns_matrix,
)


@pytest.fixture
def wallets(gaussian_wallet, trending_wallet, fat_tailed_wallet):
    return {"a": gaussian_wallet, "b": trending_wallet, "c": fat_tailed_wallet}


@pytest.fixture
def rmatrix(wallets):
    return returns_matrix(wallets)


def test_returns_matrix_shape(rmatrix, wallets):
    assert set(rmatrix.columns) == set(wallets.keys())
    assert not rmatrix.isna().any().any()


def test_correlation_matrix_diagonal_is_one(rmatrix):
    corr = correlation_matrix(rmatrix)
    assert np.allclose(np.diag(corr.values), 1.0)


def test_mdb_candidate_already_in_book_is_zero(rmatrix):
    assert marginal_diversification_benefit(rmatrix, ["a"], "a", scheme="eq") == 0.0


def test_mdb_unknown_scheme_raises(rmatrix):
    with pytest.raises(ValueError):
        marginal_diversification_benefit(rmatrix, ["a"], "b", scheme="bogus")


def test_mdb_robust_flag_matches_all_three_schemes(rmatrix):
    flag = mdb_robust_flag(rmatrix, ["a"], "b")
    manual = all(
        marginal_diversification_benefit(rmatrix, ["a"], "b", scheme=s) > 0
        for s in ("eq", "rp", "mv")
    )
    assert flag == manual


def test_mdb_table_shape(rmatrix):
    table = mdb_table(rmatrix, book=["a"], candidates=["b", "c"])
    assert list(table.index) == ["b", "c"]
    assert set(table.columns) == {"MDB_eq", "MDB_rp", "MDB_mv", "robust"}


def test_mean_variance_weights_falls_back_below_30_obs():
    from evaluation.correlation_mdb import _mean_variance_weights

    idx = pd.date_range("2024-01-01", periods=10, freq="D")
    r = pd.DataFrame(
        {
            "a": np.random.default_rng(1).normal(0, 0.01, 10),
            "b": np.random.default_rng(2).normal(0, 0.01, 10),
        },
        index=idx,
    )
    w = _mean_variance_weights(r, ["a", "b"])
    assert w == {"a": 0.5, "b": 0.5}
