#!/usr/bin/env python3
"""Plot signed mean-variance backtest weights, PnL, and rolling Sharpe."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/backtesting-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/backtesting-cache")

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from run_portfolio_baselines import ASSETS_DIR, RESULTS_DIR, UNIVERSE_JSON, load_daily_prices, load_universe
from run_portfolio_short_funding import load_daily_funding, metrics, simulate


def rolling_sharpe(returns: pd.Series, window: int) -> pd.Series:
    mean = returns.rolling(window).mean()
    std = returns.rolling(window).std()
    return mean / std.replace(0.0, np.nan) * np.sqrt(365.0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe-json", type=Path, default=UNIVERSE_JSON)
    parser.add_argument("--lookback", type=int, default=60)
    parser.add_argument("--rebalance-days", type=int, default=7)
    parser.add_argument("--fee", type=float, default=0.00035)
    parser.add_argument("--cap", type=float, default=0.20)
    parser.add_argument("--gross-limit", type=float, default=1.0)
    parser.add_argument("--mean-shrink", type=float, default=0.50)
    parser.add_argument("--risk-aversion", type=float, default=1.0)
    parser.add_argument("--turnover-penalty", type=float, default=0.05)
    parser.add_argument("--rolling-window", type=int, default=30)
    args = parser.parse_args()

    coins = load_universe(args.universe_json)
    prices = load_daily_prices(coins)
    price_returns = prices.pct_change().dropna()
    funding = load_daily_funding(coins, price_returns.index)

    returns, weights, costs, funding_pnl = simulate(
        price_returns,
        funding,
        "shrunk_mean_variance_signed",
        args.lookback,
        args.rebalance_days,
        args.fee,
        args.cap,
        args.gross_limit,
        args.mean_shrink,
        args.risk_aversion,
        args.turnover_penalty,
    )
    equity = (1.0 + returns).cumprod()
    pnl = equity - 1.0
    rsharpe = rolling_sharpe(returns, args.rolling_window)
    row = metrics(returns, weights, costs, funding_pnl, args.rebalance_days)

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_png = ASSETS_DIR / "portfolio_signed_mv_backtest_diagnostics_current.png"
    out_csv = RESULTS_DIR / "portfolio_signed_mv_backtest_diagnostics_current.csv"
    out_json = RESULTS_DIR / "portfolio_signed_mv_backtest_diagnostics_current.json"

    diagnostics = pd.concat(
        [
            returns.rename("return"),
            equity.rename("equity"),
            pnl.rename("pnl"),
            rsharpe.rename(f"rolling_sharpe_{args.rolling_window}d"),
            costs.rename("fee_drag"),
            funding_pnl.rename("funding_pnl"),
            weights.add_prefix("weight_"),
        ],
        axis=1,
    )
    diagnostics.to_csv(out_csv, index_label="date")

    payload = {
        "universe": coins,
        "window": {"start": str(returns.index.min()), "end": str(returns.index.max())},
        "method": {
            "portfolio": "shrunk_mean_variance_signed",
            "lookback_days": args.lookback,
            "rebalance_days": args.rebalance_days,
            "fee": args.fee,
            "max_abs_weight": args.cap,
            "gross_limit": args.gross_limit,
            "mean_shrink": args.mean_shrink,
            "risk_aversion": args.risk_aversion,
            "turnover_penalty": args.turnover_penalty,
            "rolling_sharpe_days": args.rolling_window,
        },
        "metrics": row,
    }
    out_json.write_text(json.dumps(payload, indent=2))

    colors = plt.get_cmap("tab10").colors
    fig, axes = plt.subplots(
        3,
        1,
        figsize=(15, 10.5),
        sharex=True,
        gridspec_kw={"height_ratios": [2.1, 1.2, 1.2]},
        constrained_layout=False,
    )
    fig.suptitle("Signed Mean-Variance Backtest Diagnostics", fontsize=16, fontweight="bold", y=0.985)

    ax = axes[0]
    for idx, coin in enumerate(coins):
        ax.plot(weights.index, weights[coin] * 100.0, label=coin, linewidth=1.6, color=colors[idx % len(colors)])
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title("Daily Actual Weights")
    ax.set_ylabel("Weight (%)")
    ax.grid(True, alpha=0.25)
    ax.legend(ncol=9, loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False, fontsize=9)

    ax = axes[1]
    ax.plot(pnl.index, pnl * 100.0, color="#1f77b4", linewidth=2.0)
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.fill_between(pnl.index, 0.0, pnl * 100.0, where=pnl >= 0, color="#2ca02c", alpha=0.15)
    ax.fill_between(pnl.index, 0.0, pnl * 100.0, where=pnl < 0, color="#d62728", alpha=0.15)
    ax.set_title(f"PnL Over Time: final {row['total_return_pct']:.2f}%")
    ax.set_ylabel("PnL (%)")
    ax.grid(True, alpha=0.25)

    ax = axes[2]
    ax.plot(rsharpe.index, rsharpe, color="#9467bd", linewidth=2.0)
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title(f"{args.rolling_window}D Rolling Sharpe, Annualized")
    ax.set_ylabel("Sharpe")
    ax.grid(True, alpha=0.25)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.set_xlabel("Date")

    subtitle = (
        f"{returns.index.min().date()} -> {returns.index.max().date()} | "
        f"Sharpe {row['sharpe']:.2f} | Calmar {row['calmar']:.2f} | "
        f"MDD {row['max_drawdown_pct']:.2f}% | fees {row['total_fee_drag_pct']:.2f}% | "
        f"funding {row['total_funding_pnl_pct']:.2f}%"
    )
    fig.text(0.5, 0.955, subtitle, ha="center", va="top", fontsize=10, color="#444444")
    fig.subplots_adjust(top=0.90, bottom=0.07, hspace=0.62)
    fig.savefig(out_png, dpi=180)
    plt.close(fig)

    print(f"wrote {out_png}")
    print(f"wrote {out_csv}")
    print(f"wrote {out_json}")
    print(
        f"return={row['total_return_pct']:.2f}% sharpe={row['sharpe']:.2f} "
        f"calmar={row['calmar']:.2f} mdd={row['max_drawdown_pct']:.2f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
