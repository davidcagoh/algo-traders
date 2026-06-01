#!/usr/bin/env python3
"""
Layer-5 evaluation metrics: tail shape + path-aware drawdown.

These metrics complement Calmar/SQN/DSR (Layers 2-4) by exposing what a single
risk-adjusted-return number hides: skew, fat tails, and the *shape* of the
drawdown path (not just its deepest point).

Metrics produced
----------------
skew          sample skew of daily wallet log-returns
kurt_excess   excess kurtosis (Gaussian = 0; fat tails > 0)
tail_ratio    |P95| / |P5| of daily returns; > 1 = right-tailed
cvar_5        mean(daily returns <= P5); typically negative
ulcer_index   sqrt(mean(drawdown_pct ** 2)) along wallet curve — path-aware
martin_ratio  CAGR / ulcer_index — "return per unit of underwater pain"
pain_index    mean(|drawdown_pct|) — simpler than ulcer (no squaring)

Usage
-----
    ./freqtrade/.venv/bin/python scripts/eval_layers.py <zip_path>

Prints a markdown table suitable for paste into wiki/results/*.md.

This module is also imported by dsr_analysis.py for the shared loader.
"""
from __future__ import annotations

import json
import math
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Shared loaders (extracted from dsr_analysis.py — single source of truth)
# ---------------------------------------------------------------------------


def load_wallet_curve(zip_path: Path) -> pd.Series:
    """Load the daily wallet-balance series from a freqtrade backtest zip.

    Returns the *level* series (not returns), indexed by UTC date.
    Resampled to daily, last value per day.
    """
    with zipfile.ZipFile(zip_path) as z:
        wallet_files = [n for n in z.namelist() if n.endswith("_wallet.feather")]
        if not wallet_files:
            raise FileNotFoundError(f"no wallet feather in {zip_path.name}")
        with z.open(wallet_files[0]) as f:
            df = pd.read_feather(f)
    df = df[["date", "total_quote"]].copy()
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.set_index("date")
    return df["total_quote"].resample("1D").last().dropna()


def load_daily_returns(zip_path: Path) -> pd.Series:
    """Daily log-returns of the wallet balance."""
    wallet = load_wallet_curve(zip_path)
    return np.log(wallet / wallet.shift(1)).dropna()


def load_trade_returns(zip_path: Path) -> pd.Series:
    """Per-trade profit ratios. Each trade is one observation."""
    with zipfile.ZipFile(zip_path) as z:
        name = [
            n
            for n in z.namelist()
            if n.endswith(".json") and "config" not in n and "meta" not in n
        ][0]
        d = json.loads(z.read(name))
    strat = list(d["strategy"].values())[0]
    trades = pd.DataFrame(strat["trades"])
    if trades.empty:
        return pd.Series(dtype=float)
    return trades["profit_ratio"]


# ---------------------------------------------------------------------------
# Layer-5 metric functions — each pure, < 15 lines, operates on pd.Series
# ---------------------------------------------------------------------------


def skew(returns: pd.Series) -> float:
    """Sample skew of daily returns. Negative = left-tailed (loss-skewed)."""
    if len(returns) < 3:
        return 0.0
    return float(stats.skew(returns, bias=False))


def kurt_excess(returns: pd.Series) -> float:
    """Excess kurtosis (fisher=True). Gaussian = 0, fat tails > 0."""
    if len(returns) < 4:
        return 0.0
    return float(stats.kurtosis(returns, bias=False, fisher=True))


def tail_ratio(returns: pd.Series) -> float:
    """|P95| / |P5|. > 1 = right-tailed (let-winners-run); < 1 = left-tailed."""
    if len(returns) < 20:
        return float("nan")
    p95 = float(np.quantile(returns, 0.95))
    p5 = float(np.quantile(returns, 0.05))
    if p5 == 0:
        return float("nan")
    return abs(p95) / abs(p5)


def cvar_5(returns: pd.Series) -> float:
    """Mean of returns in the worst 5% (Expected Shortfall at 5%). Negative."""
    if len(returns) < 20:
        return float("nan")
    p5 = float(np.quantile(returns, 0.05))
    tail = returns[returns <= p5]
    if tail.empty:
        return float("nan")
    return float(tail.mean())


def _drawdown_series(wallet: pd.Series) -> pd.Series:
    """Drawdown percentage from running peak. Always <= 0."""
    running_peak = wallet.cummax()
    return (wallet / running_peak - 1.0) * 100.0


def ulcer_index(wallet: pd.Series) -> float:
    """sqrt(mean(drawdown_pct ** 2)) along the wallet curve. Path-aware."""
    if len(wallet) < 2:
        return float("nan")
    dd = _drawdown_series(wallet)
    return float(np.sqrt(np.mean(dd**2)))


