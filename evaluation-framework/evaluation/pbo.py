"""Probability of Backtest Overfitting via Combinatorially Symmetric
Cross-Validation (CSCV).

Literature: Bailey, Borwein, López de Prado & Zhu 2017, *The Probability of
Backtest Overfitting* (`../literature/strategy-evaluation/foundational/probability-of-backtest-overfitting.pdf`).
Companion diagnostics (performance degradation, probability of loss,
stochastic dominance) are named in the same paper. Chauhan 2026 (SSRN
6861958) motivates reporting PBO alongside DSR rather than using DSR's
kurtosis-sensitive carve-out (`dsr.py`) — PBO does not depend on the
Gaussian-plus-Cornish-Fisher approximation DSR uses, so it degrades
differently under fat tails.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd


def _default_metric(returns: pd.Series) -> float:
    """Annualisation-agnostic Sharpe proxy: mean/std of the given returns."""
    if len(returns) < 2 or returns.std() == 0:
        return float("-inf")
    return float(returns.mean() / returns.std())


@dataclass(frozen=True)
class PBOResult:
    pbo: float
    n_combinations: int
    logits: list[float]
    degradation_slope: float
    probability_of_loss: float
    dominance: float  # fraction of OOS draws where optimized < non-optimized


def cscv_pbo(
    trial_returns: pd.DataFrame,
    n_splits: int = 16,
    metric: Callable[[pd.Series], float] = _default_metric,
    allow_large: bool = False,
) -> PBOResult:
    """Combinatorially symmetric cross-validation PBO.

    `trial_returns`: (T periods x N trials) DataFrame, one column per trial.
    `n_splits`: number of contiguous time blocks S (must be even). Every way
    of choosing S/2 blocks as the in-sample (IS) half is enumerated;
    C(16, 8) = 12,870 by default. Raises above C(20, 10) = 184,756 unless
    `allow_large=True`, since cost grows combinatorially.
    """
    if n_splits % 2 != 0:
        raise ValueError(f"n_splits={n_splits} must be even")
    if n_splits > 20 and not allow_large:
        raise ValueError(
            f"n_splits={n_splits} implies C({n_splits},{n_splits // 2}) combinations; "
            "pass allow_large=True to proceed above n_splits=20"
        )

    n_trials = trial_returns.shape[1]
    n_obs = trial_returns.shape[0]
    if n_trials < 2:
        raise ValueError("cscv_pbo needs at least 2 trials")
    if n_obs < 2 * n_splits:
        raise ValueError(f"n_obs={n_obs} too small for n_splits={n_splits}")

    block_bounds = np.linspace(0, n_obs, n_splits + 1).astype(int)
    blocks = [trial_returns.iloc[block_bounds[i] : block_bounds[i + 1]] for i in range(n_splits)]
    block_idx = list(range(n_splits))
    half = n_splits // 2

    logits: list[float] = []
    is_metrics_for_regression: list[float] = []
    oos_metrics_for_regression: list[float] = []
    below_zero_oos = 0
    total_oos_draws = 0

    for is_blocks in combinations(block_idx, half):
        oos_blocks = [b for b in block_idx if b not in is_blocks]
        is_returns = pd.concat([blocks[b] for b in is_blocks])
        oos_returns = pd.concat([blocks[b] for b in oos_blocks])

        is_scores = is_returns.apply(metric, axis=0)
        oos_scores = oos_returns.apply(metric, axis=0)

        best_trial = is_scores.idxmax()
        best_is_score = is_scores[best_trial]
        best_oos_score = oos_scores[best_trial]

        rank = int((oos_scores <= best_oos_score).sum())  # 1..N
        omega = rank / (n_trials + 1)
        omega = min(max(omega, 1e-6), 1 - 1e-6)
        logit = math.log(omega / (1 - omega))
        logits.append(logit)

        is_metrics_for_regression.append(best_is_score)
        oos_metrics_for_regression.append(best_oos_score)

        below_zero_oos += int((oos_scores < 0).sum())
        total_oos_draws += len(oos_scores)

    pbo = float(np.mean([lam <= 0 for lam in logits]))

    x = np.array(is_metrics_for_regression)
    y = np.array(oos_metrics_for_regression)
    if x.std() > 0:
        slope = float(np.polyfit(x, y, 1)[0])
    else:
        slope = float("nan")

    prob_loss = below_zero_oos / total_oos_draws if total_oos_draws else float("nan")

    non_optimized_oos = []
    optimized_oos = oos_metrics_for_regression
    for is_blocks in combinations(block_idx, half):
        oos_blocks = [b for b in block_idx if b not in is_blocks]
        oos_returns = pd.concat([blocks[b] for b in oos_blocks])
        oos_scores = oos_returns.apply(metric, axis=0)
        non_optimized_oos.extend(oos_scores.tolist())
    dominance = float(np.mean([opt < np.median(non_optimized_oos) for opt in optimized_oos]))

    return PBOResult(
        pbo=pbo,
        n_combinations=len(logits),
        logits=logits,
        degradation_slope=slope,
        probability_of_loss=prob_loss,
        dominance=dominance,
    )


def format_pbo_table(result: PBOResult, label: str = "") -> str:
    title = f" — {label}" if label else ""
    return (
        f"### PBO (CSCV){title}\n\n"
        f"| Metric | Value | Reading |\n"
        f"|---|---:|---|\n"
        f"| PBO | {result.pbo:.3f} | fraction of splits where IS-best is below-median OOS |\n"
        f"| N combinations | {result.n_combinations} | C(S, S/2) evaluated |\n"
        f"| Degradation slope | {result.degradation_slope:.3f} | OLS(OOS ~ IS); 1.0 = no overfitting |\n"
        f"| P(loss) | {result.probability_of_loss:.3f} | P(OOS metric < 0) |\n"
        f"| Dominance | {result.dominance:.3f} | P(optimized OOS < median non-optimized OOS) |\n"
    )
