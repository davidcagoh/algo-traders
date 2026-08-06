"""Factor regression with HAC (Newey-West) standard errors.

Literature: Chauhan 2026 (SSRN 6861958) — Sharpe-ratio variance inflation
under cross-sectional and serial dependence; an alpha that vanishes against
a market beta is not an alpha. Pippas, Ludvig & Turkay 2025
(`../literature/strategy-evaluation/surveys/2408.10932-rl-quant-finance-survey.pdf`)
— factor controls and survivorship bias in strategy evaluation. Long-only
trend strategies on crypto majors (this project's own HmmSmaSlope family)
are plausibly explained by market beta alone; nothing in the existing
six-layer stack could reveal that without a factor regression.

`statsmodels` (the `factor` extra) is used when available for a proper HAC
covariance estimator; a small pure-numpy Newey-West fallback keeps the
package's core dependency-free.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FactorResult:
    alpha: float
    alpha_tstat: float
    betas: dict[str, float]
    beta_tstats: dict[str, float]
    r_squared: float
    n_obs: int


def _newey_west_ols(
    y: np.ndarray, x: np.ndarray, lags: int
) -> tuple[np.ndarray, np.ndarray, float]:
    """OLS with a Newey-West HAC covariance matrix. `x` includes an
    intercept column. Returns (coefs, coef_se, r_squared)."""
    xtx_inv = np.linalg.pinv(x.T @ x)
    beta = xtx_inv @ x.T @ y
    resid = y - x @ beta
    u = x * resid[:, None]

    s = u.T @ u
    for lag in range(1, lags + 1):
        weight = 1.0 - lag / (lags + 1)
        gamma = u[lag:].T @ u[:-lag]
        s += weight * (gamma + gamma.T)

    cov = xtx_inv @ s @ xtx_inv
    se = np.sqrt(np.clip(np.diag(cov), 0, None))

    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return beta, se, r2


def _auto_lags(n: int) -> int:
    return max(1, round(4 * (n / 100) ** (2 / 9)))


def factor_regression(
    strategy_returns: pd.Series,
    factors: pd.DataFrame,
    hac_lags: int | str = "auto",
) -> FactorResult:
    """Regress `strategy_returns` on `factors` (period x factor DataFrame)
    with an intercept, reporting alpha and betas with HAC t-stats.
    """
    aligned = pd.concat([strategy_returns.rename("y"), factors], axis=1, join="inner").dropna()
    if len(aligned) < len(factors.columns) + 2:
        raise ValueError("not enough overlapping observations for factor regression")

    y = aligned["y"].to_numpy()
    factor_names = list(factors.columns)
    x_factors = aligned[factor_names].to_numpy()
    x = np.column_stack([np.ones(len(y)), x_factors])

    lags = _auto_lags(len(y)) if hac_lags == "auto" else int(hac_lags)
    coefs, se, r2 = _newey_west_ols(y, x, lags)

    alpha, betas_arr = coefs[0], coefs[1:]
    alpha_se, beta_se = se[0], se[1:]

    return FactorResult(
        alpha=float(alpha),
        alpha_tstat=float(alpha / alpha_se) if alpha_se > 0 else float("nan"),
        betas=dict(zip(factor_names, betas_arr.tolist())),
        beta_tstats={
            name: float(b / s) if s > 0 else float("nan")
            for name, b, s in zip(factor_names, betas_arr, beta_se)
        },
        r_squared=float(r2),
        n_obs=len(y),
    )


def crypto_factors(
    market_returns: pd.Series,
    momentum_returns: pd.Series | None = None,
    funding_returns: pd.Series | None = None,
) -> pd.DataFrame:
    """Assemble a minimal crypto factor frame: market (BTC), optional
    cross-sectional momentum, optional funding/carry. Callers supply their
    own return series (this package does not fetch data); this is a
    convenience for column-naming and alignment, not a data source.
    """
    factors = {"market": market_returns}
    if momentum_returns is not None:
        factors["momentum"] = momentum_returns
    if funding_returns is not None:
        factors["funding_carry"] = funding_returns
    return pd.concat(factors, axis=1, join="inner")


def format_factor_table(result: FactorResult, label: str = "") -> str:
    title = f" — {label}" if label else ""
    alpha_sig = "significant" if abs(result.alpha_tstat) > 1.96 else "not significant"
    rows = [f"| alpha | {result.alpha:+.5f} | {result.alpha_tstat:+.2f} | {alpha_sig} |"]
    for name, beta in result.betas.items():
        t = result.beta_tstats[name]
        rows.append(
            f"| {name} | {beta:+.3f} | {t:+.2f} | "
            f"{'significant' if abs(t) > 1.96 else 'not significant'} |"
        )
    body = "\n".join(rows)
    return (
        f"### Factor regression (HAC){title}\n\n"
        "| Term | Coef | t-stat | Reading |\n"
        "|---|---:|---:|---|\n"
        f"{body}\n\n"
        f"_R² = {result.r_squared:.3f}, N = {result.n_obs}_"
    )
