#!/usr/bin/env python3
"""Walk-forward BTC regime inference with a truncated DP mixture.

This is intentionally analysis-only. Each predicted regime is assigned by a
model fit on prior rows only, with scalers and semantic labels also fit only on
that training window. The inferred regime for a daily candle is therefore known
after that candle closes and is usable for the next candle.
"""
from __future__ import annotations

import argparse
import json
import os
import warnings
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/backtesting-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/backtesting-cache")

import matplotlib
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.mixture import BayesianGaussianMixture
from sklearn.preprocessing import StandardScaler

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt


REPO = Path(__file__).resolve().parent.parent
DEFAULT_PRICE_PATH = (
    REPO / "data/binance/futures/BTC_USDT_USDT-1d-futures.feather"
)
DEFAULT_FUNDING_PATH = (
    REPO / "data/binance/futures/BTC_USDT_USDT-8h-funding_rate.feather"
)
DEFAULT_CSV_PATH = REPO / "analysis/reports/btc_dp_regimes.csv"
DEFAULT_JSON_PATH = REPO / "analysis/reports/btc_dp_regime_summary.json"
DEFAULT_CHART_PATH = REPO / "analysis/reports/btc_dp_regimes.png"

FEATURE_COLUMNS = [
    "ret_1d",
    "ret_7d",
    "ret_30d",
    "rv_7d",
    "rv_30d",
    "range_7d",
    "sma50_dist",
    "sma100_dist",
    "sma50_slope_20d",
    "log_volume",
    "funding_7d",
    "funding_30d",
]

REGIME_COLORS = {
    "bull": "#2ca02c",
    "volatile_bull": "#17becf",
    "recovery": "#8bc34a",
    "chop": "#7f7f7f",
    "drawdown": "#ff7f0e",
    "stress": "#d62728",
    "unlabeled": "#d9d9d9",
}


@dataclass(frozen=True)
class RunConfig:
    price_path: Path
    funding_path: Path | None
    output_csv: Path
    output_json: Path
    output_chart: Path
    min_train: int
    train_window: int
    refit_every: int
    max_regimes: int
    min_segment_days: int
    random_state: int


def as_utc_ns(values: pd.Series | pd.DatetimeIndex) -> pd.Series | pd.DatetimeIndex:
    converted = pd.to_datetime(values, utc=True)
    if isinstance(converted, pd.Series):
        return converted.dt.as_unit("ns")
    return converted.as_unit("ns")


