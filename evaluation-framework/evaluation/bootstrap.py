"""Block-bootstrap confidence intervals for dependent (serially correlated)
return series.

Literature: Bysik & Ślepaczuk 2026 (`../literature/strategy-evaluation/methods/2606.00060-cost-aware-walk-forward-bitcoin.pdf`)
use block-bootstrap for strategy comparison under 27-fold walk-forward.
Chauhan 2026 (SSRN 6861958) — dependent bootstraps and HAC inference where
observations share shocks; iid bootstrap understates variance for daily
strategy returns. Oliveira, Guzman & Firoozye 2025
(`../literature/strategy-evaluation/methods/2510.12725-bootstrap-robust-optimization.pdf`)
— select parameters from conservative bootstrap quantiles, not the
in-sample optimum. Politis & Romano 1994 (stationary bootstrap) and
Politis & White 2004 (automatic block-length selection) are the underlying
methods; not separately mirrored in the literature corpus.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd


def optimal_block_length(returns: pd.Series, max_lag: int = 50) -> int:
    """Heuristic automatic block length (Politis-White style).

    Uses the lag-1 autocorrelation to size the block: near-zero
    autocorrelation -> short blocks; strong dependence -> longer blocks.
    Falls back to `n**(1/3)` when the series is too short or too noisy for
    autocorrelation to be estimated.
    """
    n = len(returns)
    fallback = max(2, round(n ** (1 / 3)))
    if n < 10:
        return fallback
    r = returns.to_numpy()
    r = r - r.mean()
    denom = np.sum(r**2)
    if denom == 0:
        return fallback
    lag1 = np.sum(r[:-1] * r[1:]) / denom
    lag1 = min(max(lag1, -0.99), 0.99)
    if abs(lag1) < 1e-6:
        return fallback
    magnitude = abs(2 * lag1 / (1 - lag1**2))
    b = magnitude ** (2 / 3) * n ** (1 / 3)
    if not math.isfinite(b):
        return fallback
    return int(min(max(round(b), 2), min(max_lag, n // 2 or 1)))


def stationary_bootstrap_indices(
    n: int, n_boot: int, block_len: float, rng: np.random.Generator
) -> np.ndarray:
    """Vectorised Politis-Romano stationary bootstrap index generation.

    Returns an (n_boot, n) int array of resampled indices into a length-n
    series, using geometric block lengths with mean `block_len`. Public so
    that other modules (e.g. `spa.py`, which needs per-trial bootstrap
    resamples of a (T x K) matrix rather than a single series) can reuse
    the same resampling scheme instead of reimplementing it.
    """
    p = 1.0 / max(block_len, 1.0)
    starts = rng.integers(0, n, size=(n_boot, n))
    continue_block = rng.random((n_boot, n)) >= p
    continue_block[:, 0] = False  # always start a new block at position 0

    idx = np.empty((n_boot, n), dtype=np.int64)
    idx[:, 0] = starts[:, 0]
    for t in range(1, n):
        fresh = starts[:, t]
        carried = (idx[:, t - 1] + 1) % n
        idx[:, t] = np.where(continue_block[:, t], carried, fresh)
    return idx


def _moving_block_indices(
    n: int, n_boot: int, block_len: int, rng: np.random.Generator
) -> np.ndarray:
    block_len = max(1, min(block_len, n))
    n_blocks = math.ceil(n / block_len)
    starts = rng.integers(0, n - block_len + 1 if n > block_len else 1, size=(n_boot, n_blocks))
    offsets = np.arange(block_len)
    idx = (starts[:, :, None] + offsets[None, None, :]) % n
    idx = idx.reshape(n_boot, -1)[:, :n]
    return idx


def _circular_block_indices(
    n: int, n_boot: int, block_len: int, rng: np.random.Generator
) -> np.ndarray:
    block_len = max(1, min(block_len, n))
    n_blocks = math.ceil(n / block_len)
    starts = rng.integers(0, n, size=(n_boot, n_blocks))
    offsets = np.arange(block_len)
    idx = (starts[:, :, None] + offsets[None, None, :]) % n
    idx = idx.reshape(n_boot, -1)[:, :n]
    return idx


def moving_block_bootstrap(
    returns: pd.Series, n_boot: int = 10_000, block_len: int | None = None, seed: int | None = None
) -> np.ndarray:
    """Return an (n_boot, n) array of resampled return paths (non-wrapping blocks)."""
    rng = np.random.default_rng(seed)
    n = len(returns)
    bl = block_len or optimal_block_length(returns)
    idx = _moving_block_indices(n, n_boot, bl, rng)
    return returns.to_numpy()[idx]


def circular_block_bootstrap(
    returns: pd.Series, n_boot: int = 10_000, block_len: int | None = None, seed: int | None = None
) -> np.ndarray:
    """Like `moving_block_bootstrap` but blocks wrap around the series end."""
    rng = np.random.default_rng(seed)
    n = len(returns)
    bl = block_len or optimal_block_length(returns)
    idx = _circular_block_indices(n, n_boot, bl, rng)
    return returns.to_numpy()[idx]


def stationary_bootstrap(
    returns: pd.Series,
    n_boot: int = 10_000,
    block_len: float | None = None,
    seed: int | None = None,
) -> np.ndarray:
    """Politis-Romano stationary bootstrap: geometric (random) block lengths."""
    rng = np.random.default_rng(seed)
    n = len(returns)
    bl = block_len or optimal_block_length(returns)
    idx = stationary_bootstrap_indices(n, n_boot, bl, rng)
    return returns.to_numpy()[idx]


_METHODS: dict[str, Callable[..., np.ndarray]] = {
    "moving": moving_block_bootstrap,
    "circular": circular_block_bootstrap,
    "stationary": stationary_bootstrap,
}


@dataclass(frozen=True)
class BootstrapCI:
    point: float
    lower: float
    upper: float
    method: str
    block_len: int
    n_boot: int
    alpha: float


def bootstrap_ci(
    returns: pd.Series,
    statistic: Callable[[np.ndarray], float] = lambda r: (
        float(np.mean(r) / np.std(r)) if np.std(r) > 0 else 0.0
    ),
    n_boot: int = 10_000,
    method: str = "stationary",
    alpha: float = 0.05,
    block_len: int | None = None,
    seed: int | None = None,
) -> BootstrapCI:
    """Percentile block-bootstrap CI for an arbitrary statistic of a return series."""
    if method not in _METHODS:
        raise ValueError(f"unknown bootstrap method: {method!r}")
    bl = block_len or optimal_block_length(returns)
    paths = _METHODS[method](returns, n_boot=n_boot, block_len=bl, seed=seed)
    stats = np.apply_along_axis(statistic, 1, paths)
    stats = stats[np.isfinite(stats)]
    point = float(statistic(returns.to_numpy()))
    lower = float(np.quantile(stats, alpha / 2)) if len(stats) else float("nan")
    upper = float(np.quantile(stats, 1 - alpha / 2)) if len(stats) else float("nan")
    return BootstrapCI(
        point=point,
        lower=lower,
        upper=upper,
        method=method,
        block_len=bl,
        n_boot=n_boot,
        alpha=alpha,
    )


def paired_bootstrap_test(
    returns_a: pd.Series,
    returns_b: pd.Series,
    statistic: Callable[[np.ndarray], float] = lambda r: (
        float(np.mean(r) / np.std(r)) if np.std(r) > 0 else 0.0
    ),
    n_boot: int = 10_000,
    method: str = "stationary",
    seed: int | None = None,
) -> dict[str, float]:
    """Bootstrap test of statistic(a) - statistic(b) using paired (same-index) resampling."""
    if len(returns_a) != len(returns_b):
        raise ValueError("returns_a and returns_b must be the same length (paired)")
    n = len(returns_a)
    rng = np.random.default_rng(seed)
    bl = optimal_block_length(returns_a)
    if method not in _METHODS:
        raise ValueError(f"unknown bootstrap method: {method!r}")
    if method == "stationary":
        idx = stationary_bootstrap_indices(n, n_boot, bl, rng)
    elif method == "moving":
        idx = _moving_block_indices(n, n_boot, bl, rng)
    else:
        idx = _circular_block_indices(n, n_boot, bl, rng)

    a_paths = returns_a.to_numpy()[idx]
    b_paths = returns_b.to_numpy()[idx]
    a_stats = np.apply_along_axis(statistic, 1, a_paths)
    b_stats = np.apply_along_axis(statistic, 1, b_paths)
    diffs = a_stats - b_stats
    diffs = diffs[np.isfinite(diffs)]

    point = float(statistic(returns_a.to_numpy()) - statistic(returns_b.to_numpy()))
    p_value = float(np.mean(diffs <= 0)) if point > 0 else float(np.mean(diffs >= 0))
    return {
        "point_diff": point,
        "ci_lower": float(np.quantile(diffs, 0.025)) if len(diffs) else float("nan"),
        "ci_upper": float(np.quantile(diffs, 0.975)) if len(diffs) else float("nan"),
        "p_value": min(1.0, 2 * p_value),
    }
