#!/usr/bin/env python3
"""Run a daily LSTM + Twitter-sentiment research backtest."""
from __future__ import annotations

import argparse
import json
import math
import os
import urllib.request
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/backtesting-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/backtesting-cache")

import matplotlib
import numpy as np
import pandas as pd
import torch
from torch import nn

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


REPO = Path(__file__).resolve().parent.parent
HL_DATA_DIRS = [
    REPO.parent / "hmm-slope-experiment" / "research" / "data" / "hyperliquid" / "futures",
]
SENTIMENT_DIR = REPO / "state" / "sentiment"
RESULTS_DIR = REPO / "analysis" / "results"
ASSETS_DIR = RESULTS_DIR

MV_COINS = ["BTC", "HYPE", "PAXG", "TRX", "WLFI", "VVV", "TON", "ZRO", "XPL"]
LOWER_CAP_COINS = ["FARTCOIN", "WIF", "POPCAT", "KPEPE", "KBONK", "KSHIB", "KFLOKI", "SPX", "PENGU", "PNUT", "BRETT", "MELANIA"]
VVV_XPL_COINS = ["VVV", "XPL"]

SLUGS = {
    "BTC": "bitcoin",
    "HYPE": "hyperliquid",
    "PAXG": "pax-gold",
    "TRX": "tron",
    "WLFI": "world-liberty-financial-wlfi",
    "VVV": "venice-token",
    "TON": "tontoken",
    "ZRO": "layerzero",
    "XPL": "bnb-plasma-xpl",
    "FARTCOIN": "fartcoin",
    "WIF": "dogwifhat",
    "POPCAT": "popcat-sol",
    "KPEPE": "pepe",
    "KBONK": "bonk1",
    "KSHIB": "shiba-inu",
    "KFLOKI": "floki-inu-v2",
    "SPX": "spx6900",
    "PENGU": "pudgy-penguins",
    "PNUT": "peanut-the-squirrel",
    "BRETT": "based-brett",
    "MELANIA": "melania-meme",
}

WINDOW = 50
MIN_DAYS = 120
MIN_TEST_DAYS = 60
MIN_SENTIMENT_COVERAGE = 0.80
FEE = 0.00035
ENTRY_THRESHOLD = 0.002
SENTIMENT_SCALE = 0.0025


class ReturnLstm(nn.Module):
    def __init__(self, n_features: int, hidden: int = 16) -> None:
        super().__init__()
        self.lstm = nn.LSTM(n_features, hidden, batch_first=True)
        self.out = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y, _ = self.lstm(x)
        return self.out(y[:, -1, :]).squeeze(-1)


def load_hourly(coin: str) -> pd.DataFrame | None:
    for data_dir in HL_DATA_DIRS:
        path = data_dir / f"{coin}_USDC_USDC-1h-futures.feather"
        if path.exists():
            df = pd.read_feather(path)
            df["date"] = pd.to_datetime(df["date"], utc=True)
            return df.sort_values("date").drop_duplicates("date")
    return None


def load_daily_ohlcv(coin: str) -> pd.DataFrame | None:
    hourly = load_hourly(coin)
    if hourly is None:
        return None
    daily = (
        hourly.set_index("date")
        .resample("1D")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
    )
    return daily if len(daily) >= MIN_DAYS else None