def load_prices(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_feather(path)
    df["date"] = as_utc_ns(df["date"])
    df = df.sort_values("date").drop_duplicates("date")
    cols = ["open", "high", "low", "close", "volume"]
    df[cols] = df[cols].astype(float)
    return df.set_index("date")[cols]


def load_daily_funding(path: Path | None, index: pd.DatetimeIndex) -> pd.Series:
    if path is None or not path.exists():
        return pd.Series(0.0, index=index, name="funding")

    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
        time_col = "time"
        value_col = "funding_rate"
    else:
        df = pd.read_feather(path)
        time_col = "date"
        value_col = "open"

    df[time_col] = as_utc_ns(df[time_col])
    daily = df.set_index(time_col)[value_col].astype(float).resample("1D").sum()
    daily.index = as_utc_ns(daily.index)
    return daily.reindex(index).fillna(0.0).rename("funding")


def build_features(prices: pd.DataFrame, funding: pd.Series) -> pd.DataFrame:
    close = prices["close"]
    log_close = np.log(close)
    ret_1d = log_close.diff()
    log_volume = np.log(prices["volume"].clip(lower=1e-9))

    features = pd.DataFrame(index=prices.index)
    features["close"] = close
    features["ret_1d"] = ret_1d
    features["ret_7d"] = log_close.diff(7)
    features["ret_30d"] = log_close.diff(30)
    features["rv_7d"] = ret_1d.rolling(7).std() * np.sqrt(365.0)
    features["rv_30d"] = ret_1d.rolling(30).std() * np.sqrt(365.0)
    features["range_7d"] = np.log(prices["high"] / prices["low"]).rolling(7).mean()
    features["sma50_dist"] = close / close.rolling(50).mean() - 1.0
    features["sma100_dist"] = close / close.rolling(100).mean() - 1.0
    features["sma50_slope_20d"] = np.log(close.rolling(50).mean()).diff(20)
    features["log_volume"] = log_volume
    features["funding_7d"] = funding.rolling(7, min_periods=1).sum()
    features["funding_30d"] = funding.rolling(30, min_periods=1).sum()
    return features


def classify_component(profile: pd.Series, train_profiles: pd.DataFrame) -> str:
    high_vol = train_profiles["rv_30d"].quantile(0.67)
    trend = float(profile["ret_30d"] + profile["sma100_dist"])
    ret_30d = float(profile["ret_30d"])
    sma100 = float(profile["sma100_dist"])
    vol = float(profile["rv_30d"])

    if vol >= high_vol and ret_30d < -0.04:
        return "stress"
    if trend > 0.08 and sma100 > 0.0 and vol >= high_vol:
        return "volatile_bull"
    if trend > 0.08 and sma100 > 0.0:
        return "bull"
    if trend > 0.02:
        return "recovery"
    if trend < -0.08:
        return "drawdown"
    return "chop"


def component_labels(
    train_raw: pd.DataFrame,
    train_x: np.ndarray,
    model: BayesianGaussianMixture,
) -> dict[int, str]:
    train_clusters = model.predict(train_x)
    profiles = []
    for cluster in range(model.n_components):
        mask = train_clusters == cluster
        if mask.sum() < 5:
            continue
        profile = train_raw.loc[mask, FEATURE_COLUMNS].median()
        profile["cluster"] = cluster
        profile["n"] = int(mask.sum())
        profiles.append(profile)

    if not profiles:
        return {}

    profile_df = pd.DataFrame(profiles).set_index("cluster")
    labels = {}
    for cluster, profile in profile_df.iterrows():
        labels[int(cluster)] = classify_component(profile, train_raw)
    return labels


def infer_regimes(features: pd.DataFrame, config: RunConfig) -> tuple[pd.DataFrame, dict]:
    valid = features[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).dropna()
    results = pd.DataFrame(index=features.index)
    results["close"] = features["close"]
    results["regime"] = "unlabeled"
    results["regime_raw"] = "unlabeled"
    results["cluster"] = -1
    results["confidence"] = np.nan
    results["active_regimes"] = np.nan
    results["refit_date"] = ""

    if len(valid) < config.min_train + config.refit_every:
        raise ValueError("Not enough valid feature rows for requested walk-forward run.")

    valid_positions = np.flatnonzero(features.index.isin(valid.index))
    first_pos = int(valid_positions[0] + config.min_train)
    last_pos = len(features)
    refit_summaries = []

    warnings.filterwarnings("ignore", category=ConvergenceWarning)

    for refit_pos in range(first_pos, last_pos, config.refit_every):
        train_start = max(int(valid_positions[0]), refit_pos - config.train_window)
        train_slice = features.iloc[train_start:refit_pos].copy()
        train_slice = train_slice.replace([np.inf, -np.inf], np.nan).dropna(
            subset=FEATURE_COLUMNS
        )
        if len(train_slice) < config.min_train:
            continue

        scaler = StandardScaler()
        train_x = scaler.fit_transform(train_slice[FEATURE_COLUMNS])
        model = BayesianGaussianMixture(
            n_components=config.max_regimes,
            covariance_type="full",
            weight_concentration_prior_type="dirichlet_process",
            weight_concentration_prior=1.0,
            max_iter=1000,
            n_init=2,
            reg_covar=1e-5,
            random_state=config.random_state,
        )
        model.fit(train_x)
        labels = component_labels(train_slice, train_x, model)

        active = int((model.weights_ > 0.03).sum())
        refit_date = features.index[refit_pos]
        refit_summaries.append(
            {
                "refit_date": refit_date.isoformat(),
                "train_start": train_slice.index[0].isoformat(),
                "train_end": train_slice.index[-1].isoformat(),
                "train_rows": int(len(train_slice)),
                "active_regimes": active,
            }
        )

        score_end = min(refit_pos + config.refit_every, last_pos)
        score_slice = features.iloc[refit_pos:score_end].copy()
        score_slice = score_slice.replace([np.inf, -np.inf], np.nan).dropna(
            subset=FEATURE_COLUMNS
        )
        if score_slice.empty:
            continue

        score_x = scaler.transform(score_slice[FEATURE_COLUMNS])
        probs = model.predict_proba(score_x)
        clusters = probs.argmax(axis=1)
        confidence = probs.max(axis=1)

        for date, cluster, conf in zip(score_slice.index, clusters, confidence):
            results.at[date, "cluster"] = int(cluster)
            results.at[date, "confidence"] = float(conf)
            results.at[date, "active_regimes"] = active
            results.at[date, "refit_date"] = refit_date.isoformat()
            results.at[date, "regime_raw"] = labels.get(int(cluster), "chop")

    results["regime"] = smooth_regimes(results["regime_raw"], config.min_segment_days)
    summary = {
        "input": str(config.price_path),
        "funding_input": str(config.funding_path) if config.funding_path else None,
        "window": {
            "start": features.index.min().date().isoformat(),
            "end": features.index.max().date().isoformat(),
            "rows": int(len(features)),
            "valid_feature_rows": int(len(valid)),
        },
        "method": {
            "model": "sklearn BayesianGaussianMixture",
            "prior": "finite truncation of a Dirichlet-process mixture",
            "max_regimes": config.max_regimes,
            "min_train_days": config.min_train,
            "train_window_days": config.train_window,
            "refit_every_days": config.refit_every,
            "min_segment_days": config.min_segment_days,
            "leakage_policy": "fit scaler/model/labels on rows strictly before each scored segment",
        },
        "refits": refit_summaries,
        "regime_counts": results["regime"].value_counts().to_dict(),
    }
    return results, summary


def smooth_regimes(regimes: pd.Series, min_segment_days: int) -> pd.Series:
    if min_segment_days <= 1 or regimes.empty:
        return regimes.copy()

    smoothed = regimes.copy()
    segments = contiguous_segments(smoothed)
    for idx, (start, end, regime) in enumerate(segments):
        if regime == "unlabeled":
            continue
        days = (end - start).days + 1
        if days >= min_segment_days:
            continue

        replacement = None
        if idx > 0 and segments[idx - 1][2] != "unlabeled":
            replacement = segments[idx - 1][2]
        elif idx + 1 < len(segments) and segments[idx + 1][2] != "unlabeled":
            replacement = segments[idx + 1][2]
        if replacement is not None:
            smoothed.loc[start:end] = replacement
    return smoothed


def contiguous_segments(regimes: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp, str]]:
    segments = []
    start = regimes.index[0]
    current = regimes.iloc[0]
    prev = regimes.index[0]
    for date, regime in regimes.iloc[1:].items():
        if regime != current:
            segments.append((start, prev, current))
            start = date
            current = regime
        prev = date
    segments.append((start, prev, current))
    return segments


