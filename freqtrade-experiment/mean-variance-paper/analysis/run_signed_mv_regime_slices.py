#!/usr/bin/env python3
"""Run signed mean-variance portfolio by calendar/regime slices."""
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

from run_portfolio_baselines import ASSETS_DIR, RESULTS_DIR
from run_portfolio_short_funding import metrics, simulate


REPO = Path(__file__).resolve().parent.parent


def as_utc_ns(values: pd.Series | pd.DatetimeIndex) -> pd.Series | pd.DatetimeIndex:
    converted = pd.to_datetime(values, utc=True)
    if isinstance(converted, pd.Series):
        return converted.dt.as_unit("ns")
    return converted.as_unit("ns")


def exchange_paths(exchange: str) -> tuple[Path, Path, str]:
    quote = "USDT_USDT" if exchange == "binance" else "USDC_USDC"
    data_dir = REPO.parent / "hmm-slope-experiment" / "research" / "data" / exchange / "futures"
    funding_dir = REPO.parent / "hmm-slope-experiment" / "research" / "data" / exchange / "funding"
    return data_dir, funding_dir, quote


def load_daily_prices_1d(coins: list[str], data_dir: Path, quote: str) -> pd.DataFrame:
    series = []
    for coin in coins:
        path = data_dir / f"{coin}_{quote}-1d-futures.feather"
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_feather(path)
        df["date"] = as_utc_ns(df["date"])
        df = df.sort_values("date").drop_duplicates("date")
        series.append(df.set_index("date")["close"].astype(float).rename(coin))
    return pd.concat(series, axis=1).dropna(how="any")


