#!/usr/bin/env python3
"""
Run walk-forward portfolio-construction baselines for the selected Hyperliquid universe.

Writes:
  analysis/reports/portfolio_baselines_hl_1h_current.json
  analysis/reports/portfolio_baselines_hl_1h_current.md
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/backtesting-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/backtesting-cache")

import numpy as np
import pandas as pd
import matplotlib
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data" / "hyperliquid" / "futures"
UNIVERSE_JSON = REPO / "analysis" / "reports" / "universe_selection_hl_1h_current.json"
RESULTS_DIR = REPO / "analysis" / "reports"
ASSETS_DIR = REPO / "analysis" / "reports"


def load_universe(path: Path) -> list[str]:
    payload = json.loads(path.read_text())
    return payload["selected_universe"]["coins"]


def load_daily_prices(coins: list[str]) -> pd.DataFrame:
    series = []
    for coin in coins:
        path = DATA_DIR / f"{coin}_USDC_USDC-1h-futures.feather"
        df = pd.read_feather(path)
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.sort_values("date").drop_duplicates("date")
        daily = df.set_index("date")["close"].resample("1D").last().dropna()
        series.append(daily.rename(coin))
    return pd.concat(series, axis=1).dropna(how="any")


def shrink_cov(hist: pd.DataFrame) -> np.ndarray:
    cov = LedoitWolf().fit(hist.to_numpy()).covariance_
    return cov * 365.0


def effective_assets(weights: np.ndarray) -> float:
    invested = weights.sum()
    if invested <= 1e-12:
        return 0.0
    scaled = weights / invested
    return float(1.0 / np.sum(np.square(scaled)))


def solve_min_var(hist: pd.DataFrame, cap: float) -> np.ndarray:
    n = hist.shape[1]
    cov = shrink_cov(hist)
    x0 = np.repeat(1.0 / n, n)
    bounds = [(0.0, cap)] * n
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    result = minimize(
        lambda w: float(w @ cov @ w),
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-10},
    )
    if not result.success:
        return x0
    return np.asarray(result.x)


def solve_mean_var(
    hist: pd.DataFrame,
    previous: np.ndarray,
    cap: float,
    mean_shrink: float,
    risk_aversion: float,
    turnover_penalty: float,
) -> np.ndarray:
    n = hist.shape[1]
    cov = shrink_cov(hist)
    mu = hist.mean().to_numpy() * 365.0 * mean_shrink
    x0 = np.minimum(np.maximum(previous, 0.0), cap)
    bounds = [(0.0, cap)] * n
    constraints = [{"type": "ineq", "fun": lambda w: 1.0 - np.sum(w)}]

    def objective(w: np.ndarray) -> float:
        ret = float(mu @ w)
        risk = float(w @ cov @ w)
        churn = float(np.sum(np.square(w - previous)))
        return -(ret - risk_aversion * risk - turnover_penalty * churn)

    result = minimize(
        objective,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-10},
    )
    if not result.success:
        return x0
    return np.asarray(result.x)


def inverse_vol(hist: pd.DataFrame, cap: float) -> np.ndarray:
    vol = hist.std().replace(0, np.nan)
    inv = (1.0 / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy()
    if inv.sum() <= 0:
        return np.repeat(1.0 / hist.shape[1], hist.shape[1])
    raw = inv / inv.sum()
    capped = np.minimum(raw, cap)
    while capped.sum() < 1.0 - 1e-12:
        room = cap - capped
        if room.sum() <= 1e-12:
            break
        add = np.minimum(room, (1.0 - capped.sum()) * room / room.sum())
        capped += add
    return capped / capped.sum()


def simulate(
    returns: pd.DataFrame,
    method: str,
    lookback: int,
    rebalance_days: int,
    fee: float,
    cap: float,
    mean_shrink: float,
    risk_aversion: float,
    turnover_penalty: float,
) -> tuple[pd.Series, pd.DataFrame, pd.Series]:
    n = returns.shape[1]
    active_index = returns.index[lookback:]
    weights = pd.DataFrame(0.0, index=active_index, columns=returns.columns)
    costs = pd.Series(0.0, index=active_index)
    portfolio_returns = pd.Series(0.0, index=active_index)
    asset_values = np.zeros(n)
    cash = 1.0

    for idx in range(lookback, len(returns)):
        date = returns.index[idx]
        day_start_value = float(asset_values.sum() + cash)
        cost = 0.0
        if (idx - lookback) % rebalance_days == 0:
            hist = returns.iloc[idx - lookback:idx]
            current_weights = asset_values / day_start_value if day_start_value > 0 else np.zeros(n)
            new = target_weights(
                returns=returns,
                method=method,
                hist=hist,
                previous=current_weights,
                cap=cap,
                mean_shrink=mean_shrink,
                risk_aversion=risk_aversion,
                turnover_penalty=turnover_penalty,
            )
            turnover = float(np.abs(new - current_weights).sum())
            cost = fee * turnover * day_start_value
            investable = day_start_value - cost
            asset_values = new * investable
            cash = max(0.0, 1.0 - float(new.sum())) * investable

        asset_values = asset_values * (1.0 + returns.iloc[idx].to_numpy())
        day_end_value = float(asset_values.sum() + cash)
        weights.loc[date] = asset_values / day_end_value if day_end_value > 0 else np.zeros(n)
        costs.loc[date] = cost / day_start_value if day_start_value > 0 else 0.0
        portfolio_returns.loc[date] = day_end_value / day_start_value - 1.0

    return portfolio_returns, weights, costs


def target_weights(
    returns: pd.DataFrame,
    method: str,
    hist: pd.DataFrame,
    previous: np.ndarray,
    cap: float,
    mean_shrink: float,
    risk_aversion: float,
    turnover_penalty: float,
) -> np.ndarray:
    n = returns.shape[1]
    if method == "btc":
        new = np.zeros(n)
        new[returns.columns.get_loc("BTC")] = 1.0
    elif method == "equal_weight":
        new = np.repeat(1.0 / n, n)
    elif method == "inverse_vol":
        new = inverse_vol(hist, cap)
    elif method == "minimum_variance":
        new = solve_min_var(hist, cap)
    elif method == "shrunk_mean_variance":
        new = solve_mean_var(
            hist,
            previous,
            cap,
            mean_shrink,
            risk_aversion,
            turnover_penalty,
        )
    else:
        raise ValueError(method)
    return new


def max_drawdown(equity: pd.Series) -> float:
    drawdown = equity / equity.cummax() - 1.0
    return float(drawdown.min())


def metrics(
    returns: pd.Series,
    weights: pd.DataFrame,
    costs: pd.Series,
    rebalance_days: int,
) -> dict:
    equity = (1.0 + returns).cumprod()
    n_days = len(returns)
    total_return = float(equity.iloc[-1] - 1.0)
    cagr = float(equity.iloc[-1] ** (365.0 / n_days) - 1.0)
    vol = float(returns.std() * np.sqrt(365.0))
    sharpe = float(returns.mean() / returns.std() * np.sqrt(365.0)) if returns.std() > 0 else np.nan
    downside = returns[returns < 0].std()
    sortino = float(returns.mean() / downside * np.sqrt(365.0)) if downside > 0 else np.nan
    mdd = max_drawdown(equity)
    drawdown = equity / equity.cummax() - 1.0
    ulcer = float(np.sqrt(np.mean(np.square(drawdown.to_numpy()))))
    exposures = weights.sum(axis=1)
    rebalanced_weights = weights.iloc[::rebalance_days]
    turnover = weights.diff().abs().sum(axis=1)
    turnover.iloc[0] = weights.iloc[0].abs().sum()
    rebalanced_turnover = turnover.iloc[::rebalance_days]
    return {
        "days": int(n_days),
        "total_return_pct": total_return * 100.0,
        "cagr_pct": cagr * 100.0,
        "ann_vol_pct": vol * 100.0,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown_pct": mdd * 100.0,
        "calmar": cagr / abs(mdd) if mdd < 0 else np.nan,
        "ulcer_pct": ulcer * 100.0,
        "avg_exposure": float(exposures.mean()),
        "avg_effective_assets": float(np.mean([effective_assets(row) for row in rebalanced_weights.to_numpy()])),
        "avg_turnover_per_rebalance": float(rebalanced_turnover.mean()),
        "total_fee_drag_pct": float(costs.sum() * 100.0),
        "final_weights": {
            coin: float(weight)
            for coin, weight in weights.iloc[-1].items()
            if abs(weight) > 1e-8
        },
    }


def format_metric(value: float, pct: bool = False) -> str:
    if value is None or not np.isfinite(value):
        return "nan"
    if pct:
        return f"{value:.2f}%"
    return f"{value:.2f}"


def markdown_table(rows: dict[str, dict]) -> str:
    order = [
        "total_return_pct",
        "cagr_pct",
        "ann_vol_pct",
        "sharpe",
        "sortino",
        "max_drawdown_pct",
        "calmar",
        "ulcer_pct",
        "avg_exposure",
        "avg_effective_assets",
        "avg_turnover_per_rebalance",
        "total_fee_drag_pct",
    ]
    labels = {
        "total_return_pct": "Total Return",
        "cagr_pct": "CAGR",
        "ann_vol_pct": "Ann Vol",
        "sharpe": "Sharpe",
        "sortino": "Sortino",
        "max_drawdown_pct": "MDD",
        "calmar": "Calmar",
        "ulcer_pct": "Ulcer",
        "avg_exposure": "Avg Exposure",
        "avg_effective_assets": "Eff Assets",
        "avg_turnover_per_rebalance": "Turnover/Rebal",
        "total_fee_drag_pct": "Fee Drag",
    }
    pct_fields = {
        "total_return_pct",
        "cagr_pct",
        "ann_vol_pct",
        "max_drawdown_pct",
        "ulcer_pct",
        "total_fee_drag_pct",
    }
    methods = list(rows)
    lines = ["| Metric | " + " | ".join(methods) + " |"]
    lines.append("|---|" + "|".join(["---:"] * len(methods)) + "|")
    for key in order:
        vals = [format_metric(rows[name][key], key in pct_fields) for name in methods]
        lines.append(f"| {labels[key]} | " + " | ".join(vals) + " |")
    return "\n".join(lines)


def render_equal_weight_charts(returns: pd.Series, weights: pd.DataFrame) -> tuple[Path, Path]:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    equity = (1.0 + returns).cumprod()
    profit = (equity - 1.0) * 100.0

    profit_path = ASSETS_DIR / "portfolio_equal_weight_profit_current.png"
    fig, ax = plt.subplots(figsize=(11.0, 5.8), dpi=180)
    ax.plot(profit.index, profit, color="#1f77b4", linewidth=2.0)
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.45)
    ax.set_title("Equal-Weight Portfolio Profit Over Time")
    ax.set_ylabel("Profit (%)")
    ax.grid(True, alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(profit_path)
    plt.close(fig)

    positions_path = ASSETS_DIR / "portfolio_equal_weight_positions_current.png"
    fig, ax = plt.subplots(figsize=(11.0, 6.2), dpi=180)
    for coin in weights.columns:
        ax.plot(weights.index, weights[coin] * 100.0, linewidth=1.4, label=coin)
    ax.set_title("Equal-Weight Portfolio Positions Over Time")
    ax.set_ylabel("Weight (%)")
    ax.grid(True, alpha=0.25)
    ax.legend(ncol=5, fontsize=8, frameon=False)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(positions_path)
    plt.close(fig)
    return profit_path, positions_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--universe-json", type=Path, default=UNIVERSE_JSON)
    parser.add_argument("--lookback", type=int, default=60)
    parser.add_argument("--rebalance-days", type=int, default=7)
    parser.add_argument("--fee", type=float, default=0.00035)
    parser.add_argument("--cap", type=float, default=0.20)
    parser.add_argument("--mean-shrink", type=float, default=0.10)
    parser.add_argument("--risk-aversion", type=float, default=3.0)
    parser.add_argument("--turnover-penalty", type=float, default=0.05)
    args = parser.parse_args()

    coins = load_universe(args.universe_json)
    prices = load_daily_prices(coins)
    returns = prices.pct_change().dropna()
    methods = [
        "btc",
        "equal_weight",
        "inverse_vol",
        "minimum_variance",
        "shrunk_mean_variance",
    ]

    rows = {}
    simulations = {}
    for method in methods:
        port_rets, weights, costs = simulate(
            returns,
            method=method,
            lookback=args.lookback,
            rebalance_days=args.rebalance_days,
            fee=args.fee,
            cap=args.cap,
            mean_shrink=args.mean_shrink,
            risk_aversion=args.risk_aversion,
            turnover_penalty=args.turnover_penalty,
        )
        rows[method] = metrics(port_rets, weights, costs, args.rebalance_days)
        simulations[method] = (port_rets, weights, costs)

    equal_profit_path, equal_positions_path = render_equal_weight_charts(
        simulations["equal_weight"][0],
        simulations["equal_weight"][1],
    )

    payload = {
        "universe": coins,
        "method": {
            "return_frequency": "daily close-to-close from 1h OHLCV",
            "lookback_days": args.lookback,
            "rebalance_days": args.rebalance_days,
            "fee": args.fee,
            "max_weight": args.cap,
            "mean_shrink": args.mean_shrink,
            "risk_aversion": args.risk_aversion,
            "turnover_penalty": args.turnover_penalty,
            "funding": "not included",
        },
        "window": {
            "price_start": str(prices.index.min()),
            "price_end": str(prices.index.max()),
            "active_start": str(returns.index[args.lookback]),
            "active_end": str(returns.index.max()),
        },
        "results": rows,
        "charts": {
            "equal_weight_profit": str(equal_profit_path),
            "equal_weight_positions": str(equal_positions_path),
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = RESULTS_DIR / "portfolio_baselines_hl_1h_current.json"
    out_md = RESULTS_DIR / "portfolio_baselines_hl_1h_current.md"
    out_json.write_text(json.dumps(payload, indent=2))
    out_md.write_text(
        "# Portfolio Baselines - Hyperliquid Current Universe\n\n"
        f"Universe: `{', '.join(coins)}`\n\n"
        f"Window: `{payload['window']['active_start']}` -> `{payload['window']['active_end']}`\n\n"
        + markdown_table(rows)
        + "\n"
    )

    print(markdown_table(rows))
    print(f"\nwrote {out_json}")
    print(f"wrote {out_md}")
    print(f"wrote {equal_profit_path}")
    print(f"wrote {equal_positions_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