def plot_regimes(results: pd.DataFrame, output_path: Path) -> None:
    plot_df = results.copy()
    plot_df["drawdown"] = plot_df["close"] / plot_df["close"].cummax() - 1.0
    returns = np.log(plot_df["close"] / plot_df["close"].shift(1))
    plot_df["rv_30d"] = returns.rolling(30).std() * np.sqrt(365.0)

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(15, 10),
        sharex=True,
        gridspec_kw={"height_ratios": [2.0, 0.8, 1.0]},
        constrained_layout=True,
    )
    fig.suptitle(
        "BTC Walk-Forward DP Regime Inference",
        fontsize=16,
        fontweight="bold",
    )

    segments = contiguous_segments(plot_df["regime"])

    ax = axes[0]
    for start, end, regime in segments:
        ax.axvspan(
            start,
            end + pd.Timedelta(days=1),
            color=REGIME_COLORS.get(regime, REGIME_COLORS["chop"]),
            alpha=0.16 if regime != "unlabeled" else 0.22,
            linewidth=0,
        )
    ax.plot(plot_df.index, plot_df["close"], color="#111111", linewidth=1.4)
    ax.set_yscale("log")
    ax.set_title("BTC Close With Inferred Regime Segments")
    ax.set_ylabel("Close (log)")
    ax.grid(True, alpha=0.25)
    handles = [
        mpatches.Patch(color=color, label=label.replace("_", " "))
        for label, color in REGIME_COLORS.items()
        if label in set(plot_df["regime"])
    ]
    ax.legend(handles=handles, frameon=False, ncol=4, loc="upper left")

    ax = axes[1]
    conf = plot_df["confidence"]
    ax.plot(plot_df.index, conf, color="#1f77b4", linewidth=1.2)
    ax.fill_between(plot_df.index, 0.0, conf.fillna(0.0), color="#1f77b4", alpha=0.15)
    ax.set_ylim(0.0, 1.02)
    ax.set_title("Posterior Assignment Confidence")
    ax.set_ylabel("Max prob")
    ax.grid(True, alpha=0.25)

    ax = axes[2]
    ax.plot(plot_df.index, plot_df["drawdown"] * 100.0, color="#d62728", linewidth=1.2)
    ax2 = ax.twinx()
    ax2.plot(plot_df.index, plot_df["rv_30d"], color="#9467bd", linewidth=1.0, alpha=0.75)
    ax.axhline(0.0, color="#222222", linewidth=0.8)
    ax.set_title("Drawdown and 30d Realized Volatility")
    ax.set_ylabel("Drawdown (%)")
    ax2.set_ylabel("Realized vol")
    ax.grid(True, alpha=0.25)

    axes[-1].xaxis.set_major_locator(mdates.YearLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def parse_args() -> RunConfig:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--price-path", type=Path, default=DEFAULT_PRICE_PATH)
    parser.add_argument("--funding-path", type=Path, default=DEFAULT_FUNDING_PATH)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument("--output-chart", type=Path, default=DEFAULT_CHART_PATH)
    parser.add_argument("--min-train", type=int, default=120)
    parser.add_argument("--train-window", type=int, default=730)
    parser.add_argument("--refit-every", type=int, default=30)
    parser.add_argument("--max-regimes", type=int, default=8)
    parser.add_argument("--min-segment-days", type=int, default=14)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()
    return RunConfig(
        price_path=args.price_path,
        funding_path=args.funding_path,
        output_csv=args.output_csv,
        output_json=args.output_json,
        output_chart=args.output_chart,
        min_train=args.min_train,
        train_window=args.train_window,
        refit_every=args.refit_every,
        max_regimes=args.max_regimes,
        min_segment_days=args.min_segment_days,
        random_state=args.random_state,
    )


def main() -> None:
    config = parse_args()
    prices = load_prices(config.price_path)
    funding = load_daily_funding(config.funding_path, prices.index)
    features = build_features(prices, funding)
    results, summary = infer_regimes(features, config)

    config.output_csv.parent.mkdir(parents=True, exist_ok=True)
    out = results.reset_index().rename(columns={"index": "date"})
    out.to_csv(config.output_csv, index=False)

    config.output_json.parent.mkdir(parents=True, exist_ok=True)
    config.output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    plot_regimes(results, config.output_chart)

    counts = results["regime"].value_counts().to_dict()
    print(f"wrote {config.output_csv}")
    print(f"wrote {config.output_json}")
    print(f"wrote {config.output_chart}")
    print(f"window {summary['window']['start']} -> {summary['window']['end']}")
    print(f"regime_counts {counts}")


if __name__ == "__main__":
    main()
