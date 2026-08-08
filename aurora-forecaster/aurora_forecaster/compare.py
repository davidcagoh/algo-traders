"""Paired comparison between two forecast loss series (e.g. per-origin CRPS
for unimodal vs. multimodal), so "does text help?" is answered by a
significance test rather than eyeballing a mean difference.

Literature: Diebold & Mariano 1995, *Comparing Predictive Accuracy*. This is
the plain (non-HAC) form — no autocorrelation-robust variance estimator —
since origin counts here are currently small (see README's rolling-forecast
status); revisit if origins overlap in time (overlapping horizons induce
serial correlation the plain form doesn't account for).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from aurora_forecaster.scoring import _std_normal_cdf


@dataclass(frozen=True)
class DieboldMarianoResult:
    statistic: float
    p_value: float
    n_obs: int


def diebold_mariano(loss_a: Sequence[float], loss_b: Sequence[float]) -> DieboldMarianoResult:
    """Two-sided DM test on d_t = loss_a_t - loss_b_t.

    Negative statistic (with small p-value) means `loss_a` is significantly
    lower (better) than `loss_b`.
    """
    if len(loss_a) != len(loss_b):
        raise ValueError(
            f"loss_a and loss_b must have equal length, got {len(loss_a)} and {len(loss_b)}"
        )
    n = len(loss_a)
    if n < 2:
        raise ValueError(f"need at least 2 paired observations, got {n}")

    d = [a - b for a, b in zip(loss_a, loss_b)]
    d_bar = sum(d) / n

    if n == 1:
        variance = 0.0
    else:
        variance = sum((x - d_bar) ** 2 for x in d) / (n - 1)

    if variance == 0:
        statistic = 0.0
    else:
        statistic = d_bar / math.sqrt(variance / n)

    p_value = 2 * (1 - _std_normal_cdf(abs(statistic)))
    return DieboldMarianoResult(statistic=statistic, p_value=p_value, n_obs=n)