def santiment_query(slug: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    SENTIMENT_DIR.mkdir(parents=True, exist_ok=True)
    cache = SENTIMENT_DIR / f"{slug}-sentiment_weighted_twitter_1d-{start.date()}-{end.date()}.csv"
    if cache.exists():
        return pd.read_csv(cache, parse_dates=["date"]).set_index("date")

    query = """
    query($slug: String!, $from: DateTime!, $to: DateTime!) {
      getMetric(metric: "sentiment_weighted_twitter_1d") {
        timeseriesData(slug: $slug, from: $from, to: $to, interval: "1d") {
          datetime
          value
        }
      }
    }
    """
    payload = {
        "query": query,
        "variables": {
            "slug": slug,
            "from": start.strftime("%Y-%m-%dT00:00:00Z"),
            "to": end.strftime("%Y-%m-%dT00:00:00Z"),
        },
    }
    request = urllib.request.Request(
        "https://api.santiment.net/graphql",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "backtesting-research/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode())
    rows = data.get("data", {}).get("getMetric", {}).get("timeseriesData")
    if not rows:
        errors = data.get("errors") or []
        msg = "; ".join(error.get("message", "") for error in errors)
        raise RuntimeError(msg or f"no sentiment rows for {slug}")

    out = pd.DataFrame(rows).rename(columns={"datetime": "date"})
    out["date"] = pd.to_datetime(out["date"], utc=True)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.dropna().set_index("date").sort_index()
    out.to_csv(cache, index_label="date")
    return out


def feature_frame(daily: pd.DataFrame, sentiment: pd.Series) -> pd.DataFrame:
    df = daily.copy()
    out = pd.DataFrame(index=df.index)
    out["ret"] = np.log(df["close"]).diff()
    out["range"] = (df["high"] - df["low"]) / df["close"]
    out["oc"] = (df["close"] - df["open"]) / df["open"]
    out["vol_chg"] = np.log1p(df["volume"]).diff()
    sent = sentiment.reindex(out.index).ffill()
    sent_smooth = sent.rolling(7, min_periods=3).mean()
    sent_mean = sent_smooth.rolling(60, min_periods=20).mean()
    sent_std = sent_smooth.rolling(60, min_periods=20).std().replace(0, np.nan)
    out["sent_z_signal"] = ((sent_smooth - sent_mean) / sent_std).shift(1)
    out["target_ret"] = df["close"].pct_change()
    return out.replace([np.inf, -np.inf], np.nan)


def build_sequences(features: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex, pd.Series]:
    model_cols = ["ret", "range", "oc", "vol_chg"]
    x_rows = []
    y_rows = []
    dates = []
    sent = []
    for idx in range(WINDOW, len(features)):
        window = features.iloc[idx - WINDOW:idx]
        row = features.iloc[idx]
        if window[model_cols].isna().any().any() or not np.isfinite(row["target_ret"]):
            continue
        x_rows.append(window[model_cols].to_numpy(dtype=np.float32))
        y_rows.append(float(row["target_ret"]))
        dates.append(features.index[idx])
        sent.append(float(row["sent_z_signal"]) if np.isfinite(row["sent_z_signal"]) else 0.0)
    return np.asarray(x_rows), np.asarray(y_rows, dtype=np.float32), pd.DatetimeIndex(dates), pd.Series(sent, index=dates)


def fit_predict(x: np.ndarray, y: np.ndarray, train_n: int, epochs: int, seed: int) -> np.ndarray:
    x_train = x[:train_n]
    y_train = y[:train_n]
    mean = x_train.reshape(-1, x_train.shape[-1]).mean(axis=0)
    std = x_train.reshape(-1, x_train.shape[-1]).std(axis=0)
    std[std < 1e-8] = 1.0
    x_scaled = (x - mean) / std

    torch.manual_seed(seed)
    model = ReturnLstm(x.shape[-1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01, weight_decay=1e-4)
    loss_fn = nn.MSELoss()
    xt = torch.tensor(x_scaled[:train_n], dtype=torch.float32)
    yt = torch.tensor(y_train, dtype=torch.float32)
    for _ in range(epochs):
        model.train()
        optimizer.zero_grad()
        loss = loss_fn(model(xt), yt)
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        return model(torch.tensor(x_scaled, dtype=torch.float32)).numpy()


def position_returns(position: pd.Series, returns: pd.Series) -> pd.Series:
    position = position.reindex(returns.index).fillna(0.0)
    turnover = position.diff().abs()
    if len(turnover):
        turnover.iloc[0] = abs(position.iloc[0])
    return position * returns - turnover * FEE


def max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1.0).min())


def metrics(returns: pd.Series, exposure: pd.Series, turnover: pd.Series | None = None) -> dict:
    returns = returns.dropna()
    if returns.empty:
        return {}
    equity = (1.0 + returns).cumprod()
    days = len(returns)
    total = float(equity.iloc[-1] - 1.0)
    cagr = float(equity.iloc[-1] ** (365.0 / days) - 1.0) if equity.iloc[-1] > 0 else -1.0
    std = float(returns.std())
    mdd = max_drawdown(equity)
    return {
        "days": int(days),
        "total_return_pct": total * 100.0,
        "cagr_pct": cagr * 100.0,
        "sharpe": float(returns.mean() / std * math.sqrt(365.0)) if std > 0 else float("nan"),
        "max_drawdown_pct": mdd * 100.0,
        "calmar": cagr / abs(mdd) if mdd < 0 else float("nan"),
        "avg_exposure": float(exposure.abs().mean()),
        "avg_turnover": float(turnover.mean()) if turnover is not None and len(turnover) else float("nan"),
    }


def run_coin(coin: str, epochs: int, seed: int) -> dict:
    daily = load_daily_ohlcv(coin)
    if daily is None:
        return {"coin": coin, "status": "skip", "reason": "missing or short OHLCV"}
    slug = SLUGS.get(coin)
    if not slug:
        return {"coin": coin, "status": "skip", "reason": "missing Santiment slug"}
    sentiment = santiment_query(slug, daily.index.min(), daily.index.max())["value"]
    overlap = daily.index.intersection(sentiment.index)
    coverage = len(overlap) / len(daily)
    if coverage < MIN_SENTIMENT_COVERAGE:
        return {"coin": coin, "status": "skip", "reason": f"sentiment coverage {coverage:.1%}", "slug": slug}

    features = feature_frame(daily, sentiment)
    x, y, dates, sent_z = build_sequences(features)
    if len(y) < MIN_TEST_DAYS + 40:
        return {"coin": coin, "status": "skip", "reason": f"only {len(y)} usable samples", "slug": slug, "coverage": coverage}

    train_n = max(40, int(len(y) * 0.60))
    test_n = len(y) - train_n
    if test_n < MIN_TEST_DAYS:
        return {"coin": coin, "status": "skip", "reason": f"only {test_n} test days", "slug": slug, "coverage": coverage}

    pred = pd.Series(fit_predict(x, y, train_n, epochs, seed), index=dates)
    actual = pd.Series(y, index=dates)
    test_idx = dates[train_n:]
    lstm_pos = pd.Series(np.where(pred.loc[test_idx] > ENTRY_THRESHOLD, 1.0, np.where(pred.loc[test_idx] < -ENTRY_THRESHOLD, -1.0, 0.0)), index=test_idx)
    fused_score = pred.loc[test_idx] + SENTIMENT_SCALE * sent_z.loc[test_idx].clip(-3.0, 3.0)
    fused_pos = pd.Series(np.where(fused_score > ENTRY_THRESHOLD, 1.0, np.where(fused_score < -ENTRY_THRESHOLD, -1.0, 0.0)), index=test_idx)

    lstm_ret = position_returns(lstm_pos, actual.loc[test_idx])
    fused_ret = position_returns(fused_pos, actual.loc[test_idx])
    return {
        "coin": coin,
        "status": "ok",
        "slug": slug,
        "coverage": coverage,
        "daily_rows": int(len(daily)),
        "usable_samples": int(len(y)),
        "train_days": int(train_n),
        "test_days": int(test_n),
        "start": str(test_idx.min().date()),
        "end": str(test_idx.max().date()),
        "lstm_only": metrics(lstm_ret, lstm_pos, lstm_pos.diff().abs()),
        "lstm_twitter": metrics(fused_ret, fused_pos, fused_pos.diff().abs()),
        "returns": {
            "actual": actual.loc[test_idx],
            "lstm_only": lstm_ret,
            "lstm_twitter": fused_ret,
            "lstm_position": lstm_pos,
            "twitter_position": fused_pos,
        },
    }


def aggregate(results: list[dict], coins: list[str], key: str) -> dict:
    series = aggregate_series(results, coins, key)
    if series is None:
        return {}
    return metrics(series["portfolio_return"], series["exposure"], series["turnover"])


def aggregate_series(results: list[dict], coins: list[str], key: str) -> pd.DataFrame | None:
    ok = [r for r in results if r["status"] == "ok" and r["coin"] in coins]
    if not ok:
        return None
    returns = pd.concat([r["returns"][key].rename(r["coin"]) for r in ok], axis=1).fillna(0.0)
    positions = pd.concat(
        [
            (r["returns"]["lstm_position"] if key == "lstm_only" else r["returns"]["twitter_position"]).rename(r["coin"])
            for r in ok
        ],
        axis=1,
    ).fillna(0.0)
    active = positions.abs().sum(axis=1).replace(0.0, np.nan)
    weights = positions.div(active, axis=0).fillna(0.0)
    gross_turnover = weights.diff().abs().sum(axis=1)
    gross_turnover.iloc[0] = weights.iloc[0].abs().sum()
    asset_rets = pd.concat([r["returns"]["actual"].rename(r["coin"]) for r in ok], axis=1).reindex(weights.index).fillna(0.0)
    portfolio_returns = (weights * asset_rets).sum(axis=1) - gross_turnover * FEE
    out = pd.concat(
        [
            portfolio_returns.rename("portfolio_return"),
            weights.abs().sum(axis=1).rename("exposure"),
            gross_turnover.rename("turnover"),
            weights.add_prefix("weight_"),
            asset_rets.add_prefix("asset_return_"),
        ],
        axis=1,
    )
    return out


def clean_result(result: dict) -> dict:
    out = {k: v for k, v in result.items() if k != "returns"}
    return out


def fmt(value: float, pct: bool = False) -> str:
    if value is None or not np.isfinite(value):
        return "nan"
    return f"{value:.2f}%" if pct else f"{value:.2f}"


def rolling_sharpe(returns: pd.Series, window: int = 30) -> pd.Series:
    mean = returns.rolling(window).mean()
    std = returns.rolling(window).std()
    return mean / std.replace(0.0, np.nan) * math.sqrt(365.0)


def render_diagnostics(results: list[dict]) -> dict[str, Path]:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    mv_lstm = aggregate_series(results, MV_COINS, "lstm_only")
    mv_twitter = aggregate_series(results, MV_COINS, "lstm_twitter")
    lower_twitter = aggregate_series(results, LOWER_CAP_COINS, "lstm_twitter")
    vvv_xpl_twitter = aggregate_series(results, VVV_XPL_COINS, "lstm_twitter")
    if mv_lstm is None or mv_twitter is None or lower_twitter is None or vvv_xpl_twitter is None:
        return {}

    diagnostics = pd.DataFrame(index=mv_twitter.index)
    for name, frame in [
        ("mv_lstm_only", mv_lstm),
        ("mv_lstm_twitter", mv_twitter),
        ("lower_lstm_twitter", lower_twitter),
        ("vvv_xpl_lstm_twitter", vvv_xpl_twitter),
    ]:
        returns = frame["portfolio_return"].reindex(diagnostics.index).fillna(0.0)
        equity = (1.0 + returns).cumprod()
        diagnostics[f"{name}_return"] = returns
        diagnostics[f"{name}_equity"] = equity
        diagnostics[f"{name}_pnl"] = equity - 1.0
        diagnostics[f"{name}_drawdown"] = equity / equity.cummax() - 1.0
        diagnostics[f"{name}_rolling_sharpe_30d"] = rolling_sharpe(returns, 30)
        diagnostics[f"{name}_turnover"] = frame["turnover"].reindex(diagnostics.index).fillna(0.0)

    per_coin = []
    for r in results:
        if r["status"] != "ok":
            continue
        per_coin.append(
            {
                "coin": r["coin"],
                "universe": "MV" if r["coin"] in MV_COINS else "Lower-cap",
                "lstm_only_return_pct": r["lstm_only"]["total_return_pct"],
                "lstm_twitter_return_pct": r["lstm_twitter"]["total_return_pct"],
                "lstm_twitter_sharpe": r["lstm_twitter"]["sharpe"],
                "lstm_twitter_mdd_pct": r["lstm_twitter"]["max_drawdown_pct"],
                "lstm_twitter_calmar": r["lstm_twitter"]["calmar"],
            }
        )
    per_coin_df = pd.DataFrame(per_coin).sort_values("lstm_twitter_return_pct", ascending=False)

    out_csv = RESULTS_DIR / "lstm_twitter_sentiment_diagnostics_current.csv"
    out_coin_csv = RESULTS_DIR / "lstm_twitter_sentiment_per_coin_current.csv"
    out_png = ASSETS_DIR / "lstm_twitter_sentiment_diagnostics_current.png"
    out_coin_png = ASSETS_DIR / "lstm_twitter_sentiment_per_coin_current.png"
    out_vvv_xpl_png = ASSETS_DIR / "lstm_twitter_sentiment_vvv_xpl_current.png"
    diagnostics.to_csv(out_csv, index_label="date")
    per_coin_df.to_csv(out_coin_csv, index=False)

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(15, 10.5),
        sharex=True,
        gridspec_kw={"height_ratios": [2.0, 1.2, 1.2]},
    )
    fig.suptitle("LSTM + Twitter Sentiment Diagnostics", fontsize=16, fontweight="bold", y=0.985)
    ax = axes[0]
    ax.plot(diagnostics.index, diagnostics["mv_lstm_only_pnl"] * 100.0, label="MV LSTM-only", linewidth=1.9)
    ax.plot(diagnostics.index, diagnostics["mv_lstm_twitter_pnl"] * 100.0, label="MV LSTM+Twitter", linewidth=2.3)
    ax.plot(diagnostics.index, diagnostics["lower_lstm_twitter_pnl"] * 100.0, label="Lower-cap LSTM+Twitter", linewidth=1.8)
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title("PnL Over Time")
    ax.set_ylabel("PnL (%)")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False, ncol=3)

    ax = axes[1]
    ax.plot(diagnostics.index, diagnostics["mv_lstm_twitter_drawdown"] * 100.0, label="MV LSTM+Twitter", linewidth=2.0)
    ax.plot(diagnostics.index, diagnostics["lower_lstm_twitter_drawdown"] * 100.0, label="Lower-cap LSTM+Twitter", linewidth=1.8)
    ax.fill_between(diagnostics.index, diagnostics["mv_lstm_twitter_drawdown"] * 100.0, 0.0, alpha=0.14)
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title("Drawdown")
    ax.set_ylabel("Drawdown (%)")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False, ncol=2)

    ax = axes[2]
    ax.plot(diagnostics.index, diagnostics["mv_lstm_twitter_rolling_sharpe_30d"], label="MV LSTM+Twitter", linewidth=2.0)
    ax.plot(diagnostics.index, diagnostics["lower_lstm_twitter_rolling_sharpe_30d"], label="Lower-cap LSTM+Twitter", linewidth=1.8)
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title("30D Rolling Sharpe, Annualized")
    ax.set_ylabel("Sharpe")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False, ncol=2)
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.set_xlabel("Date")
    fig.subplots_adjust(top=0.92, bottom=0.07, hspace=0.45)
    fig.savefig(out_png, dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(14, 6.5))
    x = np.arange(len(per_coin_df))
    width = 0.38
    ax.bar(x - width / 2, per_coin_df["lstm_only_return_pct"], width, label="LSTM-only", color="#7f7f7f")
    ax.bar(x + width / 2, per_coin_df["lstm_twitter_return_pct"], width, label="LSTM+Twitter", color="#1f77b4")
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(per_coin_df["coin"], rotation=45, ha="right")
    ax.set_ylabel("Total Return (%)")
    ax.set_title("Per-Coin Return: LSTM-only vs LSTM+Twitter")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_coin_png, dpi=180)
    plt.close(fig)

    vvv = next(r for r in results if r.get("coin") == "VVV" and r["status"] == "ok")
    xpl = next(r for r in results if r.get("coin") == "XPL" and r["status"] == "ok")
    fig, axes = plt.subplots(3, 1, figsize=(15, 10.5), sharex=True)
    fig.suptitle("VVV / XPL Focus: LSTM + Twitter Sentiment", fontsize=16, fontweight="bold", y=0.985)
    ax = axes[0]
    for r, color in [(vvv, "#2ca02c"), (xpl, "#ff7f0e")]:
        equity = (1.0 + r["returns"]["lstm_twitter"]).cumprod()
        ax.plot(equity.index, (equity - 1.0) * 100.0, label=f"{r['coin']} standalone", linewidth=2.0, color=color)
    ax.plot(diagnostics.index, diagnostics["vvv_xpl_lstm_twitter_pnl"] * 100.0, label="Equal-active VVV/XPL", linewidth=2.4, color="#1f77b4")
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title("PnL Over Time")
    ax.set_ylabel("PnL (%)")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False, ncol=3)

    ax = axes[1]
    for r, color in [(vvv, "#2ca02c"), (xpl, "#ff7f0e")]:
        ax.step(r["returns"]["twitter_position"].index, r["returns"]["twitter_position"], where="post", label=r["coin"], linewidth=1.9, color=color)
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title("Daily Position Signal")
    ax.set_ylabel("Position")
    ax.set_yticks([-1, 0, 1])
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False, ncol=2)

    ax = axes[2]
    vvv_xpl_returns = vvv_xpl_twitter["portfolio_return"]
    vvv_xpl_equity = (1.0 + vvv_xpl_returns).cumprod()
    ax.plot(vvv_xpl_equity.index, (vvv_xpl_equity / vvv_xpl_equity.cummax() - 1.0) * 100.0, linewidth=2.0, color="#d62728")
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title("Equal-Active VVV/XPL Drawdown")
    ax.set_ylabel("Drawdown (%)")
    ax.grid(True, alpha=0.25)
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.set_xlabel("Date")
    fig.subplots_adjust(top=0.92, bottom=0.07, hspace=0.45)
    fig.savefig(out_vvv_xpl_png, dpi=180)
    plt.close(fig)

    return {
        "diagnostics_csv": out_csv,
        "per_coin_csv": out_coin_csv,
        "diagnostics_png": out_png,
        "per_coin_png": out_coin_png,
        "vvv_xpl_png": out_vvv_xpl_png,
    }


