"""Purged, embargoed cross-validation and walk-forward splits.

Literature: Mroziewicz & Ślepaczuk 2026, *Double Out-of-Sample Data and
Walk-Forward Techniques* (`../literature/strategy-evaluation/methods/2602.10785-double-oos-walk-forward.pdf`)
— treats train/test window lengths as selected hyperparameters, so a second,
untouched final test is required beyond the usual walk-forward OOS. Bieganowski
& Ślepaczuk 2026 (`../literature/strategy-evaluation/empirical-audits/2602.00776-explainable-crypto-microstructure.pdf`)
— purged walk-forward evaluation on crypto microstructure. Jadouli 2026
(`../literature/strategy-evaluation/empirical-audits/2607.19453-negative-results-evidence-audit.pdf`)
— audited failure modes are reused dates, unpurged outcome horizons, and
same-close execution; purge+embargo is the mechanical fix. Deep, Deep &
Lamptey 2025 (`../literature/strategy-evaluation/methods/2512.12924-rigorous-walk-forward-validation.pdf`)
— sequential folds and information-set discipline.

"Purge" removes training observations whose label/outcome horizon overlaps
the test window (their label uses information from inside the test period).
"Embargo" additionally removes a span *after* the test window, since a
model touched right before a regime shift can still leak information about
it through serial correlation in features. See `combinatorial_purged_splits`
for the CPCV variant `evaluation.pbo.cscv_pbo` should be fed from, once a
project needs real trial return series that respect a label horizon.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FoldSpec:
    fold_id: int
    train_idx: np.ndarray
    test_idx: np.ndarray


def _purge_and_embargo(
    train_idx: np.ndarray,
    test_start: int,
    test_end: int,
    n: int,
    label_horizon: int,
    embargo: int,
) -> np.ndarray:
    """Remove training indices whose label horizon overlaps [test_start,
    test_end), plus `embargo` indices immediately after test_end."""
    purge_lo = max(0, test_start - label_horizon)
    embargo_hi = min(n, test_end + embargo)
    mask = ~((train_idx >= purge_lo) & (train_idx < embargo_hi))
    return train_idx[mask]


class PurgedKFold:
    """K-fold CV with purging (by label horizon) and embargo.

    sklearn-`split()`-compatible: yields (train_idx, test_idx) index arrays
    into a length-n sequence, in order.
    """

    def __init__(self, n_splits: int, embargo_pct: float = 0.0, label_horizon: int = 0):
        if n_splits < 2:
            raise ValueError("n_splits must be >= 2")
        self.n_splits = n_splits
        self.embargo_pct = embargo_pct
        self.label_horizon = label_horizon

    def split(
        self, x: pd.DataFrame | pd.Series | np.ndarray
    ) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        n = len(x)
        embargo = round(n * self.embargo_pct)
        fold_bounds = np.linspace(0, n, self.n_splits + 1).astype(int)
        all_idx = np.arange(n)
        for i in range(self.n_splits):
            test_start, test_end = fold_bounds[i], fold_bounds[i + 1]
            test_idx = all_idx[test_start:test_end]
            train_idx = np.concatenate([all_idx[:test_start], all_idx[test_end:]])
            train_idx = _purge_and_embargo(
                train_idx, test_start, test_end, n, self.label_horizon, embargo
            )
            yield train_idx, test_idx


class PurgedWalkForward:
    """Anchored or rolling walk-forward with purge + embargo.

    `anchored=True`: training window always starts at 0 and grows.
    `anchored=False`: training window is a fixed-length rolling `train_span`.
    """

    def __init__(
        self,
        train_span: int,
        test_span: int,
        step: int | None = None,
        embargo: int = 0,
        label_horizon: int = 0,
        anchored: bool = False,
    ):
        if train_span <= 0 or test_span <= 0:
            raise ValueError("train_span and test_span must be positive")
        self.train_span = train_span
        self.test_span = test_span
        self.step = step or test_span
        self.embargo = embargo
        self.label_horizon = label_horizon
        self.anchored = anchored

    def split(self, x: pd.DataFrame | pd.Series | np.ndarray) -> Iterator[FoldSpec]:
        n = len(x)
        all_idx = np.arange(n)
        test_starts = range(self.train_span, n - self.test_span + 1, self.step)
        for fold_id, test_start in enumerate(test_starts):
            test_end = test_start + self.test_span
            train_start = 0 if self.anchored else max(0, test_start - self.train_span)
            train_idx = all_idx[train_start:test_start]
            train_idx = _purge_and_embargo(
                train_idx, test_start, test_end, n, self.label_horizon, self.embargo
            )
            test_idx = all_idx[test_start:test_end]
            yield FoldSpec(fold_id=fold_id, train_idx=train_idx, test_idx=test_idx)


@dataclass(frozen=True)
class DoubleOOSSplit:
    """Three-way split: dev (window-length selection) -> oos1 (model
    selection) -> final (touched exactly once).

    All boundaries are integer positions into a length-n sequence, given as
    fractions of n via `dev_end`, `oos1_end` (both in (0, 1)); `final` is
    everything after `oos1_end`.
    """

    dev_end: float
    oos1_end: float

    def __post_init__(self) -> None:
        if not (0 < self.dev_end < self.oos1_end < 1):
            raise ValueError("require 0 < dev_end < oos1_end < 1")

    def indices(self, n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        all_idx = np.arange(n)
        dev_end_i = round(n * self.dev_end)
        oos1_end_i = round(n * self.oos1_end)
        return all_idx[:dev_end_i], all_idx[dev_end_i:oos1_end_i], all_idx[oos1_end_i:]


def combinatorial_purged_splits(
    n: int, n_splits: int, label_horizon: int = 0, embargo: int = 0
) -> Iterator[FoldSpec]:
    """CPCV: every way of choosing n_splits/2 contiguous blocks as the test
    set, purged/embargoed against the remaining training blocks. Feeds
    `evaluation.pbo.cscv_pbo` with splits that respect a label horizon,
    rather than raw block boundaries.
    """
    if n_splits % 2 != 0:
        raise ValueError("n_splits must be even")
    bounds = np.linspace(0, n, n_splits + 1).astype(int)
    blocks = [np.arange(bounds[i], bounds[i + 1]) for i in range(n_splits)]
    half = n_splits // 2
    for fold_id, test_blocks in enumerate(combinations(range(n_splits), half)):
        test_idx = np.concatenate([blocks[b] for b in test_blocks])
        train_blocks = [b for b in range(n_splits) if b not in test_blocks]
        train_idx = (
            np.concatenate([blocks[b] for b in train_blocks])
            if train_blocks
            else np.array([], dtype=int)
        )
        test_start, test_end = int(test_idx.min()), int(test_idx.max()) + 1
        train_idx = _purge_and_embargo(train_idx, test_start, test_end, n, label_horizon, embargo)
        yield FoldSpec(fold_id=fold_id, train_idx=train_idx, test_idx=test_idx)
