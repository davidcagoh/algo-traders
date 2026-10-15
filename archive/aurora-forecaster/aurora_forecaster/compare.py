"""Paired comparison between two forecast loss series (e.g. per-origin CRPS
for unimodal vs. multimodal), so "does text help?" is answered by a
significance test rather than eyeballing a mean difference.

Literature: Diebold & Mariano 1995, *Comparing Predictive Accuracy*; Newey &
West 1994, *Automatic Lag Selection in Covariance Matrix Estimation*. The
long-run variance of d_t = loss_a_t - loss_b_t is estimated with a
Bartlett/Newey-West kernel rather than the plain sample variance, since
h-step-ahead forecasts with overlapping origins induce an MA(h-1) serial
correlation structure under the null (Harvey, Leybourne & Newbold 1997) that
the plain estimator ignores, understating Var(d_bar) and inflating false
"significant" findings.
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
    max_lag: int


def _long_run_variance(d: Sequence[float], d_bar: float, max_lag: int) -> float:
    """Bartlett-kernel-weighted long-run variance of d_t (Newey & West 1994)."""
    n = len(d)
    dc = [x - d_bar for x in d]
    gamma_0 = sum(x * x for x in dc) / n
    total = gamma_0
    for i in range(1, max_lag + 1):
        gamma_i = sum(dc[t] * dc[t - i] for t in range(i, n)) / n
        weight = 1 - i / (max_lag + 1)
        total += 2 * weight * gamma_i
    return max(total, 1e-12)


def diebold_mariano(
    loss_a: Sequence[float],
    loss_b: Sequence[float],
    max_lag: int | None = None,
) -> DieboldMarianoResult:
    """Two-sided DM test on d_t = loss_a_t - loss_b_t.

    Negative statistic (with small p-value) means `loss_a` is significantly
    lower (better) than `loss_b`.

    `max_lag` sets the Bartlett-kernel truncation lag for the long-run
    variance estimate. If given explicitly, it's clipped to `[0, n-1]` — a
    caller with `h`-step-ahead overlapping origins should pass `max_lag =
    h - 1` (this function itself stays horizon-agnostic). If `None`, the
    Newey-West (1994) automatic bandwidth plug-in `floor(4*(n/100)**(2/9))`
    is used instead, also clipped to `[0, n-1]` — this never silently falls
    back to a non-robust plain estimator.
    """
    if len(loss_a) != len(loss_b):
        raise ValueError(
            f"loss_a and loss_b must have equal length, got {len(loss_a)} and {len(loss_b)}"
        )
    n = len(loss_a)
    if n < 2:
        raise ValueError(f"need at least 2 paired observations, got {n}")
    if max_lag is not None and max_lag < 0:
        raise ValueError(f"max_lag must be >= 0, got {max_lag}")

    if max_lag is None:
        lag = math.floor(4 * (n / 100) ** (2 / 9))
    else:
        lag = max_lag
    lag = min(lag, n - 1)

    d = [a - b for a, b in zip(loss_a, loss_b)]
    d_bar = sum(d) / n

    omega2 = _long_run_variance(d, d_bar, lag)
    variance = omega2 / n
    statistic = d_bar / math.sqrt(variance)

    p_value = 2 * (1 - _std_normal_cdf(abs(statistic)))
    return DieboldMarianoResult(statistic=statistic, p_value=p_value, n_obs=n, max_lag=lag)
