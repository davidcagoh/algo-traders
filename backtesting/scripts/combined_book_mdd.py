#!/usr/bin/env python3
"""
Combined-book MDD for the candidate book {T3, R∧T2} on the A1.5 common window.

Computes max-drawdown of the weighted-portfolio equity curve under each of the
three MDB weighting schemes (eq / rp / mv). Reuses loaders and weight helpers
from eval_layers.py so the formulas are identical to run_correlation_mdb.py.

Usage:
  ./freqtrade/.venv/bin/python scripts/combined_book_mdd.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from eval_layers import (
    _drawdown_series,
    _equal_weights,
    _mean_variance_weights,
    _portfolio_returns,
    _risk_parity_weights,
    build_returns_matrix,
)

REPO = Path(__file__).resolve().parent.parent
ZIP_DIR = REPO / "user_data" / "backtest_results"

BOOK_ZIPS: dict[str, Path] = {
    "T3":   ZIP_DIR / "a15_smaregime180_binance_common.zip",
    "R∧T2": ZIP_DIR / "a15_hmm_sma_slope_v2_multi_binance_common.zip",
}


def combined_mdd(returns: pd.DataFrame, weights: dict[str, float]) -> float:
    """MDD (negative pct) of equity curve built from weighted daily log-returns."""
    port_ret = _portfolio_returns(returns, weights)
    # daily log-returns → equity curve via cumulative exp
    equity = np.exp(port_ret.cumsum())
    dd = _drawdown_series(equity)
    return float(dd.min())


def main() -> None:
    returns = build_returns_matrix(BOOK_ZIPS)
    book = list(BOOK_ZIPS.keys())
    print(f"window: {returns.index.min().date()} → {returns.index.max().date()}  "
          f"({len(returns)} days)")

    w_eq = _equal_weights(book)
    w_rp = _risk_parity_weights(returns, book, vol_window=90)
    w_mv = _mean_variance_weights(returns, book)

    mdd_eq = combined_mdd(returns, w_eq)
    mdd_rp = combined_mdd(returns, w_rp)
    mdd_mv = combined_mdd(returns, w_mv)

    print(f"weights_eq: {w_eq}")
    print(f"weights_rp: {w_rp}")
    print(f"weights_mv: {w_mv}")
    print()
    print(f"book={{T3, R∧T2}}  MDD_eq={mdd_eq:.2f}%  MDD_rp={mdd_rp:.2f}%  MDD_mv={mdd_mv:.2f}%")
    print(f"K1 gate = 5.5%   verdict_rp = "
          f"{'PASS' if abs(mdd_rp) <= 5.5 else 'FAIL'}")


if __name__ == "__main__":
    main()
