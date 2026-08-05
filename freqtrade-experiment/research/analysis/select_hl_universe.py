#!/usr/bin/env python3
"""
Select a lower-correlation Hyperliquid futures universe from refreshed 1h data.

The screen is intentionally simple:
  - require current, nearly full 1h coverage
  - require a minimum median daily dollar-volume estimate
  - seed the basket with BTC and HYPE
  - exclude any manually vetoed symbols
  - greedily add coins that minimize average pairwise daily-return correlation

Writes:
  analysis/reports/universe_selection_hl_1h_current.json
  analysis/reports/universe_selection_corr_current.png
  analysis/reports/universe_selection_prices_current.png
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/backtesting-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/backtesting-cache")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data" / "hyperliquid" / "futures"
RESULTS_DIR = REPO / "analysis" / "reports"
ASSETS_DIR = REPO / "analysis" / "reports"
DEFAULT_EXCLUDE = ["TRUMP"]


@dataclass(frozen=True)
class CoinStats:
    coin: str
    rows: int
    start: str
    end: str
    median_daily_dollar_volume_est: float
    total_return_pct: float
    annualized_vol_pct: float
    avg_corr_to_all_current: float
    max_corr_to_all_current: float
    avg_corr_to_original_five: float | None
    max_corr_to_original_five: float | None


def load_ohlcv() -> tuple[dict[str, pd.DataFrame], pd.Timestamp]:
    frames: dict[str, pd.DataFrame] = {}
    max_end: pd.Timestamp | None = None
    for path in sorted(DATA_DIR.glob("*_USDC_USDC-1h-futures.feather")):
        coin = path.name.split("_USDC_USDC-")[0]
        df = pd.read_feather(path)
        if df.empty:
            continue
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.sort_values("date").drop_duplicates("date").reset_index(drop=True)
        frames[coin] = df
        end = df["date"].iloc[-1]
        max_end = end if max_end is None else max(max_end, end)
    if max_end is None:
        raise RuntimeError(f"No 1h Hyperliquid futures data found under {DATA_DIR}")
    return frames, max_end


def daily_close(df: pd.DataFrame) -> pd.Series:
    return df.set_index("date")["close"].resample("1D").last().dropna()


def median_daily_dollar_volume(df: pd.DataFrame) -> float:
    dollar_volume = df.set_index("date")["volume"] * df.set_index("date")["close"]
    return float(dollar_volume.resample("1D").sum().median())


def pairwise_values(corr: pd.DataFrame, coins: list[str]) -> pd.Series:
    matrix = corr.loc[coins, coins]
    mask = np.triu(np.ones(matrix.shape), 1).astype(bool)
    return matrix.where(mask).stack()


def greedy_select(
    corr: pd.DataFrame,
    pool: list[str],
    seed: list[str],
    size: int,
    max_corr_penalty: float,
) -> list[str]:
    chosen = [coin for coin in seed if coin in pool]
    while len(chosen) < size:
        best: tuple[float, str] | None = None
        for coin in pool:
            if coin in chosen:
                continue
            candidate = chosen + [coin]
            values = pairwise_values(corr, candidate)
            score = float(values.mean()) + max_corr_penalty * float(values.max())
            if best is None or score < best[0]:
                best = (score, coin)
        if best is None:
            break
        chosen.append(best[1])
    return chosen


def render_corr(corr: pd.DataFrame, coins: list[str], out_path: Path) -> None:
    matrix = corr.loc[coins, coins]
    fig, ax = plt.subplots(figsize=(9.5, 8.0), dpi=180)
    im = ax.imshow(matrix, vmin=-0.2, vmax=1.0, cmap="RdBu_r")
    ax.set_xticks(range(len(coins)), labels=coins, rotation=45, ha="right")
    ax.set_yticks(range(len(coins)), labels=coins)
    ax.set_title("Daily Return Correlation - Selected Hyperliquid Universe")
    for i, row in enumerate(coins):
        for j, col in enumerate(coins):
            val = matrix.loc[row, col]
            color = "white" if val > 0.62 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8, color=color)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)


def render_prices(prices: pd.DataFrame, coins: list[str], out_path: Path) -> None:
    normalized = prices.loc[:, coins] / prices.loc[:, coins].iloc[0]
    fig, ax = plt.subplots(figsize=(12.0, 7.0), dpi=180)
    for coin in coins:
        ax.plot(normalized.index, normalized[coin], linewidth=1.8, label=coin)
    ax.set_yscale("log")
    ax.set_title("Normalized Daily Closes - Selected Hyperliquid Universe")
    ax.set_ylabel("Growth of $1, log scale")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(ncol=5, fontsize=8, frameon=False)
    fig.autofmt_xdate()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--size", type=int, default=9)
    parser.add_argument("--min-dollar-volume", type=float, default=1_000_000)
    parser.add_argument("--min-rows", type=int, default=4_800)
    parser.add_argument("--max-end-lag-hours", type=float, default=24.0)
    parser.add_argument("--seed", nargs="+", default=["BTC", "HYPE"])
    parser.add_argument("--exclude", nargs="*", default=DEFAULT_EXCLUDE)
    parser.add_argument("--max-corr-penalty", type=float, default=0.10)
    args = parser.parse_args()

    frames, max_end = load_ohlcv()
    current_cutoff = max_end - pd.Timedelta(hours=args.max_end_lag_hours)
    current = {
        coin: df
        for coin, df in frames.items()
        if len(df) >= args.min_rows and df["date"].iloc[-1] >= current_cutoff
    }

    closes = {coin: daily_close(df).rename(coin) for coin, df in current.items()}
    prices = pd.concat(closes.values(), axis=1).dropna(how="any")
    returns = prices.pct_change().dropna()
    corr = returns.corr()

    volumes = {coin: median_daily_dollar_volume(df) for coin, df in current.items()}
    exclude = set(args.exclude)
    pool = sorted(
        [
            coin
            for coin in current
            if coin not in exclude and volumes[coin] >= args.min_dollar_volume
        ]
    )
    selected = greedy_select(
        corr=corr,
        pool=pool,
        seed=args.seed,
        size=args.size,
        max_corr_penalty=args.max_corr_penalty,
    )

    original = ["BTC", "ETH", "HYPE", "XRP", "SOL"]
    stats: list[CoinStats] = []
    for coin in sorted(current):
        df = current[coin]
        peer_corr = corr[coin].drop(coin)
        original_peers = [c for c in original if c in corr.index and c != coin]
        original_corr = corr.loc[coin, original_peers] if original_peers else None
        stats.append(
            CoinStats(
                coin=coin,
                rows=int(len(df)),
                start=str(df["date"].iloc[0]),
                end=str(df["date"].iloc[-1]),
                median_daily_dollar_volume_est=volumes[coin],
                total_return_pct=float((prices[coin].iloc[-1] / prices[coin].iloc[0] - 1) * 100),
                annualized_vol_pct=float(returns[coin].std() * np.sqrt(365) * 100),
                avg_corr_to_all_current=float(peer_corr.mean()),
                max_corr_to_all_current=float(peer_corr.max()),
                avg_corr_to_original_five=float(original_corr.mean()) if original_corr is not None else None,
                max_corr_to_original_five=float(original_corr.max()) if original_corr is not None else None,
            )
        )

    selected_values = pairwise_values(corr, selected)
    original_values = pairwise_values(corr, [coin for coin in original if coin in corr.index])
    payload = {
        "method": {
            "timeframe": "1h",
            "return_frequency": "daily close-to-close",
            "current_filter": {
                "min_rows": args.min_rows,
                "latest_end": str(max_end),
                "max_end_lag_hours": args.max_end_lag_hours,
            },
            "liquidity_filter": {
                "min_median_daily_dollar_volume_est": args.min_dollar_volume,
            },
            "selection": {
                "seed": args.seed,
                "excluded": sorted(exclude),
                "size": args.size,
                "score": "avg_pairwise_corr + max_corr_penalty * max_pairwise_corr",
                "max_corr_penalty": args.max_corr_penalty,
            },
        },
        "counts": {
            "local_1h_files": len(frames),
            "current_fullish": len(current),
            "liquid_current_pool": len(pool),
        },
        "common_window": {
            "start": str(prices.index.min()),
            "end": str(prices.index.max()),
            "n_daily_prices": int(len(prices)),
            "n_daily_returns": int(len(returns)),
        },
        "original_five": {
            "coins": original,
            "avg_pairwise_corr": float(original_values.mean()),
            "max_pairwise_corr": float(original_values.max()),
            "min_pairwise_corr": float(original_values.min()),
        },
        "selected_universe": {
            "coins": selected,
            "avg_pairwise_corr": float(selected_values.mean()),
            "max_pairwise_corr": float(selected_values.max()),
            "min_pairwise_corr": float(selected_values.min()),
            "pearson_corr": corr.loc[selected, selected].round(4).to_dict(),
        },
        "ranked_current": [
            asdict(row)
            for row in sorted(stats, key=lambda row: row.avg_corr_to_all_current)
        ],
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = RESULTS_DIR / "universe_selection_hl_1h_current.json"
    out_json.write_text(json.dumps(payload, indent=2))

    render_corr(corr, selected, ASSETS_DIR / "universe_selection_corr_current.png")
    render_prices(prices, selected, ASSETS_DIR / "universe_selection_prices_current.png")

    print(f"current/full-ish coins: {len(current)}")
    print(f"liquid current pool: {len(pool)}")
    print(f"selected: {', '.join(selected)}")
    print(
        "selected corr: "
        f"avg={selected_values.mean():.3f}, "
        f"max={selected_values.max():.3f}, "
        f"min={selected_values.min():.3f}"
    )
    print(f"wrote {out_json}")
    print(f"wrote {ASSETS_DIR / 'universe_selection_corr_current.png'}")
    print(f"wrote {ASSETS_DIR / 'universe_selection_prices_current.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
