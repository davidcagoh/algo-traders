#!/usr/bin/env python3
"""
Run MeanVariancePortfolio backtests with and without transaction costs.

Writes a comparison table to stdout and wiki/results/mean_variance_hl_universe.json.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FT = REPO / "freqtrade" / ".venv" / "bin" / "freqtrade"
CONFIG = REPO / "user_data" / "config_hl_mv_universe.json"
STRATEGY = "MeanVariancePortfolio"
TIMEFRAME = "1h"
TIMERANGE = "20251110-20260601"
FEE_TAKER = 0.00035
RESULT_JSON = REPO / "wiki" / "results" / "mean_variance_hl_universe.json"

PAIR_ARGS = [
    "BTC/USDC:USDC",
    "HYPE/USDC:USDC",
    "PAXG/USDC:USDC",
    "TRX/USDC:USDC",
    "WLFI/USDC:USDC",
    "VVV/USDC:USDC",
    "TON/USDC:USDC",
    "ZRO/USDC:USDC",
    "XPL/USDC:USDC",
]


def _parse_backtest_report(text: str) -> dict[str, float | int]:
    metrics: dict[str, float | int] = {}
    patterns = {
        "total_profit_pct": r"Total profit %\s*\|\s*([-\d.]+)%",
        "cagr_pct": r"CAGR %\s*\|\s*([-\d.]+)%",
        "sharpe": r"Sharpe\s*\|\s*([-\d.]+)",
        "sortino": r"Sortino\s*\|\s*([-\d.]+)",
        "calmar": r"Calmar\s*\|\s*([-\d.]+)",
        "mdd_pct": r"Max % of account underwater\s*\|\s*([-\d.]+)%",
        "trades": r"Total/Daily Avg Trades\s*\|\s*(\d+)",
        "profit_usdc": r"Absolute profit\s*\|\s*([-\d.]+) USDC",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text)
        if m:
            val = m.group(1)
            metrics[key] = int(val) if key == "trades" else float(val)
    return metrics


def run_backtest(fee: float, label: str) -> tuple[dict, str]:
    cmd = [
        str(FT),
        "backtesting",
        "--userdir",
        str(REPO / "user_data"),
        "-c",
        str(CONFIG),
        "--datadir",
        str(REPO / "user_data" / "data" / "hyperliquid"),
        "--data-format-ohlcv",
        "feather",
        "-s",
        STRATEGY,
        "-i",
        TIMEFRAME,
        "--timerange",
        TIMERANGE,
        "--fee",
        str(fee),
        "--eps",
        "--max-open-trades",
        "9",
        "--cache",
        "none",
    ]
    for p in PAIR_ARGS:
        cmd.extend(["-p", p])

    print(f"\n=== {label} (fee={fee}) ===\n", flush=True)
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    print(out)
    if proc.returncode != 0:
        raise RuntimeError(f"Backtest failed ({label}): exit {proc.returncode}")
    return _parse_backtest_report(out), out


def main() -> int:
    if not FT.exists():
        print(f"freqtrade not found at {FT}", file=sys.stderr)
        return 1

    pre, _ = run_backtest(0.0, "Pre-cost (zero fee)")
    post, _ = run_backtest(FEE_TAKER, "Post-cost (HL taker 0.035%/side)")

    payload = {
        "strategy": STRATEGY,
        "universe": [
            "BTC",
            "HYPE",
            "PAXG",
            "TRX",
            "WLFI",
            "VVV",
            "TON",
            "ZRO",
            "XPL",
        ],
        "timerange": TIMERANGE,
        "timeframe": TIMEFRAME,
        "fee_taker_per_side": FEE_TAKER,
        "pre_cost": pre,
        "post_cost": post,
        "cost_drag_pct": None,
    }
    if pre.get("total_profit_pct") is not None and post.get("total_profit_pct") is not None:
        payload["cost_drag_pct"] = round(
            pre["total_profit_pct"] - post["total_profit_pct"], 4
        )

    RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULT_JSON.write_text(json.dumps(payload, indent=2) + "\n")

    print("\n=== Pre vs post transaction costs ===\n")
    rows = [
        ("Total profit %", "total_profit_pct", "%"),
        ("CAGR %", "cagr_pct", "%"),
        ("Sharpe", "sharpe", ""),
        ("Calmar", "calmar", ""),
        ("Max drawdown %", "mdd_pct", "%"),
        ("Trades", "trades", ""),
        ("Profit USDC", "profit_usdc", " USDC"),
    ]
    for label, key, suffix in rows:
        pre_v = pre.get(key, "—")
        post_v = post.get(key, "—")
        print(f"{label:18}  pre: {pre_v}{suffix}   post: {post_v}{suffix}")
    if payload["cost_drag_pct"] is not None:
        print(f"\nCost drag (return): {payload['cost_drag_pct']:.2f} pp")
    print(f"\nJSON: {RESULT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
