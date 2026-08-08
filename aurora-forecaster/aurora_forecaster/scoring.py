"""Distributional forecast scoring, scoped to what `ForecastRecord` stores:
a Gaussian summary (`sample_mean`/`sample_std`) per horizon step, not raw
samples or quantiles. `crps_gaussian` uses the closed-form Gaussian CRPS
(Gneiting & Raftery 2007) rather than an empirical/sample-based estimator —
if a richer output is ever logged, this is the one function that needs a
sibling, not a rewrite of the module.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

_INV_SQRT_2PI = 1.0 / math.sqrt(2 * math.pi)
_INV_SQRT_PI = 1.0 / math.sqrt(math.pi)


def _std_normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


def _std_normal_pdf(x: float) -> float:
    return _INV_SQRT_2PI * math.exp(-0.5 * x * x)


def crps_gaussian(mu: float, sigma: float, y: float) -> float:
    """Closed-form CRPS of N(mu, sigma^2) against realized value y.

    CRPS = sigma * (z*(2*Phi(z) - 1) + 2*phi(z) - 1/sqrt(pi)), z = (y-mu)/sigma.
    """
    if sigma <= 0:
        raise ValueError(f"sigma must be positive, got {sigma}")
    z = (y - mu) / sigma
    return sigma * (z * (2 * _std_normal_cdf(z) - 1) + 2 * _std_normal_pdf(z) - _INV_SQRT_PI)


def mase(errors: Sequence[float], insample_naive_errors: Sequence[float]) -> float:
    """Mean Absolute Scaled Error (Hyndman & Koehler 2006).

    `errors` are the model's absolute forecast errors on the test horizon;
    `insample_naive_errors` are the lookback window's own lag-1 naive
    absolute errors, used as the scale denominator.
    """
    scale = sum(abs(e) for e in insample_naive_errors) / len(insample_naive_errors)
    if scale == 0:
        raise ValueError("naive in-sample scale is zero; cannot compute MASE")
    mean_abs_error = sum(abs(e) for e in errors) / len(errors)
    return mean_abs_error / scale


def skill_score(model_loss: float, naive_loss: float) -> float:
    """1 - model_loss/naive_loss. Positive means the model beats naive."""
    if naive_loss == 0:
        raise ValueError("naive_loss is zero; skill score is undefined")
    return 1.0 - model_loss / naive_loss


def calibration_coverage(
    z_scores: Sequence[float], levels: Sequence[float] = (0.5, 0.8, 0.95)
) -> dict[float, float]:
    """Empirical coverage of standardized residuals `z = (y - mu) / sigma`.

    For each nominal central-interval level p, checks the fraction of
    `z_scores` inside [-z_p, z_p] where z_p = Phi^-1((1+p)/2). A
    well-calibrated model has empirical coverage close to the nominal level.
    """
    n = len(z_scores)
    coverage: dict[float, float] = {}
    for p in levels:
        z_p = math.sqrt(2) * _inv_erf(p)
        inside = sum(1 for z in z_scores if abs(z) <= z_p)
        coverage[p] = inside / n
    return coverage


def _inv_erf(p: float) -> float:
    """Inverse of erf at the point needed for a central level `p`'s z_p.

    Solves erf(x) = p via bisection (no scipy dependency); erf is monotonic
    and smooth on [0, ~6], so bisection converges to float precision in a
    couple dozen iterations.
    """
    lo, hi = 0.0, 6.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if math.erf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
