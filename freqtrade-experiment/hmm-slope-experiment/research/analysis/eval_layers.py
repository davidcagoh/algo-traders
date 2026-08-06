#!/usr/bin/env python3
"""
Layer-5 evaluation metrics (tail shape + path-aware drawdown) for a single
backtest ZIP, plus a correlation-heatmap renderer used by
`run_correlation_mdb.py`.

Migrated 2026-08-06 onto `evaluation.layers` / `evaluation.correlation_mdb`
instead of a locally duplicated copy of the same formulas (skew, excess
kurtosis, tail ratio, CVaR-5%, Ulcer Index, Martin ratio, Pain index, and
the equal/risk-parity/mean-variance weighting schemes + MDB). See
`evaluation-framework/evaluation/layers.py` and `.../correlation_mdb.py` —
this file is now just the ZIP-loading CLI adapter and the plotting helper
those two modules don't own.

Usage
-----
    ./.venv/bin/python analysis/eval_layers.py <zip_path>

Prints a markdown table suitable for paste into analysis/reports/*.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# Make the repository-level reusable package available when this script is
# launched directly from the research directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "evaluation-framework"))
from evaluation.backtest import build_returns_matrix, load_trade_returns, load_wallet_curve
from evaluation.correlation_mdb import (
    correlation_matrix,
    equal_weights,
    marginal_diversification_benefit,
    mdb_robust_flag,
    mean_variance_weights,
    portfolio_returns,
    risk_parity_weights,
)
from evaluation.layers import CRYPTO_ANNUAL, compute, format_markdown_table

# Re-exported for `combined_book_mdd.py` and `run_correlation_mdb.py`, which
# import these names from this module.
__all__ = [
    "build_returns_matrix",
    "correlation_matrix",
    "equal_weights",
    "marginal_diversification_benefit",
    "mdb_robust_flag",
    "mean_variance_weights",
    "portfolio_returns",
    "risk_parity_weights",
    "render_heatmap",
]


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


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    zip_path = Path(argv[1]).resolve()
    if not zip_path.exists():
        print(f"error: {zip_path} not found", file=sys.stderr)
        return 1
    wallet = load_wallet_curve(zip_path)
    trade_returns = load_trade_returns(zip_path)
    m = compute(wallet, trade_returns, annualisation=CRYPTO_ANNUAL)
    print(format_markdown_table(m, title="Layer 1-5 metrics"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
