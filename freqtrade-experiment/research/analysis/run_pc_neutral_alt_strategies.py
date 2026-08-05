#!/usr/bin/env python3
"""
Backtest PC-neutral mean reversion and cluster stat-arb on requested alt clusters.

Uses refreshed Hyperliquid 1h perp OHLCV. Funding is intentionally not included
in this first pass when broad funding refresh is rate-limited.

Writes:
  analysis/reports/pc_neutral_alt_strategies_hl_1h_current.json
  analysis/reports/pc_neutral_alt_strategies_hl_1h_current.md
  analysis/reports/pc_neutral_alt_equity_top.png
  analysis/reports/pc_neutral_alt_scatter.png
  analysis/reports/pc_neutral_alt_cluster_bars.png
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/backtesting-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/backtesting-cache")

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data" / "hyperliquid" / "futures"
RESULTS_DIR = REPO / "analysis" / "reports"
ASSETS_DIR = REPO / "analysis" / "reports"

FEE = 0.00035
REBALANCE_HOURS = 4
GROSS_LIMIT = 1.0
MAX_ABS_WEIGHT = 0.15
HOURS_PER_YEAR = 365.0 * 24.0

CLUSTERS: dict[str, list[str]] = {
    "DeFi mid/old guard": ["COMP", "SNX", "CRV", "BAL", "1INCH", "CVX"],
    "L1 ex-SOL": ["NEAR", "DOT", "ATOM", "INJ", "SUI", "APT", "SEI"],
    "Gaming old-cycle": ["AXS", "SAND", "MANA", "GALA", "IMX", "RON"],
    "Old PoW cyclicals": ["LTC", "BCH", "ETC", "ZEC"],
    "Perp/DEX infra ex-HYPE": ["GMX", "DYDX", "RUNE", "GNS"],
    "AI ex-TAO maybe": ["RENDER", "AKT", "GRT", "FET", "ASI"],
}

FACTOR_ONLY = ["BTC", "ETH"]


@dataclass(frozen=True)
class Params:
    family: str
    lookback_hours: int
    n_pcs: int
    signal_hours: int | None = None
    entry_z: float = 2.0
    min_resid_corr: float | None = None
    max_pairs: int | None = None

    @property
    def name(self) -> str:
        if self.family == "pc_resid_mr":
            return (
                f"MR_L{self.lookback_hours}_PC{self.n_pcs}_"
                f"S{self.signal_hours}_Z{self.entry_z:g}"
            )
        return (
            f"PAIR_L{self.lookback_hours}_PC{self.n_pcs}_"
            f"Z{self.entry_z:g}_C{self.min_resid_corr:g}_N{self.max_pairs}"
        )


@dataclass
class SimState:
    params: Params
    weights: np.ndarray
    returns: list[float] = field(default_factory=list)
    costs: list[float] = field(default_factory=list)
    turnovers: list[float] = field(default_factory=list)
    gross: list[float] = field(default_factory=list)
    net: list[float] = field(default_factory=list)
    pc_abs: list[float] = field(default_factory=list)
    active_pairs: list[int] = field(default_factory=list)


def load_prices(coins: list[str]) -> tuple[pd.DataFrame, dict[str, dict]]:
    series = []
    coverage = {}
    for coin in coins:
        path = DATA_DIR / f"{coin}_USDC_USDC-1h-futures.feather"
        if not path.exists():
            coverage[coin] = {"available": False}
            continue
        df = pd.read_feather(path)
        if df.empty:
            coverage[coin] = {"available": False}
            continue
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.sort_values("date").drop_duplicates("date")
        coverage[coin] = {
            "available": True,
            "rows": int(len(df)),
            "start": str(df["date"].iloc[0]),
            "end": str(df["date"].iloc[-1]),
            "median_daily_dollar_volume_est": float(
                (df.set_index("date")["close"] * df.set_index("date")["volume"]).resample("1D").sum().median()
            ),
        }
        series.append(df.set_index("date")["close"].rename(coin))
    prices = pd.concat(series, axis=1, join="inner").dropna(how="any")
    return prices, coverage


def pca_residual_state(hist: pd.DataFrame, n_pcs: int) -> tuple[np.ndarray, np.ndarray]:
    values = hist.to_numpy(dtype=float)
    mu = values.mean(axis=0)
    sigma = values.std(axis=0, ddof=1)
    sigma[sigma <= 1e-12] = 1.0
    x = (values - mu) / sigma
    _u, _s, vt = np.linalg.svd(x, full_matrices=False)
    loadings = vt[:n_pcs].T
    fitted = (x @ loadings) @ loadings.T
    resid = x - fitted
    return resid, loadings


def project_neutral(raw: np.ndarray, loadings: np.ndarray) -> np.ndarray:
    w = raw.astype(float).copy()
    if np.abs(w).sum() <= 1e-12:
        return w
    b = loadings
    for _ in range(4):
        gram = b.T @ b
        if np.linalg.matrix_rank(gram) == gram.shape[0]:
            w = w - b @ np.linalg.solve(gram, b.T @ w)
        else:
            w = w - b @ (np.linalg.pinv(gram) @ (b.T @ w))
        w = np.clip(w, -MAX_ABS_WEIGHT, MAX_ABS_WEIGHT)
        gross = float(np.abs(w).sum())
        if gross > GROSS_LIMIT:
            w *= GROSS_LIMIT / gross
    w[np.abs(w) < 1e-10] = 0.0
    return w


def residual_zscores(resid: np.ndarray, signal_hours: int) -> np.ndarray:
    if len(resid) <= signal_hours + 5:
        return np.zeros(resid.shape[1])
    sums = np.array([resid[i - signal_hours:i].sum(axis=0) for i in range(signal_hours, len(resid) + 1)])
    latest = sums[-1]
    mean = sums[:-1].mean(axis=0)
    std = sums[:-1].std(axis=0, ddof=1)
    std[std <= 1e-12] = np.nan
    z = (latest - mean) / std
    return np.nan_to_num(z)


def mr_target(resid_trade: np.ndarray, loadings_trade: np.ndarray, signal_hours: int, entry_z: float) -> np.ndarray:
    z = residual_zscores(resid_trade, signal_hours)
    raw = np.where(np.abs(z) >= entry_z, -z, 0.0)
    if np.abs(raw).sum() <= 1e-12:
        return raw
    raw = raw / np.abs(raw).sum() * GROSS_LIMIT
    return project_neutral(raw, loadings_trade)


def pair_target(
    resid_trade: np.ndarray,
    loadings_trade: np.ndarray,
    trade_coins: list[str],
    pairs: list[tuple[str, str, str]],
    entry_z: float,
    min_corr: float,
    max_pairs: int,
) -> tuple[np.ndarray, int]:
    candidates: list[tuple[float, np.ndarray]] = []
    coin_to_idx = {coin: idx for idx, coin in enumerate(trade_coins)}
    for _cluster, left, right in pairs:
        i = coin_to_idx[left]
        j = coin_to_idx[right]
        ri = resid_trade[:, i]
        rj = resid_trade[:, j]
        corr = float(np.corrcoef(ri, rj)[0, 1])
        if not np.isfinite(corr) or corr < min_corr:
            continue
        ci = np.cumsum(ri)
        cj = np.cumsum(rj)
        var_j = float(np.var(cj))
        if var_j <= 1e-12:
            continue
        beta = float(np.cov(ci, cj, ddof=1)[0, 1] / var_j)
        if not np.isfinite(beta) or beta <= 0:
            continue
        beta = float(np.clip(beta, 0.25, 4.0))
        spread = ci - beta * cj
        z = float((spread[-1] - spread.mean()) / max(spread.std(ddof=1), 1e-12))
        if abs(z) < entry_z:
            continue
        pair_raw = np.zeros(len(trade_coins))
        if z > 0:
            pair_raw[i] = -1.0
            pair_raw[j] = beta
        else:
            pair_raw[i] = 1.0
            pair_raw[j] = -beta
        pair_raw = pair_raw / np.abs(pair_raw).sum()
        candidates.append((abs(z), pair_raw))

    if not candidates:
        return np.zeros(len(trade_coins)), 0
    raw = np.zeros(len(trade_coins))
    for score, pair_raw in sorted(candidates, key=lambda item: item[0], reverse=True)[:max_pairs]:
        raw += min(score / entry_z, 2.0) * pair_raw
    raw = raw / np.abs(raw).sum() * GROSS_LIMIT
    return project_neutral(raw, loadings_trade), min(max_pairs, len(candidates))


def max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1.0).min())


def summarize(state: SimState, index: pd.DatetimeIndex) -> dict:
    returns = pd.Series(state.returns, index=index)
    equity = (1.0 + returns).cumprod()
    n = len(returns)
    mdd = max_drawdown(equity)
    cagr = float(equity.iloc[-1] ** (HOURS_PER_YEAR / n) - 1.0)
    std = float(returns.std())
    downside = returns[returns < 0].std()
    return {
        "name": state.params.name,
        "family": state.params.family,
        "lookback_hours": state.params.lookback_hours,
        "n_pcs": state.params.n_pcs,
        "signal_hours": state.params.signal_hours,
        "entry_z": state.params.entry_z,
        "min_resid_corr": state.params.min_resid_corr,
        "max_pairs": state.params.max_pairs,
        "start": str(index[0]),
        "end": str(index[-1]),
        "hours": int(n),
        "total_return_pct": float((equity.iloc[-1] - 1.0) * 100.0),
        "cagr_pct": cagr * 100.0,
        "ann_vol_pct": float(std * math.sqrt(HOURS_PER_YEAR) * 100.0),
        "sharpe": float(returns.mean() / std * math.sqrt(HOURS_PER_YEAR)) if std > 0 else np.nan,
        "sortino": float(returns.mean() / downside * math.sqrt(HOURS_PER_YEAR)) if downside > 0 else np.nan,
        "max_drawdown_pct": mdd * 100.0,
        "calmar": cagr / abs(mdd) if mdd < 0 else np.nan,
        "avg_gross": float(np.mean(state.gross)),
        "avg_net": float(np.mean(state.net)),
        "avg_turnover": float(np.mean(state.turnovers)),
        "total_fee_drag_pct": float(np.sum(state.costs) * 100.0),
        "active_hours_pct": float(np.mean(np.array(state.gross) > 1e-8) * 100.0),
        "avg_abs_pc_exposure": float(np.mean(state.pc_abs)),
        "avg_active_pairs": float(np.mean(state.active_pairs)) if state.active_pairs else 0.0,
        "equity": [float(x) for x in equity.to_numpy()],
    }


def run_group(
    returns: pd.DataFrame,
    trade_coins: list[str],
    factor_cols: list[str],
    pairs: list[tuple[str, str, str]],
    params: list[Params],
    lookback: int,
    n_pcs: int,
) -> list[dict]:
    trade_idx = [factor_cols.index(coin) for coin in trade_coins]
    states = [SimState(params=p, weights=np.zeros(len(trade_coins))) for p in params]
    active_index = returns.index[lookback:]

    for t in range(lookback, len(returns)):
        do_rebalance = (t - lookback) % REBALANCE_HOURS == 0
        loadings_trade = None
        resid_trade = None
        if do_rebalance:
            hist = returns.iloc[t - lookback:t][factor_cols]
            resid, loadings = pca_residual_state(hist, n_pcs)
            resid_trade = resid[:, trade_idx]
            loadings_trade = loadings[trade_idx, :]

        period_returns = returns.iloc[t][trade_coins].to_numpy(dtype=float)
        for state in states:
            cost = 0.0
            active_pair_count = 0
            if do_rebalance and resid_trade is not None and loadings_trade is not None:
                if state.params.family == "pc_resid_mr":
                    target = mr_target(
                        resid_trade,
                        loadings_trade,
                        signal_hours=int(state.params.signal_hours or 1),
                        entry_z=state.params.entry_z,
                    )
                else:
                    target, active_pair_count = pair_target(
                        resid_trade,
                        loadings_trade,
                        trade_coins,
                        pairs,
                        entry_z=state.params.entry_z,
                        min_corr=float(state.params.min_resid_corr or 0.0),
                        max_pairs=int(state.params.max_pairs or 1),
                    )
                turnover = float(np.abs(target - state.weights).sum())
                cost = FEE * turnover
                state.weights = target
            else:
                turnover = 0.0

            ret = float(state.weights @ period_returns - cost)
            state.returns.append(ret)
            state.costs.append(cost)
            state.turnovers.append(turnover)
            state.gross.append(float(np.abs(state.weights).sum()))
            state.net.append(float(state.weights.sum()))
            if loadings_trade is not None:
                state.pc_abs.append(float(np.abs(loadings_trade.T @ state.weights).sum()))
            else:
                state.pc_abs.append(0.0)
            state.active_pairs.append(active_pair_count)

    return [summarize(state, active_index) for state in states]


def render_scatter(rows: list[dict], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), dpi=180)
    colors = {"pc_resid_mr": "#1d4ed8", "pc_pair_stat_arb": "#b91c1c"}
    for family in sorted({row["family"] for row in rows}):
        fam = [row for row in rows if row["family"] == family and rank_score(row) > -1e8]
        ax.scatter(
            [abs(row["max_drawdown_pct"]) for row in fam],
            [row["sharpe"] for row in fam],
            s=45,
            alpha=0.8,
            color=colors.get(family, "gray"),
            label=family,
        )
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("|Max drawdown| %")
    ax.set_ylabel("Sharpe")
    ax.set_title("PC-Neutral Alt Strategy Sweep")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)


def render_equity(rows: list[dict], index_by_name: dict[str, pd.DatetimeIndex], out_path: Path) -> None:
    top = sorted(
        [row for row in rows if rank_score(row) > -1e8],
        key=rank_score,
        reverse=True,
    )[:6]
    fig, ax = plt.subplots(figsize=(12, 7), dpi=180)
    for row in top:
        idx = index_by_name[row["name"]]
        ax.plot(idx, row["equity"], linewidth=1.7, label=f"{row['name']} S={row['sharpe']:.2f}")
    ax.axhline(1.0, color="black", linewidth=0.8)
    ax.set_title("Top PC-Neutral Alt Strategy Equity Curves")
    ax.set_ylabel("Growth of $1")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, frameon=False)
    fig.autofmt_xdate()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)


def render_cluster_bars(returns: pd.DataFrame, clusters: dict[str, list[str]], out_path: Path) -> None:
    rows = []
    for cluster, coins in clusters.items():
        available = [coin for coin in coins if coin in returns.columns]
        if not available:
            continue
        avg_corr = returns[available].corr().where(np.triu(np.ones((len(available), len(available))), 1).astype(bool)).stack().mean()
        rows.append((cluster, len(available), float(avg_corr)))
    fig, ax = plt.subplots(figsize=(11, 5.8), dpi=180)
    labels = [row[0] for row in rows]
    values = [row[2] for row in rows]
    ax.barh(labels, values, color="#647083")
    for i, (_cluster, count, value) in enumerate(rows):
        ax.text(value + 0.01, i, f"n={count}, corr={value:.2f}", va="center", fontsize=8)
    ax.set_title("Within-Cluster 1h Return Correlation")
    ax.set_xlabel("Average pairwise correlation")
    ax.set_xlim(0, max(values + [0.1]) + 0.15)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)


def markdown(payload: dict) -> str:
    rows = payload["results"]
    top = sorted(
        [row for row in rows if rank_score(row) > -1e8],
        key=rank_score,
        reverse=True,
    )[:12]
    lines = [
        "# PC-Neutral Alt Mean Reversion / Stat-Arb Sweep",
        "",
        f"Window: `{payload['window']['start']}` -> `{payload['window']['end']}`.",
        "",
        "Funding is omitted in this first pass because the broad Hyperliquid funding refresh hit 429 rate limits.",
        "",
        f"Available requested alts: `{', '.join(payload['universe']['trade_coins'])}`",
        f"Missing on Hyperliquid: `{', '.join(payload['universe']['missing_requested'])}`",
        "",
        "## Top Rows by Sharpe",
        "",
        "| Rank | Name | Family | Return | Sharpe | MDD | Calmar | Gross | Active | Fees |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for rank, row in enumerate(top, start=1):
        lines.append(
            f"| {rank} | `{row['name']}` | {row['family']} | "
            f"{row['total_return_pct']:.2f}% | {row['sharpe']:.2f} | "
            f"{row['max_drawdown_pct']:.2f}% | {row['calmar']:.2f} | "
            f"{row['avg_gross']:.2f} | {row['active_hours_pct']:.1f}% | "
            f"{row['total_fee_drag_pct']:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Charts",
            "",
            "![equity](../assets/pc_neutral_alt_equity_top.png)",
            "",
            "![scatter](../assets/pc_neutral_alt_scatter.png)",
            "",
            "![clusters](../assets/pc_neutral_alt_cluster_bars.png)",
            "",
            "## Method",
            "",
            "- Factor set: BTC, ETH, and all available requested alts.",
            "- Trade set: requested alts only.",
            "- PCA is fit walk-forward on standardized 1h returns.",
            "- PC residual MR trades extreme residual z-scores against the move.",
            "- Pair stat-arb trades within user-specified clusters after residualizing to PCs.",
            "- Target weights are projected to be neutral to the fitted PCs, then capped at 15% per token and 100% gross.",
            "- Rebalance cadence: 4h. Fee: 0.035% per unit turnover.",
        ]
    )
    return "\n".join(lines) + "\n"


def rank_score(row: dict) -> float:
    sharpe = float(row.get("sharpe", float("nan")))
    if not np.isfinite(sharpe) or row.get("active_hours_pct", 0.0) <= 0:
        return -1e9
    return sharpe


def main() -> int:
    requested = [coin for coins in CLUSTERS.values() for coin in coins]
    all_needed = sorted(set(requested + FACTOR_ONLY))
    prices, coverage = load_prices(all_needed)

    trade_coins = [coin for coin in requested if coin in prices.columns]
    missing = [coin for coin in requested if coin not in prices.columns]
    factor_cols = [coin for coin in FACTOR_ONLY + trade_coins if coin in prices.columns]
    prices = prices[factor_cols]
    returns = prices.pct_change().dropna()

    pairs = []
    for cluster, coins in CLUSTERS.items():
        available = [coin for coin in coins if coin in trade_coins]
        for i, left in enumerate(available):
            for right in available[i + 1:]:
                pairs.append((cluster, left, right))

    params: list[Params] = []
    for lookback in [168, 336, 720]:
        for n_pcs in [1, 2, 3]:
            for signal_hours in [6, 24, 48]:
                for entry_z in [1.5, 2.0, 2.5, 3.0]:
                    params.append(
                        Params(
                            family="pc_resid_mr",
                            lookback_hours=lookback,
                            n_pcs=n_pcs,
                            signal_hours=signal_hours,
                            entry_z=entry_z,
                        )
                    )
    for lookback in [336, 720]:
        for n_pcs in [1, 2, 3]:
            for entry_z in [1.5, 2.0, 2.5, 3.0]:
                for min_corr in [0.1, 0.3, 0.5]:
                    for max_pairs in [3, 6]:
                        params.append(
                            Params(
                                family="pc_pair_stat_arb",
                                lookback_hours=lookback,
                                n_pcs=n_pcs,
                                entry_z=entry_z,
                                min_resid_corr=min_corr,
                                max_pairs=max_pairs,
                            )
                        )

    all_results: list[dict] = []
    index_by_name: dict[str, pd.DatetimeIndex] = {}
    for (lookback, n_pcs), group_params in sorted(
        pd.Series(params).groupby(lambda idx: (params[idx].lookback_hours, params[idx].n_pcs)).groups.items()
    ):
        selected_params = [params[i] for i in group_params]
        print(f"running lookback={lookback} n_pcs={n_pcs} params={len(selected_params)}")
        rows = run_group(returns, trade_coins, factor_cols, pairs, selected_params, lookback, n_pcs)
        active_index = returns.index[lookback:]
        for row in rows:
            all_results.append(row)
            index_by_name[row["name"]] = active_index

    payload = {
        "method": {
            "venue": "Hyperliquid perps",
            "timeframe": "1h",
            "funding": "omitted - broad refresh hit Hyperliquid 429 rate limits",
            "rebalance_hours": REBALANCE_HOURS,
            "fee": FEE,
            "gross_limit": GROSS_LIMIT,
            "max_abs_weight": MAX_ABS_WEIGHT,
            "families": [
                "pc_resid_mr: individual-token residual mean reversion",
                "pc_pair_stat_arb: cluster pair residual stat-arb",
            ],
        },
        "window": {"start": str(returns.index.min()), "end": str(returns.index.max()), "hours": int(len(returns))},
        "universe": {
            "clusters": CLUSTERS,
            "factor_cols": factor_cols,
            "trade_coins": trade_coins,
            "missing_requested": missing,
            "coverage": coverage,
            "pairs": pairs,
        },
        "results": sorted(all_results, key=lambda row: row["sharpe"], reverse=True),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = RESULTS_DIR / "pc_neutral_alt_strategies_hl_1h_current.json"
    out_md = RESULTS_DIR / "pc_neutral_alt_strategies_hl_1h_current.md"
    out_json.write_text(json.dumps(payload, indent=2))
    out_md.write_text(markdown(payload))
    render_scatter(payload["results"], ASSETS_DIR / "pc_neutral_alt_scatter.png")
    render_equity(payload["results"], index_by_name, ASSETS_DIR / "pc_neutral_alt_equity_top.png")
    render_cluster_bars(returns, CLUSTERS, ASSETS_DIR / "pc_neutral_alt_cluster_bars.png")

    print(markdown(payload).split("## Charts")[0])
    print(f"wrote {out_json}")
    print(f"wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
