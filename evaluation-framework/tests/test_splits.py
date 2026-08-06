from __future__ import annotations

import pandas as pd
import pytest

from evaluation.splits import (
    DoubleOOSSplit,
    PurgedKFold,
    PurgedWalkForward,
    combinatorial_purged_splits,
)


def test_purged_kfold_no_train_test_intersection():
    x = pd.Series(range(200))
    cv = PurgedKFold(n_splits=5, embargo_pct=0.02, label_horizon=3)
    for train_idx, test_idx in cv.split(x):
        assert set(train_idx).isdisjoint(set(test_idx))


def test_purged_kfold_purges_label_horizon_around_test():
    x = pd.Series(range(100))
    cv = PurgedKFold(n_splits=4, label_horizon=5, embargo_pct=0.0)
    folds = list(cv.split(x))
    train_idx, test_idx = folds[1]
    test_start = test_idx.min()
    # training indices within label_horizon before test_start must be purged
    near_boundary = [i for i in range(max(0, test_start - 5), test_start)]
    assert not any(i in train_idx for i in near_boundary)


def test_purged_kfold_rejects_single_split():
    with pytest.raises(ValueError):
        PurgedKFold(n_splits=1)


def test_purged_walk_forward_rolling_train_span_fixed():
    x = pd.Series(range(300))
    wf = PurgedWalkForward(train_span=50, test_span=20, anchored=False)
    folds = list(wf.split(x))
    assert len(folds) > 0
    for fold in folds:
        assert set(fold.train_idx).isdisjoint(set(fold.test_idx))
        assert len(fold.train_idx) <= 50


def test_purged_walk_forward_anchored_grows():
    x = pd.Series(range(300))
    wf = PurgedWalkForward(train_span=50, test_span=20, anchored=True)
    folds = list(wf.split(x))
    sizes = [len(f.train_idx) for f in folds]
    assert sizes == sorted(sizes)  # non-decreasing


def test_purged_walk_forward_rejects_nonpositive_spans():
    with pytest.raises(ValueError):
        PurgedWalkForward(train_span=0, test_span=10)


def test_double_oos_split_ordering_and_no_overlap():
    split = DoubleOOSSplit(dev_end=0.5, oos1_end=0.8)
    dev, oos1, final = split.indices(1000)
    assert dev.max() < oos1.min()
    assert oos1.max() < final.min()
    assert len(dev) + len(oos1) + len(final) == 1000


def test_double_oos_split_rejects_bad_bounds():
    with pytest.raises(ValueError):
        DoubleOOSSplit(dev_end=0.8, oos1_end=0.5)
    with pytest.raises(ValueError):
        DoubleOOSSplit(dev_end=0.0, oos1_end=0.5)


def test_double_oos_split_final_never_in_dev_or_oos1_across_many_sizes():
    split = DoubleOOSSplit(dev_end=0.6, oos1_end=0.85)
    for n in (100, 537, 1000):
        dev, oos1, final = split.indices(n)
        combined_early = set(dev) | set(oos1)
        assert combined_early.isdisjoint(set(final))


def test_combinatorial_purged_splits_rejects_odd_n_splits():
    with pytest.raises(ValueError):
        list(combinatorial_purged_splits(n=100, n_splits=5))


def test_combinatorial_purged_splits_train_test_disjoint():
    for fold in combinatorial_purged_splits(n=200, n_splits=6, label_horizon=2, embargo=2):
        assert set(fold.train_idx).isdisjoint(set(fold.test_idx))


def test_combinatorial_purged_splits_count_matches_binomial():
    from math import comb

    folds = list(combinatorial_purged_splits(n=200, n_splits=6))
    assert len(folds) == comb(6, 3)


def test_leakage_injection_purge_removes_lookahead_training_rows():
    """A training row whose label depends on values inside the test window
    (label_horizon steps ahead) is exactly what purge must exclude. Without
    purge those boundary rows remain in train_idx; with purge they don't."""
    y = pd.Series(range(500))
    label_horizon = 10

    cv_no_purge = PurgedKFold(n_splits=5, label_horizon=0, embargo_pct=0.0)
    cv_purged = PurgedKFold(n_splits=5, label_horizon=label_horizon, embargo_pct=0.0)

    train_idx_no_purge, test_idx = next(iter(cv_no_purge.split(y)))
    train_idx_purged, _ = next(iter(cv_purged.split(y)))

    test_start = int(test_idx.min())
    boundary_rows = set(range(max(0, test_start - label_horizon), test_start))

    assert boundary_rows.issubset(set(train_idx_no_purge))
    assert boundary_rows.isdisjoint(set(train_idx_purged))
