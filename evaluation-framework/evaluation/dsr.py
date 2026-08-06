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

Corrected 2026-08-06 (`../wiki/decisions-archive.md`): the 2026-05-20
carve-out also demoted DSR to a humility check under high excess kurtosis.
That double-counted — the denominator above already absorbs skew (γ_3) and
kurtosis (γ_4) by construction, so a fat-tailed sample already produces a
low DSR on its own; no separate kurtosis gate is needed, and having one let
a DSR=0.000 strategy (`HmmSmaSlopeV2`) be waved through to paper trading,
where it then failed live. `is_dsr_binding()` now only checks N_obs, which
governs whether the CLT-based standard-error approximation the formula
relies on is valid — a distinct concern from the skew/kurtosis correction
already inside the formula.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from scipy import stats

from evaluation.layers import DEFAULT_ANNUAL, kurt_excess

if TYPE_CHECKING:
    from evaluation.ledger import TrialLedger

EULER_GAMMA = 0.5772156649

# Small-sample threshold below which the DSR formula's CLT-based standard
# error is unreliable, independent of skew/kurtosis (2026-05-20, N-clause
# retained; kurtosis clause removed 2026-08-06 — see module docstring).
DSR_BINDING_N_MIN = 250


@dataclass(frozen=True)
class DSRStats:
    label: str
    sharpe: float
    skew: float
    kurt: float  # non-excess (Pearson) for direct use in the formula
    n_obs: int
    sharpe_star: float
    dsr: float
    verdict: str  # SIGNAL / WEAK / NOISE


def _sharpe_components(returns: pd.Series, annualisation: float) -> tuple[float, float, float, int]:
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
    return math.sqrt(max(sharpe_var, 0.0)) * ((1.0 - EULER_GAMMA) * z1 + EULER_GAMMA * z2)


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
    """Check the small-sample carve-out.

    Returns (binding, reason). When False, N_obs is too low for the DSR
    formula's CLT-based standard error to be trusted as a pass/fail gate.
    Fat-tailed samples are *not* carved out here: the DSR formula already
    penalises high skew/kurtosis through its denominator, so a fat-tailed
    strategy should simply score a low DSR rather than being exempted from
    the gate. If a strategy is failing DSR only because of kurtosis, prefer
    a less kurtosis-sensitive deflator (PBO/CSCV) over demoting DSR.
    """
    n = len(returns)
    ek = kurt_excess(returns)
    if n <= DSR_BINDING_N_MIN:
        return False, f"N={n} <= {DSR_BINDING_N_MIN} (insufficient daily obs)"
    return True, f"N={n}, excess kurt={ek:.2f} (binding)"


def _verdict(dsr: float) -> str:
    if dsr > 0.95:
        return "SIGNAL"
    if dsr > 0.5:
        return "WEAK"
    return "NOISE"


def compute_dsr_table(
    wallets: dict[str, pd.Series],
    *,
    n_trials: int,
    annualisation: float = DEFAULT_ANNUAL,
    sharpe_var: float | None = None,
) -> list[DSRStats]:
    """Compute DSR for each (label → wallet curve) entry in `wallets`.

    `n_trials` is required and must be the size of the real search — every
    parameter combination and strategy variant actually tried, including
    discarded ones, not just the leaderboard/survivors in `wallets`. Passing
    `len(wallets)` here silently under-deflates: SR_star only grows with the
    trials you tell it about.

    `sharpe_var` (the cross-trial Sharpe variance feeding SR_star) defaults
    to the variance of the Sharpes in `wallets` when not given — but that is
    only a good estimate when `wallets` is representative of the full
    search. Passing a *narrow, correlated family* (e.g. minor parameter
    variants of one strategy, all with similar Sharpes) understates the true
    cross-trial variance and inflates DSR, the mirror-image bug of passing
    too few trials for `n_trials`. When the full search spans structurally
    different strategies, compute `sharpe_var` from that wider set (e.g.
    `ledger.sharpe_variance(...)` scoped broadly) and pass it explicitly.
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

    if n_trials < len(components):
        raise ValueError(
            f"n_trials={n_trials} is smaller than the {len(components)} "
            "candidates passed in — n_trials must cover at least the "
            "wallets given, and should cover the full search."
        )

    if sharpe_var is None:
        sharpe_var = (
            float(np.var([c[1] for c in components], ddof=1)) if len(components) > 1 else 0.0
        )
    sr_star = expected_max_sharpe(sharpe_var, n_trials)

    rows: list[DSRStats] = []
    for label, sh, sk, kt, n in components:
        dsr = deflated_sharpe(sh, sr_star, sk, kt, n)
        rows.append(DSRStats(label, sh, sk, kt, n, sr_star, dsr, _verdict(dsr)))
    rows.sort(key=lambda r: -r.dsr)
    return rows


def compute_dsr_from_ledger(
    wallets: dict[str, pd.Series],
    ledger: TrialLedger,
    annualisation: float = DEFAULT_ANNUAL,
    variance_scope_kwargs: dict[str, object] | None = None,
    **scope_kwargs: object,
) -> list[DSRStats]:
    """Compute DSR pulling `n_trials` (and, by default, `sharpe_var`) from a
    `TrialLedger` scope.

    `n_trials` = the ledger's trial count (including discarded trials) for
    the given scope, not `len(wallets)`. Pass `family=`, `dataset_id=`, or
    `since=` via `scope_kwargs` to restrict which ledger rows count toward
    `n_trials`. `sharpe_var` is pulled from the ledger's recorded Sharpes
    over the same scope by default (a more representative variance estimate
    than `wallets` alone when `wallets` is a narrow family — see
    `compute_dsr_table`'s docstring); pass `variance_scope_kwargs` to widen
    that scope independently (e.g. drop `family=` so variance reflects the
    whole search, not just the family being scored).
    """
    n_trials = ledger.n_trials(**scope_kwargs)
    sharpe_var = ledger.sharpe_variance(**(variance_scope_kwargs or scope_kwargs))
    return compute_dsr_table(
        wallets, n_trials=n_trials, annualisation=annualisation, sharpe_var=sharpe_var or None
    )


def format_dsr_table(rows: list[DSRStats], n_trials: int) -> str:
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
        f"_N_trials={n_trials} (real search size); N_reported={len(rows)} "
        f"(rows shown); SR* (expected max under null) = {sr_star:.3f}_"
        f"\n\n{head}\n{body}"
    )