def pain_index(wallet: pd.Series) -> float:
    """mean(|drawdown_pct|). Simpler than ulcer (no squaring)."""
    if len(wallet) < 2:
        return float("nan")
    dd = _drawdown_series(wallet)
    return float(np.mean(np.abs(dd)))


def martin_ratio(wallet: pd.Series, annualisation: float = 365.0) -> float:
    """CAGR / ulcer_index. Return per unit of underwater pain."""
    if len(wallet) < 2:
        return float("nan")
    ui = ulcer_index(wallet)
    if ui == 0 or math.isnan(ui):
        return float("nan")
    years = (wallet.index[-1] - wallet.index[0]).days / 365.25
    if years <= 0:
        return float("nan")
    total_return = wallet.iloc[-1] / wallet.iloc[0]
    cagr_pct = (total_return ** (1.0 / years) - 1.0) * 100.0
    return float(cagr_pct / ui)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Layer5Metrics:
    skew: float
    kurt_excess: float
    tail_ratio: float
    cvar_5_pct: float
    ulcer_index: float
    martin_ratio: float
    pain_index: float
    n_obs: int


def compute_layer5_metrics(zip_path: Path) -> Layer5Metrics:
    """Compute the seven Layer-5 metrics for a single backtest ZIP."""
    returns = load_daily_returns(zip_path)
    wallet = load_wallet_curve(zip_path)
    # CVaR/tail_ratio are reported in percent for readability.
    return Layer5Metrics(
        skew=skew(returns),
        kurt_excess=kurt_excess(returns),
        tail_ratio=tail_ratio(returns),
        cvar_5_pct=cvar_5(returns) * 100.0,
        ulcer_index=ulcer_index(wallet),
        martin_ratio=martin_ratio(wallet),
        pain_index=pain_index(wallet),
        n_obs=len(returns),
    )


# ---------------------------------------------------------------------------
# Correlation + MDB (Marginal Diversification Benefit)
# ---------------------------------------------------------------------------

ANNUALISATION = 365.0  # crypto trades 365 days (pre-decision Q1, locked-in)


def build_returns_matrix(zip_paths: dict[str, Path]) -> pd.DataFrame:
    """Load daily log-returns from each ZIP and join on common dates.

    Missing dates (strategy was flat) are filled with 0 — locked-in choice
    per decision 005 pre-decision Q1. This pulls correlations toward zero by
    construction; rolling-window 90d correlation is the v2 alternative.

    Returns a DataFrame indexed by UTC date, with one column per strategy code.
    """
    series = {code: load_daily_returns(p) for code, p in zip_paths.items()}
    df = pd.DataFrame(series)
    df = df.fillna(0.0)
    return df


