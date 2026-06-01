"""Panel rebalance backtest for SGX/IDX trend_vol.

Mechanics (deliberately simpler than feishu's competition backtester):
  - Daily target weights from `strategy.weights()`.
  - Execution at next bar's open (T+1 entry; standard retail-realistic).
  - All-NaN target rows = "hold prior positions" (regime-gate days).
  - Proportional transaction costs on turnover, applied on rebalance.
  - No short-selling, no leverage, no T+1 sell restriction.
  - Single currency per market — caller chooses universe and currency.

Returns a `BacktestResult` with the wallet curve (DatetimeIndex), the
realised holdings DataFrame, and per-day turnover series.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestResult:
    wallet: pd.Series         # portfolio value over time (date index)
    holdings: pd.DataFrame    # actual weight held end-of-day, per ticker
    turnover: pd.Series       # |Δw|.sum() per rebalance (fraction of NAV)
    n_rebalances: int


def backtest(
    target_weights: pd.DataFrame,
    close: pd.DataFrame,
    open_: pd.DataFrame | None = None,
    initial_capital: float = 100_000.0,
    cost_bps: float = 10.0,
) -> BacktestResult:
    """Run the panel backtest.

    Parameters
    ----------
    target_weights : (date × ticker) weights from `strategy.weights()`. Rows
                     summing to ~1 trigger a rebalance; all-NaN rows hold.
    close          : (date × ticker) closing prices, used for P&L marking.
    open_          : optional (date × ticker) opens. If provided, rebalance
                     fills are taken at next-day open (T+1). If None, fills
                     are at the same day's close.
    initial_capital: starting NAV.
    cost_bps       : round-trip cost in basis points of turnover. 10bps is
                     a reasonable SGX/IDX retail-broker assumption.

    Returns
    -------
    BacktestResult
    """
    target_weights = target_weights.reindex(close.index)
    if open_ is not None:
        open_ = open_.reindex(close.index, columns=close.columns)

    # Execution prices for rebalances
    exec_price = open_.shift(-1) if open_ is not None else close
    exec_price = exec_price.reindex(close.index, columns=close.columns)

    # Per-period simple returns from close-to-close on each ticker
    ret = close.pct_change().fillna(0.0)

    # Walk forward
    dates = close.index
    tickers = close.columns
    held = pd.Series(0.0, index=tickers)
    nav = initial_capital

    wallet = pd.Series(np.nan, index=dates)
    holdings_rows: list[pd.Series] = []
    turnover_rows: list[float] = []

    cost_rate = cost_bps / 10_000.0

    for i, d in enumerate(dates):
        # Mark current holdings to market using today's close return
        portfolio_ret = float((held * ret.loc[d]).sum())
        nav *= 1.0 + portfolio_ret

        # Rebalance decision: today's row of target_weights
        target = target_weights.loc[d]
        if target.isna().all():
            # Regime gate or pre-warmup; hold
            turnover_rows.append(0.0)
        else:
            new = target.fillna(0.0)
            # Cap at last available execution price (drop tickers with no
            # exec price tomorrow — can't fill them).
            if i + 1 < len(dates):
                tradable = exec_price.loc[d].notna()
                new = new.where(tradable, 0.0)
                renorm = new.sum()
                if renorm > 0:
                    new = new / renorm
                else:
                    new = pd.Series(0.0, index=tickers)
            else:
                # Last bar: don't rebalance (no future fill)
                new = held

            delta = (new - held).abs().sum()
            turnover_rows.append(float(delta))
            nav *= 1.0 - cost_rate * float(delta)
            held = new

        wallet.iloc[i] = nav
        holdings_rows.append(held.copy())

    holdings_df = pd.DataFrame(holdings_rows, index=dates)
    turnover_s = pd.Series(turnover_rows, index=dates, name="turnover")
    n_rebal = int((turnover_s > 0).sum())

    return BacktestResult(
        wallet=wallet,
        holdings=holdings_df,
        turnover=turnover_s,
        n_rebalances=n_rebal,
    )