def load_daily_funding(
    coins: list[str],
    index: pd.DatetimeIndex,
    data_dir: Path,
    funding_dir: Path,
    quote: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    series = []
    observed = []
    for coin in coins:
        parquet = funding_dir / f"{coin}-funding.parquet"
        feather_candidates = sorted(data_dir.glob(f"{coin}_{quote}-*h-funding_rate.feather"))
        if parquet.exists():
            df = pd.read_parquet(parquet)
            df["time"] = as_utc_ns(df["time"])
            daily = df.set_index("time")["funding_rate"].astype(float).resample("1D").sum()
        elif feather_candidates:
            feather = feather_candidates[0]
            df = pd.read_feather(feather)
            df["date"] = as_utc_ns(df["date"])
            daily = df.set_index("date")["open"].astype(float).resample("1D").sum()
        else:
            daily = pd.Series(dtype=float)
        daily.index = as_utc_ns(daily.index)
        aligned = daily.reindex(index)
        series.append(aligned.fillna(0.0).rename(coin))
        observed.append(aligned.notna().astype(float).rename(coin))
    funding = pd.concat(series, axis=1).fillna(0.0)
    funding.index = as_utc_ns(funding.index)
    coverage = pd.concat(observed, axis=1).fillna(0.0)
    coverage.index = as_utc_ns(coverage.index)
    return funding, coverage


def slice_metrics(
    returns: pd.Series,
    weights: pd.DataFrame,
    costs: pd.Series,
    funding_pnl: pd.Series,
    rebalance_days: int,
) -> dict:
    if len(returns) < 30:
        return {}
    return metrics(returns, weights, costs, funding_pnl, rebalance_days)


def market_return(price_returns: pd.DataFrame, dates: pd.DatetimeIndex, method: str) -> float:
    subset = price_returns.reindex(dates).dropna(how="any")
    if subset.empty:
        return float("nan")
    if method == "btc":
        rets = subset["BTC"]
    elif method == "equal_weight":
        rets = subset.mean(axis=1)
    else:
        raise ValueError(method)
    return float(((1.0 + rets).prod() - 1.0) * 100.0)


def regime_label(btc_return_pct: float) -> str:
    if btc_return_pct >= 50:
        return "bull"
    if btc_return_pct <= -30:
        return "bear"
    if btc_return_pct >= 10:
        return "recovery"
    if btc_return_pct <= -10:
        return "drawdown"
    return "chop"


def pct(value: float) -> str:
    if not np.isfinite(value):
        return "n/a"
    return f"{value:.2f}%"


def rolling_sharpe(returns: pd.Series, window: int) -> pd.Series:
    mean = returns.rolling(window).mean()
    std = returns.rolling(window).std()
    return mean / std.replace(0.0, np.nan) * np.sqrt(365.0)


def markdown(payload: dict) -> str:
    exchange = payload["method"]["venue"]
    if exchange == "binance":
        data_note = "Uses Binance USDT-margined perp daily candles and funding on the older 5-coin major proxy universe."
    else:
        data_note = "Uses Hyperliquid daily candles on the older 5-coin major proxy universe. Local Hyperliquid funding coverage starts in May 2023, so earlier funding is zero-filled."
    lines = [
        "# Signed Mean-Variance Regime Slices",
        "",
        f"Universe: `{', '.join(payload['universe'])}`",
        "",
        f"Window: `{payload['window']['start']}` -> `{payload['window']['end']}`",
        "",
        "Same deployed signed-MV parameters: 60d lookback, weekly rebalance, 20% per-token cap, 100% gross cap, 0.035% turnover fee, `mean_shrink=0.50`, `risk_aversion=1.0`, `turnover_penalty=0.05`.",
        "",
        f"Data note: {data_note}",
        "",
        "| Period | Regime | Days | Signed MV Return | Sharpe | MDD | Calmar | BTC Return | Equal Weight Return | Funding Coverage |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["slices"]:
        lines.append(
            f"| {row['period']} | {row['regime']} | {row['days']} | "
            f"{pct(row['signed_mv_return_pct'])} | {row['signed_mv_sharpe']:.2f} | "
            f"{pct(row['signed_mv_mdd_pct'])} | {row['signed_mv_calmar']:.2f} | "
            f"{pct(row['btc_return_pct'])} | {pct(row['equal_weight_return_pct'])} | "
            f"{row['funding_coverage_pct']:.1f}% |"
        )
    return "\n".join(lines) + "\n"


def plot(payload: dict, equity: pd.Series, slices_df: pd.DataFrame, out_path: Path) -> None:
    fig, axes = plt.subplots(
        3,
        1,
        figsize=(14, 10),
        gridspec_kw={"height_ratios": [1.4, 1.0, 1.0]},
        constrained_layout=True,
    )
    fig.suptitle("Signed MV Performance by Regime Slice", fontsize=16, fontweight="bold")

    ax = axes[0]
    ax.plot(equity.index, (equity - 1.0) * 100.0, color="#1f77b4", linewidth=2.0)
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    for _, row in slices_df.iterrows():
        color = {"bull": "#2ca02c", "bear": "#d62728", "recovery": "#17becf", "drawdown": "#ff7f0e", "chop": "#7f7f7f"}[row["regime"]]
        ax.axvspan(pd.Timestamp(row["start"]), pd.Timestamp(row["end"]), color=color, alpha=0.08)
    ax.set_title("Full Backtest PnL With Regime Shading")
    ax.set_ylabel("PnL (%)")
    ax.grid(True, alpha=0.25)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    ax = axes[1]
    x = np.arange(len(slices_df))
    width = 0.25
    ax.bar(x - width, slices_df["signed_mv_return_pct"], width, label="Signed MV", color="#1f77b4")
    ax.bar(x, slices_df["btc_return_pct"], width, label="BTC", color="#ff7f0e")
    ax.bar(x + width, slices_df["equal_weight_return_pct"], width, label="Equal weight", color="#2ca02c")
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title("Return by Period")
    ax.set_ylabel("Return (%)")
    ax.set_xticks(x, slices_df["period"])
    ax.legend(frameon=False, ncol=3)
    ax.grid(True, axis="y", alpha=0.25)

    ax = axes[2]
    ax.bar(x - width / 2, slices_df["signed_mv_sharpe"], width, label="Sharpe", color="#9467bd")
    ax.bar(x + width / 2, slices_df["signed_mv_mdd_pct"], width, label="MDD %", color="#d62728")
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title("Signed MV Risk by Period")
    ax.set_ylabel("Metric")
    ax.set_xticks(x, slices_df["period"])
    ax.legend(frameon=False, ncol=2)
    ax.grid(True, axis="y", alpha=0.25)

    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_diagnostics(
    returns: pd.Series,
    weights: pd.DataFrame,
    slices_df: pd.DataFrame,
    rolling_window: int,
    out_path: Path,
) -> None:
    equity = (1.0 + returns).cumprod()
    pnl = equity - 1.0
    rsharpe = rolling_sharpe(returns, rolling_window)

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(15, 11),
        sharex=True,
        gridspec_kw={"height_ratios": [1.8, 1.2, 1.2]},
        constrained_layout=True,
    )
    fig.suptitle("Signed MV Binance 5-Coin Diagnostics", fontsize=16, fontweight="bold")

    colors = plt.get_cmap("tab10").colors
    ax = axes[0]
    for idx, coin in enumerate(weights.columns):
        ax.plot(weights.index, weights[coin] * 100.0, label=coin, linewidth=1.3, color=colors[idx % len(colors)])
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title("Daily Actual Weights")
    ax.set_ylabel("Weight (%)")
    ax.legend(frameon=False, ncol=len(weights.columns), loc="upper left")
    ax.grid(True, alpha=0.25)

    ax = axes[1]
    ax.plot(pnl.index, pnl * 100.0, color="#1f77b4", linewidth=2.0)
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    for _, row in slices_df.iterrows():
        color = {"bull": "#2ca02c", "bear": "#d62728", "recovery": "#17becf", "drawdown": "#ff7f0e", "chop": "#7f7f7f"}[row["regime"]]
        ax.axvspan(pd.Timestamp(row["start"]), pd.Timestamp(row["end"]), color=color, alpha=0.08)
    ax.set_title("PnL Over Time")
    ax.set_ylabel("PnL (%)")
    ax.grid(True, alpha=0.25)

    ax = axes[2]
    ax.plot(rsharpe.index, rsharpe, color="#9467bd", linewidth=1.8)
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title(f"{rolling_window}D Rolling Sharpe, Annualized")
    ax.set_ylabel("Sharpe")
    ax.set_xlabel("Date")
    ax.grid(True, alpha=0.25)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exchange", choices=["binance", "hyperliquid"], default="binance")
    parser.add_argument("--coins", nargs="+", default=["BTC", "ETH", "SOL", "AVAX", "DOGE"])
    parser.add_argument("--lookback", type=int, default=60)
    parser.add_argument("--rebalance-days", type=int, default=7)
    parser.add_argument("--fee", type=float, default=0.00035)
    parser.add_argument("--cap", type=float, default=0.20)
    parser.add_argument("--gross-limit", type=float, default=1.0)
    parser.add_argument("--mean-shrink", type=float, default=0.50)
    parser.add_argument("--risk-aversion", type=float, default=1.0)
    parser.add_argument("--turnover-penalty", type=float, default=0.05)
    parser.add_argument("--rolling-window", type=int, default=90)
    args = parser.parse_args()

    data_dir, funding_dir, quote = exchange_paths(args.exchange)
    prices = load_daily_prices_1d(args.coins, data_dir, quote)
    price_returns = prices.pct_change().dropna()
    funding, coverage = load_daily_funding(args.coins, price_returns.index, data_dir, funding_dir, quote)
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

    years = sorted(set(returns.index.year))
    rows = []
    for year in years:
        mask = returns.index.year == year
        subset = returns.loc[mask]
        if len(subset) < 30:
            continue
        stats = slice_metrics(
            subset,
            weights.loc[subset.index],
            costs.loc[subset.index],
            funding_pnl.loc[subset.index],
            args.rebalance_days,
        )
        btc_ret = market_return(price_returns, subset.index, "btc")
        ew_ret = market_return(price_returns, subset.index, "equal_weight")
        cov = coverage.reindex(subset.index).mean(axis=1).mean() * 100.0
        rows.append(
            {
                "period": str(year),
                "start": str(subset.index.min()),
                "end": str(subset.index.max()),
                "regime": regime_label(btc_ret),
                "days": int(len(subset)),
                "signed_mv_return_pct": stats["total_return_pct"],
                "signed_mv_sharpe": stats["sharpe"],
                "signed_mv_mdd_pct": stats["max_drawdown_pct"],
                "signed_mv_calmar": stats["calmar"],
                "btc_return_pct": btc_ret,
                "equal_weight_return_pct": ew_ret,
                "funding_coverage_pct": float(cov),
            }
        )

    full_stats = metrics(returns, weights, costs, funding_pnl, args.rebalance_days)
    payload = {
        "universe": args.coins,
        "window": {"start": str(returns.index.min()), "end": str(returns.index.max())},
        "method": {
            "venue": args.exchange,
            "timeframe": "1d",
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
            "funding_note": "Funding zero-filled where local funding history is unavailable.",
        },
        "full_metrics": full_stats,
        "slices": rows,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"signed_mv_regime_slices_{args.exchange}_5coin_1d"
    out_json = RESULTS_DIR / f"{stem}.json"
    out_md = RESULTS_DIR / f"{stem}.md"
    out_png = ASSETS_DIR / f"{stem}.png"
    out_csv = RESULTS_DIR / f"{stem}.csv"
    out_timeseries = RESULTS_DIR / f"{stem}_timeseries.csv"
    out_diag_png = ASSETS_DIR / f"{stem}_diagnostics.png"

    slices_df = pd.DataFrame(rows)
    timeseries = pd.concat(
        [
            returns.rename("return"),
            equity.rename("equity"),
            (equity - 1.0).rename("pnl"),
            rolling_sharpe(returns, args.rolling_window).rename(f"rolling_sharpe_{args.rolling_window}d"),
            costs.rename("fee_drag"),
            funding_pnl.rename("funding_pnl"),
            weights.add_prefix("weight_"),
        ],
        axis=1,
    )
    slices_df.to_csv(out_csv, index=False)
    timeseries.to_csv(out_timeseries, index_label="date")
    out_json.write_text(json.dumps(payload, indent=2))
    out_md.write_text(markdown(payload))
    plot(payload, equity, slices_df, out_png)
    plot_diagnostics(returns, weights, slices_df, args.rolling_window, out_diag_png)

    print(markdown(payload))
    print(f"Full return={full_stats['total_return_pct']:.2f}% sharpe={full_stats['sharpe']:.2f} mdd={full_stats['max_drawdown_pct']:.2f}%")
    print(f"wrote {out_md}")
    print(f"wrote {out_json}")
    print(f"wrote {out_csv}")
    print(f"wrote {out_timeseries}")
    print(f"wrote {out_png}")
    print(f"wrote {out_diag_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