def correlation_matrix(returns: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    """Pairwise correlation matrix of daily returns. method ∈ {pearson, spearman}."""
    return returns.corr(method=method)


def _sharpe(returns: pd.Series, annualisation: float = ANNUALISATION) -> float:
    """Annualised Sharpe of a return series."""
    sd = returns.std()
    if sd == 0 or len(returns) < 2:
        return 0.0
    return float((returns.mean() / sd) * math.sqrt(annualisation))


def _portfolio_returns(
    returns: pd.DataFrame, weights: dict[str, float]
) -> pd.Series:
    """Compute weighted-portfolio daily return series."""
    cols = list(weights.keys())
    w = np.array([weights[c] for c in cols])
    sub = returns[cols]
    return pd.Series(sub.values @ w, index=sub.index)


def _equal_weights(strategies: list[str]) -> dict[str, float]:
    """1/N weights."""
    n = len(strategies)
    return {s: 1.0 / n for s in strategies}


def _risk_parity_weights(
    returns: pd.DataFrame, strategies: list[str], vol_window: int = 90
) -> dict[str, float]:
    """Inverse-vol weights using the trailing vol_window of each series.
    Each strategy contributes equal risk."""
    vols = {}
    for s in strategies:
        recent = returns[s].iloc[-vol_window:] if len(returns) > vol_window else returns[s]
        sd = recent.std()
        vols[s] = sd if sd > 0 else 1e-9
    inv = {s: 1.0 / v for s, v in vols.items()}
    total = sum(inv.values())
    return {s: x / total for s, x in inv.items()}


def _mean_variance_weights(
    returns: pd.DataFrame, strategies: list[str]
) -> dict[str, float]:
    """Sharpe-optimal weights via Markowitz mean-var (no shorting, no risk-free).
    Numerically unstable at small N — flagged for MDB-mv 'upper bound' reading."""
    sub = returns[strategies].dropna(how="any")
    if len(sub) < 30:
        return _equal_weights(strategies)
    mu = sub.mean().values
    cov = sub.cov().values
    try:
        # Standard tangency portfolio: w ∝ Σ⁻¹ μ, clip to [0, 1], normalize.
        inv_cov = np.linalg.pinv(cov)
        raw = inv_cov @ mu
        raw = np.clip(raw, 0.0, None)  # long-only
        if raw.sum() <= 0:
            return _equal_weights(strategies)
        norm = raw / raw.sum()
        return dict(zip(strategies, norm.tolist()))
    except (np.linalg.LinAlgError, ValueError):
        return _equal_weights(strategies)


def marginal_diversification_benefit(
    returns: pd.DataFrame,
    book: list[str],
    candidate: str,
    scheme: str = "rp",
    vol_window: int = 90,
) -> float:
    """MDB = Sharpe(book ∪ {candidate}) − Sharpe(book) under the chosen weighting.

    scheme ∈ {"eq" (equal-weight), "rp" (risk-parity inverse-vol),
              "mv" (mean-var Markowitz, unstable at small N)}.

    Returns float in (-∞, +∞). Positive = candidate adds to portfolio Sharpe.
    """
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
        raise ValueError(f"unknown MDB scheme: {scheme}")

    return _sharpe(_portfolio_returns(returns, we)) - _sharpe(_portfolio_returns(returns, wb))


def mdb_robust_flag(
    returns: pd.DataFrame,
    book: list[str],
    candidate: str,
    eps: float = 0.0,
) -> bool:
    """True iff MDB > eps under all three schemes."""
    for scheme in ("eq", "rp", "mv"):
        if marginal_diversification_benefit(returns, book, candidate, scheme) <= eps:
            return False
    return True


def render_heatmap(
    corr: pd.DataFrame,
    output_path: Path,
    title: str = "Strategy correlation (daily log-returns, common window)",
) -> None:
    """Render a correlation heatmap PNG."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = len(corr.columns)
    fig, ax = plt.subplots(figsize=(max(6, n * 0.8), max(5, n * 0.7)))
    im = ax.imshow(corr.values, vmin=-1, vmax=1, cmap="RdBu_r", aspect="auto")
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticklabels(corr.columns)
    # Annotate cells.
    for i in range(n):
        for j in range(n):
            v = corr.values[i, j]
            color = "white" if abs(v) > 0.5 else "black"
            ax.text(j, i, f"{v:+.2f}", ha="center", va="center", color=color, fontsize=8)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, shrink=0.7)
    fig.tight_layout()
    fig.savefig(output_path, dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------------------
# CLI — print markdown table
# ---------------------------------------------------------------------------


def format_markdown_table(m: Layer5Metrics) -> str:
    """Render a Layer-5 sub-table for paste into a result card."""
    lines = [
        "### Layer 5 — Tail / Path shape",
        "",
        "| Metric | Value | Reading |",
        "|---|---:|---|",
        f"| Skew | {m.skew:+.2f} | {_skew_reading(m.skew)} |",
        f"| Excess kurtosis | {m.kurt_excess:+.2f} | {_kurt_reading(m.kurt_excess)} |",
        f"| Tail ratio (\\|P95\\|/\\|P5\\|) | {m.tail_ratio:.2f} | {_tail_reading(m.tail_ratio)} |",
        f"| CVaR-5% (daily) | {m.cvar_5_pct:+.2f}% | mean loss on worst 5% of days |",
        f"| Ulcer Index | {m.ulcer_index:.2f} | path-aware DD (lower = better) |",
        f"| Martin ratio | {m.martin_ratio:.2f} | CAGR per unit ulcer (higher = better) |",
        f"| Pain index | {m.pain_index:.2f} | mean abs drawdown |",
        "",
        f"_N_obs (daily): {m.n_obs}_",
    ]
    return "\n".join(lines)


def _skew_reading(s: float) -> str:
    if s > 0.5:
        return "right-tailed (rare big wins)"
    if s < -0.5:
        return "left-tailed (rare big losses)"
    return "near-symmetric"


def _kurt_reading(k: float) -> str:
    if k > 3:
        return "fat-tailed (Sharpe overstates)"
    if k < -1:
        return "thin-tailed"
    return "near-Gaussian"


def _tail_reading(t: float) -> str:
    if math.isnan(t):
        return "n/a (N < 20)"
    if t > 1.2:
        return "winners > losers in size"
    if t < 0.8:
        return "losers > winners in size"
    return "balanced"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    zip_path = Path(argv[1]).resolve()
    if not zip_path.exists():
        print(f"error: {zip_path} not found", file=sys.stderr)
        return 1
    m = compute_layer5_metrics(zip_path)
    print(format_markdown_table(m))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
