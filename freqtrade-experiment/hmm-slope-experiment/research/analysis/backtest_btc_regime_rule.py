#!/usr/bin/env python3
"""Backtest a naive BTC regime rule from inferred DP regime labels.

Rule:
- long green regimes: bull, volatile_bull, recovery
- short orange regime: drawdown
- flat otherwise

The signal is shifted by one daily bar. A regime inferred at day t close is used
for exposure from t close to t+1 close.
"""
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


REPO = Path(__file__).resolve().parent.parent
DEFAULT_REGIMES = REPO / "analysis/reports/btc_dp_regimes.csv"
DEFAULT_FUNDING = REPO / "data/binance/futures/BTC_USDT_USDT-8h-funding_rate.feather"
DEFAULT_CSV = REPO / "analysis/reports/btc_dp_regime_rule_backtest.csv"
DEFAULT_JSON = REPO / "analysis/reports/btc_dp_regime_rule_backtest.json"
DEFAULT_CHART = REPO / "analysis/reports/btc_dp_regime_rule_backtest.png"

LONG_REGIMES = {"bull", "volatile_bull", "recovery"}
SHORT_REGIMES = {"drawdown"}
FEE = 0.00035
TRADING_DAYS = 365.0


def as_utc_ns(values: pd.Series | pd.DatetimeIndex) -> pd.Series | pd.DatetimeIndex:
    converted = pd.to_datetime(values, utc=True)
    if isinstance(converted, pd.Series):
        return converted.dt.as_unit("ns")
    return converted.as_unit("ns")


def load_daily_funding(path: Path, index: pd.DatetimeIndex) -> pd.Series:
    if not path.exists():
        return pd.Series(0.0, index=index, name="funding")
    df = pd.read_feather(path)
    df["date"] = as_utc_ns(df["date"])
    daily = df.set_index("date")["open"].astype(float).resample("1D").sum()
    daily.index = as_utc_ns(daily.index)
    return daily.reindex(index).fillna(0.0).rename("funding")


def max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1.0).min())


def ulcer_index(equity: pd.Series) -> float:
    dd = equity / equity.cummax() - 1.0
    return float(np.sqrt(np.mean(np.square(np.minimum(dd, 0.0)))))


def metrics(returns: pd.Series, equity: pd.Series, exposure: pd.Series) -> dict:
    returns = returns.dropna()
    if returns.empty:
        return {}
    total = float(equity.iloc[-1] - 1.0)
    years = len(returns) / TRADING_DAYS
    cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 else 0.0
    vol = float(returns.std() * np.sqrt(TRADING_DAYS))
    sharpe = float(returns.mean() / returns.std() * np.sqrt(TRADING_DAYS)) if returns.std() > 0 else 0.0
    mdd = max_drawdown(equity)
    calmar = float(cagr / abs(mdd)) if mdd < 0 else float("inf")
    ulcer = ulcer_index(equity)
    martin = float(cagr / ulcer) if ulcer > 0 else float("inf")
    return {
        "total_return_pct": total * 100.0,
        "cagr_pct": cagr * 100.0,
        "volatility_pct": vol * 100.0,
        "sharpe": sharpe,
        "max_drawdown_pct": mdd * 100.0,
        "calmar": calmar,
        "ulcer_pct": ulcer * 100.0,
        "martin": martin,
        "days": int(len(returns)),
        "active_days": int((exposure != 0).sum()),
        "long_days": int((exposure > 0).sum()),
        "short_days": int((exposure < 0).sum()),
        "flat_days": int((exposure == 0).sum()),
        "avg_abs_exposure": float(exposure.abs().mean()),
    }


