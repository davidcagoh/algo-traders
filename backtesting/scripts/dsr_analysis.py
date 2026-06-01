#!/usr/bin/env python3
"""
Deflated Sharpe Ratio analysis across all backtested strategies.

For each strategy, compute the daily-wallet Sharpe (with adjustments for
skew and kurtosis), then deflate by the expected-max-Sharpe under the null
across N trials (López de Prado 2014).

DSR = Φ( (SR_hat - SR_star) × √(N_obs - 1) /
         √(1 - γ_3 × SR_hat + (γ_4 - 1) / 4 × SR_hat²) )

where:
- SR_hat   observed annualised Sharpe
- SR_star  expected max Sharpe under null across N trials
- γ_3, γ_4 sample skew and kurtosis of daily returns
- N_obs    number of daily return observations
- Φ        standard-normal CDF

SR_star is approximated (López de Prado 2014):
    SR_star = √V × ((1-γ) Φ^-1(1 - 1/N) + γ Φ^-1(1 - 1/(N e)))
where V is variance of Sharpe estimates across trials and γ = 0.5772 (Euler-Mascheroni).

A strategy is signal-distinguishable when DSR > 0.95.

Usage:
    ./freqtrade/.venv/bin/python scripts/dsr_analysis.py
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# Shared loaders moved to eval_layers.py (single source of truth, A1 refactor).
from eval_layers import load_daily_returns, load_trade_returns  # noqa: F401


REPO_ROOT = Path(__file__).resolve().parent.parent
ZIP_DIR = REPO_ROOT / "user_data" / "backtest_results"

# Backtest archives to include in the analysis. Each entry is a tuple of
# (label, zip filename relative to ZIP_DIR, window-type for context).
RUNS = [
    ("HmmRegime4Rolling-multi (bull)", "hmm_multi_binance_bull_2023_2025.zip", "bull"),
    ("HmmCarry (bull)",                 "hmm_carry_binance_bull_2023_2025.zip", "bull"),
    ("FundingCarry (bull)",             "funding_carry_binance_bull_2023_2025.zip", "bull"),
    ("HmmSmaSlope (bull)",              "hmm_sma_slope_binance_bull.zip", "bull"),
    ("HmmSmaSlopeV2 (bull)",            "hmm_sma_slope_v2_binance_bull.zip", "bull"),
    ("HmmSmaSlopeV3 (bull)",            "hmm_sma_slope_v3_binance_bull.zip", "bull"),
    ("HmmSmaSlope (bear)",              "hmm_sma_slope_hl_bear.zip", "bear"),
    ("HmmSmaSlopeV2 (bear)",            "hmm_sma_slope_v2_hl_bear.zip", "bear"),
    ("HmmSmaSlopeV3 (bear)",            "hmm_sma_slope_v3_hl_bear.zip", "bear"),
]

EULER_GAMMA = 0.5772156649


@dataclass
class StratStats:
    label: str
    window: str
    sharpe: float
    skew: float
    kurt: float
    n_obs: int
    sharpe_star: float = 0.0
    dsr: float = 0.0


def compute_sharpe(returns: pd.Series, annualisation: float = 365.0) -> tuple[float, float, float, int]:
    """Return (annualised_sharpe, skew, kurtosis, n_obs). Pass annualisation
    = 365 for daily returns, or N_trades_per_year for per-trade returns."""
    n = len(returns)
    if n < 2 or returns.std() == 0:
        return 0.0, 0.0, 3.0, n
    mu, sd = returns.mean(), returns.std()
    sharpe = (mu / sd) * math.sqrt(annualisation)
    skew = float(stats.skew(returns, bias=False))
    kurt = float(stats.kurtosis(returns, bias=False, fisher=False))  # non-excess
    return sharpe, skew, kurt, n


def expected_max_sharpe(sharpe_var: float, n_trials: int) -> float:
    """
    López de Prado 2014, Eq. 7: expected maximum Sharpe across N independent
    trials assuming Sharpes are normally distributed around 0 with variance V.
    """
    n = max(2, n_trials)
    z1 = stats.norm.ppf(1.0 - 1.0 / n)
    z2 = stats.norm.ppf(1.0 - 1.0 / (n * math.e))
    return math.sqrt(sharpe_var) * ((1.0 - EULER_GAMMA) * z1 + EULER_GAMMA * z2)


def deflated_sharpe(sharpe: float, sharpe_star: float, skew: float,
                    kurt: float, n_obs: int) -> float:
    """
    López de Prado 2014, Eq. 9: probability the true SR exceeds SR_star
    given the observed sample Sharpe, its skew/kurt, and the sample length.
    Returns DSR in [0, 1].
    """
    if n_obs < 3:
        return 0.0
    denom = math.sqrt(max(1e-9, 1.0 - skew * sharpe + ((kurt - 1.0) / 4.0) * sharpe ** 2))
    z = (sharpe - sharpe_star) * math.sqrt(n_obs - 1) / denom
    return float(stats.norm.cdf(z))


def main() -> None:
    rows_daily: list[StratStats] = []
    rows_trade: list[StratStats] = []
    for label, fname, window in RUNS:
        path = ZIP_DIR / fname
        if not path.exists():
            print(f"  [skip] {label}: {fname} not found")
            continue

        # Daily-wallet basis
        d_ret = load_daily_returns(path)
        sh, sk, kt, n = compute_sharpe(d_ret, annualisation=365.0)
        rows_daily.append(StratStats(label, window, sh, sk, kt, n))

        # Per-trade basis — annualise by N_trades_per_year computed from span
        t_ret = load_trade_returns(path)
        n_trades = len(t_ret)
        if n_trades >= 3 and not d_ret.empty:
            years = (d_ret.index[-1] - d_ret.index[0]).days / 365.25
            trades_per_year = n_trades / max(years, 1e-6)
            sh, sk, kt, n = compute_sharpe(t_ret, annualisation=trades_per_year)
            rows_trade.append(StratStats(label, window, sh, sk, kt, n))

    rows = rows_daily

    def _run(label: str, row_set: list[StratStats]) -> None:
        if not row_set:
            return
        n_trials = len(row_set)
        sharpe_var = float(np.var([r.sharpe for r in row_set], ddof=1))
        sr_star = expected_max_sharpe(sharpe_var, n_trials)
        for r in row_set:
            r.sharpe_star = sr_star
            r.dsr = deflated_sharpe(r.sharpe, sr_star, r.skew, r.kurt, r.n_obs)
        print(f"\n=== {label} === N_trials={n_trials}  SR_star={sr_star:.2f}  σ²(SR)={sharpe_var:.2f}")
        header = f"{'Strategy':<35} {'Win':>4} {'Sharpe':>7} {'Skew':>6} {'Kurt':>7} {'N':>5} {'DSR':>7} {'Verdict':>9}"
        print(header)
        print("-" * len(header))
        for r in sorted(row_set, key=lambda x: -x.dsr):
            verdict = "SIGNAL" if r.dsr > 0.95 else ("WEAK" if r.dsr > 0.5 else "NOISE")
            print(f"{r.label:<35} {r.window:>4} {r.sharpe:>7.2f} {r.skew:>6.2f} {r.kurt:>7.2f} "
                  f"{r.n_obs:>5d} {r.dsr:>7.3f} {verdict:>9}")

    _run("Daily-wallet returns (standard)", rows_daily)
    _run("Per-trade returns (alternative basis)", rows_trade)
    rows = rows_daily  # for JSON output below

    # Write structured output for the result card (daily-wallet basis)
    out = REPO_ROOT / "wiki" / "results" / "_dsr_table.json"
    with open(out, "w") as f:
        json.dump({
            "daily_wallet": [
                {
                    "strategy": r.label, "window": r.window,
                    "sharpe": r.sharpe, "skew": r.skew, "kurt": r.kurt,
                    "n_obs": r.n_obs, "dsr": r.dsr,
                }
                for r in rows_daily
            ],
            "per_trade": [
                {
                    "strategy": r.label, "window": r.window,
                    "sharpe": r.sharpe, "skew": r.skew, "kurt": r.kurt,
                    "n_obs": r.n_obs, "dsr": r.dsr,
                }
                for r in rows_trade
            ],
        }, f, indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