def write_outputs(results: list[dict], mv: dict, lower: dict, vvv_xpl: dict, chart_paths: dict[str, Path]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "method": {
            "window": WINDOW,
            "train_fraction": 0.60,
            "entry_threshold": ENTRY_THRESHOLD,
            "sentiment_scale": SENTIMENT_SCALE,
            "fee": FEE,
            "sentiment_metric": "santiment:sentiment_weighted_twitter_1d",
            "data_gate": {
                "min_days": MIN_DAYS,
                "min_test_days": MIN_TEST_DAYS,
                "min_sentiment_coverage": MIN_SENTIMENT_COVERAGE,
            },
        },
        "universes": {"mv": MV_COINS, "lower_cap": LOWER_CAP_COINS, "vvv_xpl": VVV_XPL_COINS},
        "aggregate": {"mv": mv, "lower_cap": lower, "vvv_xpl": vvv_xpl},
        "artifacts": {key: str(path.relative_to(REPO)) for key, path in chart_paths.items()},
        "coins": [clean_result(r) for r in results],
    }
    json_path = RESULTS_DIR / "lstm_twitter_sentiment_hl_1d_current.json"
    json_path.write_text(json.dumps(payload, indent=2, default=str) + "\n")

    lines = [
        "# LSTM Twitter Sentiment Probe",
        "",
        "Daily Hyperliquid OHLCV plus Santiment `sentiment_weighted_twitter_1d`.",
        "",
        "Charts: [diagnostics](../assets/lstm_twitter_sentiment_diagnostics_current.png), [per-coin returns](../assets/lstm_twitter_sentiment_per_coin_current.png), [VVV/XPL focus](../assets/lstm_twitter_sentiment_vvv_xpl_current.png).",
        "",
        "## Aggregate",
        "",
        "| Universe | Strategy | Days | Return | Sharpe | MDD | Calmar | Avg Exposure | Turnover |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for universe_name, rows in [("MV", mv), ("Lower-cap", lower), ("VVV/XPL", vvv_xpl)]:
        for strategy_name, row in rows.items():
            lines.append(
                f"| {universe_name} | {strategy_name} | {row.get('days', 0)} | "
                f"{fmt(row.get('total_return_pct', float('nan')), True)} | {fmt(row.get('sharpe', float('nan')))} | "
                f"{fmt(row.get('max_drawdown_pct', float('nan')), True)} | {fmt(row.get('calmar', float('nan')))} | "
                f"{fmt(row.get('avg_exposure', float('nan')))} | {fmt(row.get('avg_turnover', float('nan')))} |"
            )
    lines.extend([
        "",
        "## Per Coin",
        "",
        "| Coin | Status | Coverage | Test | LSTM Return | LSTM Sharpe | LSTM+Twitter Return | LSTM+Twitter Sharpe | Reason |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ])
    for r in results:
        if r["status"] != "ok":
            lines.append(f"| {r['coin']} | {r['status']} | | | | | | | {r.get('reason', '')} |")
            continue
        lines.append(
            f"| {r['coin']} | ok | {r['coverage']:.1%} | {r['test_days']} | "
            f"{fmt(r['lstm_only']['total_return_pct'], True)} | {fmt(r['lstm_only']['sharpe'])} | "
            f"{fmt(r['lstm_twitter']['total_return_pct'], True)} | {fmt(r['lstm_twitter']['sharpe'])} | |"
        )
    md_path = RESULTS_DIR / "lstm_twitter_sentiment_hl_1d_current.md"
    md_path.write_text("\n".join(lines) + "\n")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    torch.set_num_threads(1)
    np.random.seed(args.seed)

    coins = MV_COINS + LOWER_CAP_COINS
    results = []
    for coin in coins:
        try:
            result = run_coin(coin, args.epochs, args.seed)
        except Exception as exc:
            result = {"coin": coin, "status": "skip", "reason": str(exc)}
        results.append(result)
        print(f"{coin}: {result['status']} {result.get('reason', '')}".rstrip())

    mv = {
        "lstm_only": aggregate(results, MV_COINS, "lstm_only"),
        "lstm_twitter": aggregate(results, MV_COINS, "lstm_twitter"),
    }
    lower = {
        "lstm_only": aggregate(results, LOWER_CAP_COINS, "lstm_only"),
        "lstm_twitter": aggregate(results, LOWER_CAP_COINS, "lstm_twitter"),
    }
    vvv_xpl = {
        "lstm_only": aggregate(results, VVV_XPL_COINS, "lstm_only"),
        "lstm_twitter": aggregate(results, VVV_XPL_COINS, "lstm_twitter"),
    }
    chart_paths = render_diagnostics(results)
    write_outputs(results, mv, lower, vvv_xpl, chart_paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