def build_backtest(
    regimes_path: Path,
    funding_path: Path,
    signal_column: str,
) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(regimes_path, parse_dates=["date"]).sort_values("date")
    df["date"] = as_utc_ns(df["date"])
    df = df.set_index("date")
    if signal_column not in df.columns:
        raise ValueError(f"{signal_column} not found in {regimes_path}")
    funding = load_daily_funding(funding_path, df.index)

    df["price_return"] = df["close"].pct_change().fillna(0.0)
    signal = pd.Series(0.0, index=df.index)
    signal.loc[df[signal_column].isin(LONG_REGIMES)] = 1.0
    signal.loc[df[signal_column].isin(SHORT_REGIMES)] = -1.0

    # Shift one bar to avoid trading the same close used to infer the label.
    df["signal_regime"] = df[signal_column]
    df["signal"] = signal
    df["position"] = signal.shift(1).fillna(0.0)
    df["turnover"] = df["position"].diff().abs().fillna(df["position"].abs())
    df["fee_return"] = -FEE * df["turnover"]
    df["funding"] = funding
    df["funding_return"] = -df["position"] * df["funding"]
    df["strategy_return_gross"] = df["position"] * df["price_return"]
    df["strategy_return"] = (
        df["strategy_return_gross"] + df["funding_return"] + df["fee_return"]
    )
    df["strategy_equity"] = (1.0 + df["strategy_return"]).cumprod()
    df["buy_hold_equity"] = (1.0 + df["price_return"]).cumprod()
    df["short_hold_equity"] = (1.0 - df["price_return"] + df["funding"]).cumprod()
    df["drawdown"] = df["strategy_equity"] / df["strategy_equity"].cummax() - 1.0

    trade_count = int((df["turnover"] > 0).sum())
    summary = {
        "rule": {
            "long_regimes": sorted(LONG_REGIMES),
            "short_regimes": sorted(SHORT_REGIMES),
            "flat_otherwise": True,
            "signal_lag": "1 daily bar",
            "signal_column": signal_column,
            "fee_per_turnover": FEE,
            "funding": "daily sum; long pays positive funding, short receives positive funding",
        },
        "window": {
            "start": df.index.min().date().isoformat(),
            "end": df.index.max().date().isoformat(),
        },
        "strategy": metrics(df["strategy_return"], df["strategy_equity"], df["position"]),
        "buy_and_hold": metrics(df["price_return"], df["buy_hold_equity"], pd.Series(1.0, index=df.index)),
        "trade_count": trade_count,
        "turnover": float(df["turnover"].sum()),
        "fee_drag_pct": float(df["fee_return"].sum() * 100.0),
        "funding_pnl_pct": float(df["funding_return"].sum() * 100.0),
        "gross_price_pnl_pct": float(df["strategy_return_gross"].sum() * 100.0),
    }
    return df, summary


def plot(df: pd.DataFrame, summary: dict, output: Path) -> None:
    fig, axes = plt.subplots(
        3,
        1,
        figsize=(15, 10),
        sharex=True,
        gridspec_kw={"height_ratios": [1.7, 1.0, 0.8]},
        constrained_layout=True,
    )
    fig.suptitle("Naive BTC Regime Rule: Long Green, Short Orange", fontsize=16, fontweight="bold")

    ax = axes[0]
    ax.plot(df.index, (df["strategy_equity"] - 1.0) * 100.0, label="Regime rule", color="#1f77b4", linewidth=2.0)
    ax.plot(df.index, (df["buy_hold_equity"] - 1.0) * 100.0, label="BTC buy/hold", color="#111111", linewidth=1.3, alpha=0.75)
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title("Equity")
    ax.set_ylabel("Return (%)")
    ax.legend(frameon=False, loc="upper left")
    ax.grid(True, alpha=0.25)

    ax = axes[1]
    ax.fill_between(df.index, 0, df["position"], where=df["position"] > 0, color="#2ca02c", alpha=0.45, step="post", label="Long")
    ax.fill_between(df.index, 0, df["position"], where=df["position"] < 0, color="#ff7f0e", alpha=0.45, step="post", label="Short")
    ax.plot(df.index, df["position"], color="#333333", linewidth=0.8, drawstyle="steps-post")
    ax.set_ylim(-1.2, 1.2)
    ax.set_title("Lagged Position")
    ax.set_ylabel("Exposure")
    ax.legend(frameon=False, loc="upper left", ncol=2)
    ax.grid(True, alpha=0.25)

    ax = axes[2]
    ax.plot(df.index, df["drawdown"] * 100.0, color="#d62728", linewidth=1.3)
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title("Strategy Drawdown")
    ax.set_ylabel("Drawdown (%)")
    ax.grid(True, alpha=0.25)
    axes[-1].xaxis.set_major_locator(mdates.YearLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    text = (
        f"Return {summary['strategy']['total_return_pct']:.1f}% | "
        f"Sharpe {summary['strategy']['sharpe']:.2f} | "
        f"Calmar {summary['strategy']['calmar']:.2f} | "
        f"MDD {summary['strategy']['max_drawdown_pct']:.1f}%"
    )
    axes[0].text(
        0.99,
        0.03,
        text,
        transform=axes[0].transAxes,
        ha="right",
        va="bottom",
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.82, "edgecolor": "#dddddd"},
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regimes", type=Path, default=DEFAULT_REGIMES)
    parser.add_argument("--funding", type=Path, default=DEFAULT_FUNDING)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-chart", type=Path, default=DEFAULT_CHART)
    parser.add_argument(
        "--signal-column",
        default="regime_raw",
        help="Column used for trading labels. Use regime_raw for leak-free labels; "
        "regime is chart-smoothed and can use future segment information.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df, summary = build_backtest(args.regimes, args.funding, args.signal_column)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.reset_index().to_csv(args.output_csv, index=False)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    plot(df, summary, args.output_chart)

    print(f"wrote {args.output_csv}")
    print(f"wrote {args.output_json}")
    print(f"wrote {args.output_chart}")
    print(json.dumps(summary["strategy"], indent=2))


if __name__ == "__main__":
    main()
