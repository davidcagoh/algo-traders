"""Layer-4: Deflated Sharpe Ratio (López de Prado 2014).

Cross-venue port of `feishu/eval/dsr.py`. Annualisation is a parameter,
not a hardcoded constant.

DSR formula
-----------

    DSR = Φ( (SR_hat - SR_star) · √(N_obs - 1) /
             √(1 - γ_3·SR_hat + (γ_4 - 1)/4 · SR_hat²) )

with SR_star approximated by López de Prado 2014, Eq. 7:

    SR_star = √V · ((1-γ)·Φ⁻¹(1 - 1/N) + γ·Φ⁻¹(1 - 1/(N·e)))

where V is variance of Sharpes across N trials and γ = 0.5772 (Euler-
Mascheroni). DSR > 0.95 → signal-distinguishable.

Cross-project carve-out (`../wiki/learnings-archive.md`): DSR is binding-
meaningful only when (excess kurt < ~5) AND (N daily obs > ~250). Below
either threshold, demote to humility check. Use `is_dsr_binding()` to
gate-check before reading the DSR value as a pass/fail signal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from evaluation.layers import DEFAULT_ANNUAL, kurt_excess

EULER_GAMMA = 0.5772156649

# Carve-out thresholds from cross-project learnings (2026-05-20).
DSR_BINDING_KURT_MAX = 5.0
DSR_BINDING_N_MIN = 250


@dataclass(frozen=True)
class DSRStats:
    label: str
    sharpe: float
    skew: float
    kurt: float       # non-excess (Pearson) for direct use in the formula
    n_obs: int
    sharpe_star: float
    dsr: float
    verdict: str      # SIGNAL / WEAK / NOISE


def _sharpe_components(
    returns: pd.Series, annualisation: float
) -> tuple[float, float, float, int]:
    """Return (annualised_sharpe, sample_skew, non_excess_kurt, n_obs)."""
    n = len(returns)
    if n < 2 or returns.std() == 0:
        return 0.0, 0.0, 3.0, n
    sh = float(returns.mean() / returns.std() * math.sqrt(annualisation))
    sk = float(stats.skew(returns, bias=False))
    kt = float(stats.kurtosis(returns, bias=False, fisher=False))  # non-excess
    return sh, sk, kt, n


def expected_max_sharpe(sharpe_var: float, n_trials: int) -> float:
    """López de Prado 2014, Eq. 7."""
    n = max(2, n_trials)
    z1 = stats.norm.ppf(1.0 - 1.0 / n)
    z2 = stats.norm.ppf(1.0 - 1.0 / (n * math.e))
    return math.sqrt(max(sharpe_var, 0.0)) * (
        (1.0 - EULER_GAMMA) * z1 + EULER_GAMMA * z2
    )


def deflated_sharpe(
    sharpe: float,
    sharpe_star: float,
    skew: float,
    kurt: float,
    n_obs: int,
) -> float:
    """López de Prado 2014, Eq. 9. Returns DSR in [0, 1]."""
    if n_obs < 3:
        return 0.0
    denom_sq = 1.0 - skew * sharpe + ((kurt - 1.0) / 4.0) * sharpe**2
    denom = math.sqrt(max(1e-9, denom_sq))
    z = (sharpe - sharpe_star) * math.sqrt(n_obs - 1) / denom
    return float(stats.norm.cdf(z))


def is_dsr_binding(returns: pd.Series) -> tuple[bool, str]:
    """Apply the cross-project carve-out.

    Returns (binding, reason). When False, the DSR value is reported as a
    humility check rather than a pass/fail gate.
    """
    n = len(returns)
    ek = kurt_excess(returns)
    if n <= DSR_BINDING_N_MIN:
        return False, f"N={n} <= {DSR_BINDING_N_MIN} (insufficient daily obs)"
    if ek >= DSR_BINDING_KURT_MAX:
        return False, f"excess kurt={ek:.2f} >= {DSR_BINDING_KURT_MAX} (fat-tailed)"
    return True, f"N={n}, excess kurt={ek:.2f} (binding)"


def _verdict(dsr: float) -> str:
    if dsr > 0.95:
        return "SIGNAL"
    if dsr > 0.5:
        return "WEAK"
    return "NOISE"


def compute_dsr_table(
    wallets: dict[str, pd.Series],
    annualisation: float = DEFAULT_ANNUAL,
) -> list[DSRStats]:
    """Compute DSR for each (label → wallet curve) entry in `wallets`.

    SR_star uses the variance of Sharpes across the candidates passed in.
    Pass the real candidate set, not just the survivors, or the deflation
    is too weak.
    """
    components: list[tuple[str, float, float, float, int]] = []
    for label, wallet in wallets.items():
        if wallet is None or len(wallet) < 3:
            continue
        r = wallet.pct_change().dropna()
        sh, sk, kt, n = _sharpe_components(r, annualisation)
        components.append((label, sh, sk, kt, n))

    if not components:
        return []

    sharpe_var = (
        float(np.var([c[1] for c in components], ddof=1))
        if len(components) > 1
        else 0.0
    )
    sr_star = expected_max_sharpe(sharpe_var, len(components))

    rows: list[DSRStats] = []
    for label, sh, sk, kt, n in components:
        dsr = deflated_sharpe(sh, sr_star, sk, kt, n)
        rows.append(DSRStats(label, sh, sk, kt, n, sr_star, dsr, _verdict(dsr)))
    rows.sort(key=lambda r: -r.dsr)
    return rows


def format_dsr_table(rows: list[DSRStats]) -> str:
    if not rows:
        return "_(no DSR rows)_"
    head = (
        "| Strategy | Sharpe | Skew | Kurt | N | DSR | Verdict |\n"
        "|---|---:|---:|---:|---:|---:|---|"
    )
    body = "\n".join(
        f"| {r.label} | {r.sharpe:.3f} | {r.skew:+.2f} | {r.kurt:.2f} | "
        f"{r.n_obs} | {r.dsr:.3f} | {r.verdict} |"
        for r in rows
    )
    sr_star = rows[0].sharpe_star
    return (
        f"_N_trials={len(rows)}; SR* (expected max under null) = {sr_star:.3f}_"
        f"\n\n{head}\n{body}"
    )
