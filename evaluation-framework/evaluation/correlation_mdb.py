"""Layer-6: portfolio-additive metrics — correlation + Marginal Diversification
Benefit (MDB).

Cross-venue port of `feishu/eval/correlation_mdb.py`. Annualisation is a
parameter.

Definitions (`../wiki/learnings-archive.md`)
---------------------------------------
MDB[c | book] = Sharpe(book ∪ {c}) − Sharpe(book)

Computed under three weighting schemes:
  eq  — equal weight (1/N)
  rp  — inverse-vol risk parity (90-period trailing; headline scheme)
  mv  — long-only Markowitz mean-var (unstable at small N → upper bound)

A candidate is *robustly diversifying* iff MDB > 0 under all three.

Companion: pairwise Pearson on daily returns. Pairs above ~0.95 are one
strategy regardless of implementation differences; keep only one.

Gate-1 check (`../wiki/learnings-archive.md` 2026-05-20): require positive
standalone Sharpe on the candidate before computing MDB. For negative-
Sharpe candidates the MDB is dominated by Sharpe arithmetic, not by
diversification benefit, and the gate fires spuriously.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from evaluation.layers import DEFAULT_ANNUAL


# ─── Returns matrix ───────────────────────────────────────────────────────────


def returns_matrix(wallets: dict[str, pd.Series]) -> pd.DataFrame:
    """Build a (period × strategy) daily-return DataFrame.

    Periods where a strategy has no observation are filled with 0 — locked-in
    convention matching the feishu/backtesting port. This pulls correlations
    toward zero by construction; rolling-window correlation is the v2.
    """
    series: dict[str, pd.Series] = {}
    for label, w in wallets.items():
        if w is None or len(w) < 2:
            continue
        series[label] = w.pct_change().dropna()
    df = pd.DataFrame(series).fillna(0.0)
    return df


def correlation_matrix(
    returns: pd.DataFrame, method: str = "pearson"
) -> pd.DataFrame:
    return returns.corr(method=method)


# ─── Portfolio Sharpe ─────────────────────────────────────────────────────────


def _portfolio_sharpe(
    returns: pd.DataFrame,
    weights: dict[str, float],
    annualisation: float = DEFAULT_ANNUAL,
) -> float:
    cols = list(weights.keys())
    w = np.array([weights[c] for c in cols])
    series = returns[cols].values @ w
    if series.size < 2 or series.std() == 0:
        return 0.0
    return float(series.mean() / series.std() * math.sqrt(annualisation))


# ─── Weighting schemes ────────────────────────────────────────────────────────


def _equal_weights(strategies: list[str]) -> dict[str, float]:
    n = len(strategies)
    return {s: 1.0 / n for s in strategies}


def _risk_parity_weights(
    returns: pd.DataFrame,
    strategies: list[str],
    vol_window: int = 90,
) -> dict[str, float]:
    vols: dict[str, float] = {}
    for s in strategies:
        recent = (
            returns[s].iloc[-vol_window:]
            if len(returns) > vol_window
            else returns[s]
        )
        sd = recent.std()
        vols[s] = sd if sd > 0 else 1e-9
    inv = {s: 1.0 / v for s, v in vols.items()}
    total = sum(inv.values())
    return {s: x / total for s, x in inv.items()}


def _mean_variance_weights(
    returns: pd.DataFrame, strategies: list[str]
) -> dict[str, float]:
    """Long-only tangency-portfolio weights. Numerically unstable at small N."""
    sub = returns[strategies].dropna(how="any")
    if len(sub) < 30:
        return _equal_weights(strategies)
    mu = sub.mean().values
    cov = sub.cov().values
    try:
        inv_cov = np.linalg.pinv(cov)
        raw = inv_cov @ mu
        raw = np.clip(raw, 0.0, None)
        if raw.sum() <= 0:
            return _equal_weights(strategies)
        return dict(zip(strategies, (raw / raw.sum()).tolist()))
    except (np.linalg.LinAlgError, ValueError):
        return _equal_weights(strategies)


# ─── MDB ──────────────────────────────────────────────────────────────────────


def marginal_diversification_benefit(
    returns: pd.DataFrame,
    book: list[str],
    candidate: str,
    scheme: str = "rp",
    vol_window: int = 90,
    annualisation: float = DEFAULT_ANNUAL,
) -> float:
    """MDB[candidate | book] under one of {eq, rp, mv}."""
    if candidate in book:
        return 0.0
    extended = book + [candidate]
    if scheme == "eq":
        wb, we = _equal_weights(book), _equal_weights(extended)
    elif scheme == "rp":
        wb = _risk_parity_weights(returns, book, vol_window)
        we = _risk_parity_weights(returns, extended, vol_window)
    elif scheme == "mv":
        wb = _mean_variance_weights(returns, book)
        we = _mean_variance_weights(returns, extended)
    else:
        raise ValueError(f"unknown MDB scheme: {scheme!r}")
    return (
        _portfolio_sharpe(returns, we, annualisation)
        - _portfolio_sharpe(returns, wb, annualisation)
    )


def mdb_robust_flag(
    returns: pd.DataFrame,
    book: list[str],
    candidate: str,
    eps: float = 0.0,
    annualisation: float = DEFAULT_ANNUAL,
) -> bool:
    """True iff MDB > eps under all three schemes (eq, rp, mv)."""
    for scheme in ("eq", "rp", "mv"):
        m = marginal_diversification_benefit(
            returns, book, candidate, scheme, annualisation=annualisation
        )
        if m <= eps:
            return False
    return True


def mdb_table(
    returns: pd.DataFrame,
    book: list[str],
    candidates: list[str],
    annualisation: float = DEFAULT_ANNUAL,
) -> pd.DataFrame:
    """Rows = candidates; columns = eq/rp/mv MDB + robust flag."""
    rows: list[dict] = []
    for c in candidates:
        eq = marginal_diversification_benefit(
            returns, book, c, "eq", annualisation=annualisation
        )
        rp = marginal_diversification_benefit(
            returns, book, c, "rp", annualisation=annualisation
        )
        mv = marginal_diversification_benefit(
            returns, book, c, "mv", annualisation=annualisation
        )
        rows.append(
            {
                "candidate": c,
                "MDB_eq": eq,
                "MDB_rp": rp,
                "MDB_mv": mv,
                "robust": eq > 0 and rp > 0 and mv > 0,
            }
        )
    return pd.DataFrame(rows).set_index("candidate")
