"""Dependency-light OLS with Newey-West errors for exploratory regressions."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RegressionResult:
    coefficients: pd.Series
    standard_errors: pd.Series
    t_statistics: pd.Series
    p_values_normal: pd.Series
    fitted: pd.Series
    residuals: pd.Series
    r_squared: float
    adjusted_r_squared: float
    observations: int
    covariance: str
    hac_lags: int

    @property
    def summary(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "coefficient": self.coefficients,
                "std_error": self.standard_errors,
                "t_stat": self.t_statistics,
                "p_value_normal": self.p_values_normal,
            }
        )

    def __repr__(self) -> str:
        heading = (
            f"OLS: n={self.observations}, R²={self.r_squared:.4f}, "
            f"adj. R²={self.adjusted_r_squared:.4f}, covariance={self.covariance}"
        )
        return heading + "\n" + self.summary.to_string(float_format=lambda value: f"{value:.6g}")


def ols(
    y: pd.Series,
    x: pd.DataFrame,
    *,
    add_constant: bool = True,
    hac_lags: int | str | None = "auto",
) -> RegressionResult:
    frame = pd.concat([y.rename("__y__"), x], axis=1, join="inner").dropna()
    if frame.empty:
        raise ValueError("regression has no aligned, non-missing observations")
    y_values = frame.pop("__y__").to_numpy(dtype=float)
    design = frame.astype(float)
    if add_constant:
        design.insert(0, "constant", 1.0)
    matrix = design.to_numpy()
    n_obs, n_params = matrix.shape
    if n_obs <= n_params:
        raise ValueError(f"regression needs more observations than parameters ({n_obs} <= {n_params})")

    coefficients = np.linalg.lstsq(matrix, y_values, rcond=None)[0]
    fitted_values = matrix @ coefficients
    residual_values = y_values - fitted_values
    xtx_inverse = np.linalg.pinv(matrix.T @ matrix)
    dof = n_obs - n_params

    if hac_lags == "auto":
        lag_count = int(math.floor(4.0 * (n_obs / 100.0) ** (2.0 / 9.0)))
    elif hac_lags is None:
        lag_count = 0
    else:
        lag_count = int(hac_lags)
        if lag_count < 0:
            raise ValueError("hac_lags cannot be negative")

    if hac_lags is None:
        variance = float(residual_values @ residual_values / dof)
        covariance_matrix = variance * xtx_inverse
        covariance_name = "classic"
    else:
        scores = matrix * residual_values[:, None]
        meat = scores.T @ scores
        for lag in range(1, min(lag_count, n_obs - 1) + 1):
            weight = 1.0 - lag / (lag_count + 1.0)
            gamma = scores[lag:].T @ scores[:-lag]
            meat += weight * (gamma + gamma.T)
        covariance_matrix = xtx_inverse @ meat @ xtx_inverse
        covariance_name = f"Newey-West({lag_count})"

    standard_errors = np.sqrt(np.maximum(np.diag(covariance_matrix), 0.0))
    t_statistics = np.divide(
        coefficients,
        standard_errors,
        out=np.full_like(coefficients, np.nan),
        where=standard_errors > 0,
    )
    p_values = np.array([math.erfc(abs(value) / math.sqrt(2.0)) for value in t_statistics])
    total = float(((y_values - y_values.mean()) ** 2).sum())
    residual_sum = float((residual_values**2).sum())
    r_squared = 1.0 - residual_sum / total if total > 0 else float("nan")
    adjusted = 1.0 - (1.0 - r_squared) * (n_obs - 1) / dof
    index = design.columns
    observation_index = frame.index
    return RegressionResult(
        coefficients=pd.Series(coefficients, index=index, name="coefficient"),
        standard_errors=pd.Series(standard_errors, index=index, name="std_error"),
        t_statistics=pd.Series(t_statistics, index=index, name="t_stat"),
        p_values_normal=pd.Series(p_values, index=index, name="p_value_normal"),
        fitted=pd.Series(fitted_values, index=observation_index, name="fitted"),
        residuals=pd.Series(residual_values, index=observation_index, name="residual"),
        r_squared=r_squared,
        adjusted_r_squared=adjusted,
        observations=n_obs,
        covariance=covariance_name,
        hac_lags=lag_count,
    )
