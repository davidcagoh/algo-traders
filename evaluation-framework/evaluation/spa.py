"""Test for Superior Predictive Ability (SPA) and White's Reality Check (RC).

Literature: White 2000, *A Reality Check for Data Snooping*
(`../literature/strategy-evaluation/foundational/white-reality-check-data-snooping.pdf`);
Hansen 2005, *A Test for Superior Predictive Ability*
(`../literature/strategy-evaluation/foundational/hansen-test-superior-predictive-ability.pdf`).
Both test H0: no trial in a searched set beats a benchmark, using a
stationary-bootstrap null distribution of the best trial's performance.
Hansen's SPA test studentizes the per-trial statistic and uses a
data-dependent null (one of three recentering choices, `l`/`c`/`u`) instead
of White's original, unstudentized, always-LFC-centered RC; the paper's own
Monte Carlo and empirical results (Hansen Tables 2-4, 6) show SPA is
uniformly at least as powerful, so `spa_test()` is the primary entry point
here and `SPAResult.rc_p_value` carries the RC comparison for free (it
reuses the same bootstrap resamples).

Reuses `bootstrap.py::stationary_bootstrap_indices` for resampling rather
than reimplementing the Politis-Romano scheme.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from evaluation.bootstrap import optimal_block_length, stationary_bootstrap_indices


def _default_loss(returns: pd.Series) -> pd.Series:
    """Identity loss: compare mean returns directly (higher is better)."""
    return returns


def _long_run_variance(d: np.ndarray, block_len: float, max_lag: int | None = None) -> float:
    """Politis-Romano kernel-weighted long-run variance (Hansen 2005, p.372).

    omega^2 = gamma_0 + 2 * sum_{i=1}^{L} kappa(n, i) * gamma_i, with
    kappa(n, i) = (n-i)/n * (1-q)^i + i/n * (1-q)^(n-i), q = 1/block_len.
    The paper sums to n-1; truncated at `max_lag` here since kappa decays
    geometrically in q and an untruncated O(n^2) sum is wasted work.
    """
    n = len(d)
    if n < 2:
        return 0.0
    d_centered = d - d.mean()
    gamma_0 = float(np.mean(d_centered**2))
    q = 1.0 / max(block_len, 1.0)
    lag_cap = max_lag if max_lag is not None else min(n - 1, max(4 * math.ceil(block_len), 10))
    lag_cap = min(lag_cap, n - 1)

    total = gamma_0
    for i in range(1, lag_cap + 1):
        gamma_i = float(np.mean(d_centered[: n - i] * d_centered[i:]))
        kappa = (n - i) / n * (1 - q) ** i + i / n * (1 - q) ** (n - i)
        total += 2 * kappa * gamma_i
    return max(total, 1e-12)


@dataclass(frozen=True)
class SPAResult:
    p_value_liberal: float
    p_value_consistent: float
    p_value_upper: float
    rc_p_value: float
    t_stat_spa: float
    t_stat_rc: float
    best_trial: str
    n_trials: int
    n_obs: int
    n_boot: int
    block_len: int


def spa_test(
    trial_returns: pd.DataFrame,
    benchmark: pd.Series,
    loss: Callable[[pd.Series], pd.Series] = _default_loss,
    n_boot: int = 10_000,
    block_len: int | None = None,
    seed: int | None = None,
) -> SPAResult:
    """Hansen's SPA test (+ White's RC for comparison) against a benchmark.

    `trial_returns`: (T periods x N trials) DataFrame, one column per trial,
    same shape convention as `pbo.py::cscv_pbo`. `benchmark`: length-T
    series aligned to `trial_returns.index`. `loss` maps a return series to
    the quantity being compared (default: identity, i.e. compare mean
    returns directly, matching this project's Sharpe-style metrics).

    Returns three SPA p-values (liberal/consistent/upper recentering, per
    Hansen S2.4) with p_liberal <= p_consistent <= p_upper by construction,
    plus `rc_p_value` for White's original unstudentized test computed from
    the same bootstrap resamples.
    """
    if not trial_returns.index.equals(benchmark.index):
        raise ValueError("trial_returns and benchmark must share the same index")
    if trial_returns.shape[1] < 1:
        raise ValueError("spa_test needs at least 1 trial")

    n = trial_returns.shape[0]
    if n < 10:
        raise ValueError(f"n_obs={n} too small for SPA's asymptotic null")

    trial_loss = trial_returns.apply(loss, axis=0)
    benchmark_loss = loss(benchmark)
    d = trial_loss.sub(benchmark_loss, axis=0)  # d_{k,t}: positive = trial beats benchmark
    d_bar = d.mean(axis=0).to_numpy()  # (K,)
    trials = list(d.columns)
    k = len(trials)

    bl = block_len or optimal_block_length(benchmark)
    omega = np.array([math.sqrt(_long_run_variance(d[c].to_numpy(), bl)) for c in trials])

    sqrt_n = math.sqrt(n)
    studentized = sqrt_n * d_bar / omega
    t_spa = max(0.0, float(np.max(studentized)))
    t_rc = max(0.0, float(sqrt_n * np.max(d_bar)))
    best_trial = trials[int(np.argmax(studentized))]

    rng = np.random.default_rng(seed)
    idx = stationary_bootstrap_indices(n, n_boot, bl, rng)  # (n_boot, n)

    d_np = d.to_numpy()  # (n, K)
    # d_star_mean[b, k] = mean_t d_np[idx[b, t], k]
    d_star_mean = d_np[idx].mean(axis=1)  # (n_boot, K)

    g_liberal = np.maximum(d_bar, 0.0)
    g_upper = d_bar
    if n > 15:
        threshold = -np.sqrt((omega**2 / n) * 2 * math.log(math.log(n)))
        g_consistent = np.where(d_bar >= threshold, d_bar, 0.0)
    else:
        g_consistent = g_upper.copy()

    def _bootstrap_p(recenter: np.ndarray, studentize: bool, observed: float) -> float:
        z_bar = d_star_mean - recenter  # (n_boot, K)
        stat = sqrt_n * z_bar / omega if studentize else sqrt_n * z_bar
        t_star = np.maximum(0.0, stat.max(axis=1))  # (n_boot,)
        return float(np.mean(t_star > observed))

    p_liberal = _bootstrap_p(g_liberal, True, t_spa)
    p_consistent = _bootstrap_p(g_consistent, True, t_spa)
    p_upper = _bootstrap_p(g_upper, True, t_spa)
    rc_p_value = _bootstrap_p(d_bar, False, t_rc)  # RC: unstudentized, full recentering

    return SPAResult(
        p_value_liberal=p_liberal,
        p_value_consistent=p_consistent,
        p_value_upper=p_upper,
        rc_p_value=rc_p_value,
        t_stat_spa=t_spa,
        t_stat_rc=t_rc,
        best_trial=best_trial,
        n_trials=k,
        n_obs=n,
        n_boot=n_boot,
        block_len=bl,
    )


def format_spa_table(result: SPAResult, label: str = "") -> str:
    title = f" — {label}" if label else ""
    return (
        f"### SPA / Reality Check{title}\n\n"
        f"| Metric | Value | Reading |\n"
        f"|---|---:|---|\n"
        f"| Best trial | {result.best_trial} | highest studentized excess over benchmark |\n"
        f"| SPA p (liberal) | {result.p_value_liberal:.3f} | mu-hat^l recentering, most anti-conservative |\n"
        f"| SPA p (consistent) | {result.p_value_consistent:.3f} | mu-hat^c, Hansen's recommended default |\n"
        f"| SPA p (upper) | {result.p_value_upper:.3f} | mu-hat^u=0, studentized LFC null |\n"
        f"| Reality Check p | {result.rc_p_value:.3f} | White 2000, unstudentized LFC null |\n"
        f"| N trials | {result.n_trials} | |\n"
        f"| N obs | {result.n_obs} | |\n"
    )
