#!/usr/bin/env python3
"""
Sweep shrunk mean-variance parameters on the selected Hyperliquid universe.

Writes:
  analysis/results/portfolio_mv_param_sweep_hl_1h_current.json
  analysis/results/portfolio_mv_param_sweep_hl_1h_current.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from run_portfolio_baselines import (
    RESULTS_DIR,
    UNIVERSE_JSON,
    load_daily_prices,
    load_universe,
    metrics,
    simulate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--universe-json", type=Path, default=UNIVERSE_JSON)
    parser.add_argument("--lookback", type=int, default=60)
    parser.add_argument("--rebalance-days", type=int, default=7)
    parser.add_argument("--fee", type=float, default=0.00035)
    parser.add_argument("--cap", type=float, default=0.20)
    parser.add_argument("--turnover-penalty", type=float, default=0.05)
    parser.add_argument(
        "--mean-shrink",
        nargs="+",
        type=float,
        default=[0.0, 0.02, 0.05, 0.10, 0.20, 0.50, 1.00],
    )
    parser.add_argument(
        "--risk-aversion",
        nargs="+",
        type=float,
        default=[1.0, 3.0, 10.0],
    )
    args = parser.parse_args()

    coins = load_universe(args.universe_json)
    prices = load_daily_prices(coins)
    returns = prices.pct_change().dropna()

    rows = []
    for risk_aversion in args.risk_aversion:
        for mean_shrink in args.mean_shrink:
            port_rets, weights, costs = simulate(
                returns,
                method="shrunk_mean_variance",
                lookback=args.lookback,
                rebalance_days=args.rebalance_days,
                fee=args.fee,
                cap=args.cap,
                mean_shrink=mean_shrink,
                risk_aversion=risk_aversion,
                turnover_penalty=args.turnover_penalty,
            )
            row = metrics(port_rets, weights, costs, args.rebalance_days)
            row["mean_shrink"] = mean_shrink
            row["risk_aversion"] = risk_aversion
            rows.append(row)

    rows = sorted(
        rows,
        key=lambda row: (
            row["sharpe"] if np.isfinite(row["sharpe"]) else -np.inf,
            row["calmar"] if np.isfinite(row["calmar"]) else -np.inf,
        ),
        reverse=True,
    )
    payload = {
        "universe": coins,
        "method": {
            "return_frequency": "daily close-to-close from 1h OHLCV",
            "lookback_days": args.lookback,
            "rebalance_days": args.rebalance_days,
            "fee": args.fee,
            "max_weight": args.cap,
            "turnover_penalty": args.turnover_penalty,
            "mean_shrink_values": args.mean_shrink,
            "risk_aversion_values": args.risk_aversion,
            "funding": "not included",
        },
        "window": {
            "price_start": str(prices.index.min()),
            "price_end": str(prices.index.max()),
            "active_start": str(returns.index[args.lookback]),
            "active_end": str(returns.index.max()),
        },
        "rows": rows,
    }

    lines = [
        "# Mean-Variance Parameter Sweep - Hyperliquid Current Universe",
        "",
        f"Universe: `{', '.join(coins)}`",
        "",
        f"Window: `{payload['window']['active_start']}` -> `{payload['window']['active_end']}`",
        "",
        "| Rank | mean_shrink | risk_aversion | Total Return | CAGR | Ann Vol | Sharpe | MDD | Calmar | Avg Exposure | Eff Assets | Turnover/Rebal |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for idx, row in enumerate(rows, start=1):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(idx),
                    f"{row['mean_shrink']:.2f}",
                    f"{row['risk_aversion']:.2f}",
                    f"{row['total_return_pct']:.2f}%",
                    f"{row['cagr_pct']:.2f}%",
                    f"{row['ann_vol_pct']:.2f}%",
                    f"{row['sharpe']:.2f}",
                    f"{row['max_drawdown_pct']:.2f}%",
                    f"{row['calmar']:.2f}",
                    f"{row['avg_exposure']:.2f}",
                    f"{row['avg_effective_assets']:.2f}",
                    f"{row['avg_turnover_per_rebalance']:.2f}",
                ]
            )
            + " |"
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = RESULTS_DIR / "portfolio_mv_param_sweep_hl_1h_current.json"
    out_md = RESULTS_DIR / "portfolio_mv_param_sweep_hl_1h_current.md"
    out_json.write_text(json.dumps(payload, indent=2))
    out_md.write_text("\n".join(lines) + "\n")

    print("\n".join(lines[: min(len(lines), 18)]))
    print(f"\nwrote {out_json}")
    print(f"wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
