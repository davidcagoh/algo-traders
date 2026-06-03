#!/usr/bin/env python3
"""
Run portfolio baselines with signed perp weights and funding.

Writes:
  wiki/results/portfolio_short_funding_hl_1h_current.json
  wiki/results/portfolio_short_funding_hl_1h_current.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from run_portfolio_baselines import (
    RESULTS_DIR,
    UNIVERSE_JSON,
    load_daily_prices,
    load_universe,
    shrink_cov,
)


REPO = Path(__file__).resolve().parent.parent
FUNDING_DIR = REPO / "user_data" / "data" / "hyperliquid" / "funding"


def as_utc_ns(values: pd.Series | pd.DatetimeIndex) -> pd.Series | pd.DatetimeIndex:
    converted = pd.to_datetime(values, utc=True)
    if isinstance(converted, pd.Series):
        return converted.dt.as_unit("ns")
    return converted.as_unit("ns")


def load_daily_funding(coins: list[str], index: pd.DatetimeIndex) -> pd.DataFrame:
    series = []
    for coin in coins:
        path = FUNDING_DIR / f"{coin}-funding.parquet"
        df = pd.read_parquet(path)
        df["time"] = as_utc_ns(df["time"])
        daily = df.set_index("time")["funding_rate"].resample("1D").sum()
        daily.index = daily.index.as_unit("ns")
        series.append(daily.rename(coin))
    return pd.concat(series, axis=1).reindex(as_utc_ns(index)).fillna(0.0)


def effective_assets_signed(weights: np.ndarray) -> float:
    gross = np.abs(weights).sum()
    if gross <= 1e-12:
        return 0.0
    scaled = np.abs(weights) / gross
    return float(1.0 / np.sum(np.square(scaled)))


def inverse_vol(hist: pd.DataFrame, cap: float) -> np.ndarray:
    vol = hist.std().replace(0, np.nan)
    inv = (1.0 / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy()
    raw = inv / inv.sum()
    capped = np.minimum(raw, cap)
    while capped.sum() < 1.0 - 1e-12:
        room = cap - capped
        add = np.minimum(room, (1.0 - capped.sum()) * room / room.sum())
        capped += add
        if add.sum() <= 1e-12:
            break
    return capped / capped.sum()


def solve_min_var_signed(hist: pd.DataFrame, cap: float, gross_limit: float) -> np.ndarray:
    n = hist.shape[1]
    cov = shrink_cov(hist)
    x0 = np.repeat(gross_limit / n, n)
    bounds = [(-cap, cap)] * n
    constraints = [{"type": "eq", "fun": lambda w: np.abs(w).sum() - gross_limit}]
    result = minimize(
        lambda w: float(w @ cov @ w),
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-10},
    )
    if not result.success:
        return x0
    return np.asarray(result.x)


def solve_mean_var_signed(
    hist: pd.DataFrame,
    previous: np.ndarray,
    cap: float,
    gross_limit: float,
    mean_shrink: float,
    risk_aversion: float,
    turnover_penalty: float,
) -> np.ndarray:
    cov = shrink_cov(hist)
    mu = hist.mean().to_numpy() * 365.0 * mean_shrink
    n = hist.shape[1]
    previous = np.asarray(previous, dtype=float)
    bounds = [(0.0, cap)] * (2 * n)
    constraints = [{"type": "ineq", "fun": lambda z: gross_limit - np.sum(z)}]
    constraints.extend(
        {"type": "ineq", "fun": lambda z, i=i: cap - z[i] - z[n + i]}
        for i in range(n)
    )

    def pack(weights: np.ndarray) -> np.ndarray:
        weights = np.clip(weights, -cap, cap)
        gross = np.abs(weights).sum()
        if gross > gross_limit:
            weights = weights / gross * gross_limit
        return np.concatenate([np.maximum(weights, 0.0), np.maximum(-weights, 0.0)])

    def unpack(z: np.ndarray) -> np.ndarray:
        return z[:n] - z[n:]

    def signal_seed() -> np.ndarray:
        weights = np.zeros(n)
        gross = 0.0
        for idx in np.argsort(-np.abs(mu)):
            if abs(mu[idx]) <= 1e-12 or gross >= gross_limit - 1e-12:
                break
            size = min(cap, gross_limit - gross)
            weights[idx] = np.copysign(size, mu[idx])
            gross += size
        return weights

    def objective_from_weights(w: np.ndarray) -> float:
        ret = float(mu @ w)
        risk = float(w @ cov @ w)
        churn = float(np.sum(np.square(w - previous)))
        return -(ret - risk_aversion * risk - turnover_penalty * churn)

    def objective(z: np.ndarray) -> float:
        return objective_from_weights(unpack(z))

    best = np.clip(previous, -cap, cap)
    if np.abs(best).sum() > gross_limit:
        best = best / np.abs(best).sum() * gross_limit
    best_score = objective_from_weights(best)

    for seed in (best, signal_seed()):
        z0 = pack(seed)
        result = minimize(
            objective,
            z0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-10},
        )
        for candidate in (seed, unpack(result.x) if result.success else seed):
            score = objective_from_weights(candidate)
            if score < best_score:
                best = candidate
                best_score = score

    best[np.abs(best) < 1e-10] = 0.0
    return np.asarray(best)


def target_weights(
    method: str,
    hist: pd.DataFrame,
    previous: np.ndarray,
    cap: float,
    gross_limit: float,
    mean_shrink: float,
    risk_aversion: float,
    turnover_penalty: float,
) -> np.ndarray:
    n = hist.shape[1]
    if method == "btc_long":
        weights = np.zeros(n)
        weights[hist.columns.get_loc("BTC")] = 1.0
        return weights
    if method == "equal_weight_long":
        return np.repeat(1.0 / n, n)
    if method == "inverse_vol_long":
        return inverse_vol(hist, cap)
    if method == "minimum_variance_signed":
        return solve_min_var_signed(hist, cap, gross_limit)
    if method == "shrunk_mean_variance_signed":
        return solve_mean_var_signed(
            hist,
            previous,
            cap,
            gross_limit,
            mean_shrink,
            risk_aversion,
            turnover_penalty,
        )
    raise ValueError(method)


def simulate(
    price_returns: pd.DataFrame,
    funding: pd.DataFrame,
    method: str,
    lookback: int,
    rebalance_days: int,
    fee: float,
    cap: float,
    gross_limit: float,
    mean_shrink: float,
    risk_aversion: float,
    turnover_penalty: float,
) -> tuple[pd.Series, pd.DataFrame, pd.Series, pd.Series]:
    active_index = price_returns.index[lookback:]
    weights = pd.DataFrame(0.0, index=active_index, columns=price_returns.columns)
    returns = pd.Series(0.0, index=active_index)
    costs = pd.Series(0.0, index=active_index)
    funding_pnl = pd.Series(0.0, index=active_index)
    notional = np.zeros(price_returns.shape[1])
    equity = 1.0

    for idx in range(lookback, len(price_returns)):
        date = price_returns.index[idx]
        start_equity = equity
        current_weights = notional / equity if equity > 0 else np.zeros_like(notional)

        if (idx - lookback) % rebalance_days == 0:
            hist = price_returns.iloc[idx - lookback:idx] - funding.iloc[idx - lookback:idx]
            new_weights = target_weights(
                method,
                hist,
                current_weights,
                cap,
                gross_limit,
                mean_shrink,
                risk_aversion,
                turnover_penalty,
            )
            turnover = float(np.abs(new_weights - current_weights).sum())
            cost = fee * turnover * equity
            equity -= cost
            costs.loc[date] = cost / start_equity if start_equity > 0 else 0.0
            notional = new_weights * equity

        price = price_returns.iloc[idx].to_numpy()
        fund = funding.iloc[idx].to_numpy()
        fund_pnl = float(np.sum(notional * -fund))
        price_pnl = float(np.sum(notional * price))
        notional = notional * (1.0 + price)
        equity += price_pnl + fund_pnl
        returns.loc[date] = equity / start_equity - 1.0
        weights.loc[date] = notional / equity if equity > 0 else 0.0
        funding_pnl.loc[date] = fund_pnl / start_equity if start_equity > 0 else 0.0

    return returns, weights, costs, funding_pnl


def max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1.0).min())


def metrics(returns: pd.Series, weights: pd.DataFrame, costs: pd.Series, funding_pnl: pd.Series, rebalance_days: int) -> dict:
    equity = (1.0 + returns).cumprod()
    std = returns.std()
    downside = returns[returns < 0].std()
    mdd = max_drawdown(equity)
    turnover = weights.diff().abs().sum(axis=1)
    turnover.iloc[0] = weights.iloc[0].abs().sum()
    rebalanced = weights.iloc[::rebalance_days]
    n_days = len(returns)
    cagr = float(equity.iloc[-1] ** (365.0 / n_days) - 1.0)
    return {
        "days": int(n_days),
        "total_return_pct": float((equity.iloc[-1] - 1.0) * 100.0),
        "cagr_pct": cagr * 100.0,
        "ann_vol_pct": float(std * np.sqrt(365.0) * 100.0),
        "sharpe": float(returns.mean() / std * np.sqrt(365.0)) if std > 0 else np.nan,
        "sortino": float(returns.mean() / downside * np.sqrt(365.0)) if downside > 0 else np.nan,
        "max_drawdown_pct": mdd * 100.0,
        "calmar": cagr / abs(mdd) if mdd < 0 else np.nan,
        "avg_gross_exposure": float(weights.abs().sum(axis=1).mean()),
        "avg_net_exposure": float(weights.sum(axis=1).mean()),
        "avg_effective_assets": float(np.mean([effective_assets_signed(row) for row in rebalanced.to_numpy()])),
        "avg_turnover_per_rebalance": float(turnover.iloc[::rebalance_days].mean()),
        "total_fee_drag_pct": float(costs.sum() * 100.0),
        "total_funding_pnl_pct": float(funding_pnl.sum() * 100.0),
        "final_weights": {
            coin: float(weight)
            for coin, weight in weights.iloc[-1].items()
            if abs(weight) > 1e-8
        },
    }


def markdown(rows: dict[str, dict]) -> str:
    ranked = sorted(rows.items(), key=lambda item: item[1]["sharpe"], reverse=True)
    lines = [
        "| Rank | Portfolio | Return | Sharpe | MDD | Calmar | Gross | Net | Eff Assets | Fee Drag | Funding PnL |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for rank, (name, row) in enumerate(ranked, start=1):
        lines.append(
            f"| {rank} | {name} | {row['total_return_pct']:.2f}% | {row['sharpe']:.2f} | "
            f"{row['max_drawdown_pct']:.2f}% | {row['calmar']:.2f} | "
            f"{row['avg_gross_exposure']:.2f} | {row['avg_net_exposure']:.2f} | "
            f"{row['avg_effective_assets']:.2f} | {row['total_fee_drag_pct']:.2f}% | "
            f"{row['total_funding_pnl_pct']:.2f}% |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--universe-json", type=Path, default=UNIVERSE_JSON)
    parser.add_argument("--lookback", type=int, default=60)
    parser.add_argument("--rebalance-days", type=int, default=7)
    parser.add_argument("--fee", type=float, default=0.00035)
    parser.add_argument("--cap", type=float, default=0.20)
    parser.add_argument("--gross-limit", type=float, default=1.0)
    parser.add_argument("--mean-shrink", type=float, default=0.50)
    parser.add_argument("--risk-aversion", type=float, default=1.0)
    parser.add_argument("--turnover-penalty", type=float, default=0.05)
    args = parser.parse_args()

    coins = load_universe(args.universe_json)
    prices = load_daily_prices(coins)
    price_returns = prices.pct_change().dropna()
    funding = load_daily_funding(coins, price_returns.index)

    methods = [
        "btc_long",
        "equal_weight_long",
        "inverse_vol_long",
        "minimum_variance_signed",
        "shrunk_mean_variance_signed",
    ]
    rows = {}
    for method in methods:
        rets, weights, costs, fund_pnl = simulate(
            price_returns,
            funding,
            method,
            args.lookback,
            args.rebalance_days,
            args.fee,
            args.cap,
            args.gross_limit,
            args.mean_shrink,
            args.risk_aversion,
            args.turnover_penalty,
        )
        rows[method] = metrics(rets, weights, costs, fund_pnl, args.rebalance_days)

    payload = {
        "universe": coins,
        "method": {
            "return_frequency": "daily close-to-close from 1h OHLCV",
            "funding": "daily sum of Hyperliquid funding_rate; signed position return = price_return - funding_rate",
            "lookback_days": args.lookback,
            "rebalance_days": args.rebalance_days,
            "fee": args.fee,
            "max_abs_weight": args.cap,
            "gross_limit": args.gross_limit,
            "mean_shrink": args.mean_shrink,
            "risk_aversion": args.risk_aversion,
            "turnover_penalty": args.turnover_penalty,
        },
        "window": {
            "price_start": str(prices.index.min()),
            "price_end": str(prices.index.max()),
            "active_start": str(price_returns.index[args.lookback]),
            "active_end": str(price_returns.index.max()),
        },
        "results": rows,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = RESULTS_DIR / "portfolio_short_funding_hl_1h_current.json"
    out_md = RESULTS_DIR / "portfolio_short_funding_hl_1h_current.md"
    body = (
        "# Portfolio Rerank - Shorting + Funding\n\n"
        f"Universe: `{', '.join(coins)}`\n\n"
        f"Window: `{payload['window']['active_start']}` -> `{payload['window']['active_end']}`\n\n"
        + markdown(rows)
        + "\n"
    )
    out_json.write_text(json.dumps(payload, indent=2))
    out_md.write_text(body)
    print(markdown(rows))
    print(f"\nwrote {out_json}")
    print(f"wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
