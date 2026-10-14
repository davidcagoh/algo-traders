#!/usr/bin/env python3
"""Build the workspace's shared, refreshable market-research dataset.

Raw source responses are retained under ``data/market/raw``. Normalized UTC
Parquet tables live under ``data/market/normalized``. A smaller compatibility
view for Freqtrade lives under ``data/market/freqtrade``.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote
from xml.etree import ElementTree

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = Path(__file__).with_name("catalog.json")
DEFAULT_DATA_DIR = ROOT / "data" / "market"
LEGACY_HYPERLIQUID_FUNDING = (
    ROOT / "freqtrade-experiment" / "hmm-slope-experiment" / "research" / "data"
    / "hyperliquid" / "funding"
)
S3_LIST_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
BINANCE_DATA_URL = "https://data.binance.vision/"
HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
LOG = logging.getLogger("market-data")

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "trade_count", "taker_buy_volume", "taker_buy_quote_volume",
    "ignore",
]


def read_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text())


def utc_timestamp(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    microseconds = numeric.abs() > 100_000_000_000_000
    result = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns, UTC]")
    result.loc[~microseconds] = pd.to_datetime(numeric.loc[~microseconds], unit="ms", utc=True, errors="coerce")
    result.loc[microseconds] = pd.to_datetime(numeric.loc[microseconds], unit="us", utc=True, errors="coerce")
    return result


def request(session: requests.Session, method: str, url: str, **kwargs: Any) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(6):
        try:
            response = session.request(method, url, timeout=90, **kwargs)
            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
            response.raise_for_status()
            return response
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status is not None and status < 500 and status != 429:
                raise RuntimeError(f"request returned HTTP {status}: {url}") from exc
            last_error = exc
            if attempt == 5:
                break
            time.sleep(min(2**attempt, 20))
        except (requests.RequestException, TimeoutError) as exc:
            last_error = exc
            if attempt == 5:
                break
            time.sleep(min(2**attempt, 20))
    raise RuntimeError(f"request failed after retries: {url}") from last_error


def list_s3_keys(session: requests.Session, prefix: str) -> list[str]:
    token: str | None = None
    keys: list[str] = []
    while True:
        params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            params["continuation-token"] = token
        response = request(session, "GET", S3_LIST_URL, params=params)
        root = ElementTree.fromstring(response.content)
        namespace = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
        keys.extend(node.text for node in root.findall("s3:Contents/s3:Key", namespace) if node.text)
        truncated = root.findtext("s3:IsTruncated", default="false", namespaces=namespace) == "true"
        token = root.findtext("s3:NextContinuationToken", default=None, namespaces=namespace)
        if not truncated or not token:
            break
    return [key for key in keys if key.endswith(".zip")]


def download_key(session: requests.Session, key: str, raw_root: Path, refresh: bool) -> Path:
    path = raw_root / key
    if path.exists() and path.stat().st_size > 0 and not refresh:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    response = request(session, "GET", BINANCE_DATA_URL + key)
    path.write_bytes(response.content)
    return path


def download_binance_archives(
    prefixes: dict[str, str], raw_root: Path, workers: int, refresh: bool
) -> dict[str, list[Path]]:
    session = requests.Session()
    keys_by_symbol: dict[str, list[str]] = {}
    for symbol, prefix in prefixes.items():
        keys_by_symbol[symbol] = list_s3_keys(session, prefix)
        LOG.info("%s: %d archive(s)", symbol, len(keys_by_symbol[symbol]))

    path_to_symbol: dict[Path, str] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for symbol, keys in keys_by_symbol.items():
            for key in keys:
                future = pool.submit(download_key, requests.Session(), key, raw_root, refresh)
                futures[future] = symbol
        for future in as_completed(futures):
            path = future.result()
            path_to_symbol[path] = futures[future]

    paths: dict[str, list[Path]] = {symbol: [] for symbol in prefixes}
    for path, symbol in path_to_symbol.items():
        paths[symbol].append(path)
    for symbol in paths:
        paths[symbol].sort()
    return paths


def read_zip_csv(path: Path, names: list[str] | None = None) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
        if len(members) != 1:
            raise ValueError(f"expected one CSV in {path}, got {members}")
        payload = archive.read(members[0])
    first_line = payload.splitlines()[0].decode("utf-8", errors="replace") if payload else ""
    has_header = first_line.startswith("open_time") or first_line.startswith("calc_time")
    return pd.read_csv(io.BytesIO(payload), names=names, header=0 if has_header else None)


def normalize_klines(paths: Iterable[Path], symbol: str, venue: str, market: str) -> pd.DataFrame:
    pieces = [read_zip_csv(path, KLINE_COLUMNS) for path in paths]
    if not pieces:
        return pd.DataFrame()
    frame = pd.concat(pieces, ignore_index=True)
    frame["timestamp"] = utc_timestamp(frame["open_time"])
    numeric = [
        "open", "high", "low", "close", "volume", "quote_volume", "trade_count",
        "taker_buy_volume", "taker_buy_quote_volume",
    ]
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.rename(
        columns={
            "volume": "volume_base",
            "taker_buy_volume": "taker_buy_volume_base",
            "taker_buy_quote_volume": "taker_buy_volume_quote",
        }
    )
    contract_symbol = symbol.removesuffix("USDT")
    contract_multiplier = 1000 if contract_symbol.startswith("1000") else 1
    frame["symbol"] = contract_symbol.removeprefix("1000") if contract_multiplier == 1000 else contract_symbol
    frame["pair"] = symbol
    frame["quote"] = "USDT"
    frame["venue"] = venue
    frame["market"] = market
    frame["contract_multiplier"] = contract_multiplier
    columns = [
        "timestamp", "symbol", "pair", "quote", "venue", "market", "open", "high",
        "low", "close", "volume_base", "quote_volume", "trade_count",
        "taker_buy_volume_base", "taker_buy_volume_quote", "contract_multiplier",
    ]
    return (
        frame[columns]
        .dropna(subset=["timestamp", "open", "high", "low", "close"])
        .drop_duplicates(["timestamp"], keep="last")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )


def daily_from_hourly(hourly: pd.DataFrame) -> pd.DataFrame:
    if hourly.empty:
        return hourly.copy()
    data = hourly.copy()
    if "contract_multiplier" not in data:
        data["contract_multiplier"] = 1
    data["timestamp"] = data["timestamp"].dt.floor("D")
    keys = ["timestamp", "symbol", "pair", "quote", "venue", "market", "contract_multiplier"]
    daily = data.groupby(keys, observed=True, sort=True).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume_base=("volume_base", "sum"),
        quote_volume=("quote_volume", "sum"),
        trade_count=("trade_count", "sum"),
        taker_buy_volume_base=("taker_buy_volume_base", "sum"),
        taker_buy_volume_quote=("taker_buy_volume_quote", "sum"),
    ).reset_index()
    return daily


def write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False, compression="zstd")


def write_freqtrade_ohlcv(frame: pd.DataFrame, root: Path, market: str, timeframe: str) -> None:
    if frame.empty:
        return
    folder = root / "binance" / ("futures" if market == "perpetual" else "")
    folder.mkdir(parents=True, exist_ok=True)
    for pair, group in frame.groupby("pair", observed=True):
        stem = pair.replace("USDT", "_USDT")
        if market == "perpetual":
            stem = f"{stem}_USDT-{timeframe}-futures"
        else:
            stem = f"{stem}-{timeframe}"
        out = group[["timestamp", "open", "high", "low", "close", "volume_base"]].rename(
            columns={"timestamp": "date", "volume_base": "volume"}
        )
        write_parquet(out, folder / f"{stem}.parquet")


def build_binance_prices(catalog: dict[str, Any], data_dir: Path, workers: int, refresh: bool) -> dict[str, Path]:
    outputs: dict[str, Path] = {}
    raw_root = data_dir / "raw" / "binance"
    for config_key, market, s3_market, venue in [
        ("crypto_spot", "spot", "spot", "binance"),
        ("crypto_perpetual", "perpetual", "futures/um", "binance_usdm"),
    ]:
        config = catalog[config_key]
        timeframe = config["timeframe"]
        prefixes = {
            symbol: f"data/{s3_market}/monthly/klines/{symbol}/{timeframe}/"
            for symbol in config["symbols"]
        }
        archives = download_binance_archives(prefixes, raw_root, workers, refresh)
        frames = []
        for symbol, paths in archives.items():
            frame = normalize_klines(paths, symbol, venue, market)
            if not frame.empty:
                frames.append(frame)
        hourly = pd.concat(frames, ignore_index=True).sort_values(["timestamp", "pair"])
        daily = daily_from_hourly(hourly)
        hourly_path = data_dir / "normalized" / "crypto" / f"{market}_1h.parquet"
        daily_path = data_dir / "normalized" / "crypto" / f"{market}_1d.parquet"
        write_parquet(hourly, hourly_path)
        write_parquet(daily, daily_path)
        write_freqtrade_ohlcv(hourly, data_dir / "freqtrade", market, "1h")
        write_freqtrade_ohlcv(daily, data_dir / "freqtrade", market, "1d")
        outputs[f"crypto_{market}_1h"] = hourly_path
        outputs[f"crypto_{market}_1d"] = daily_path
        LOG.info("wrote %s (%d rows) and %s (%d rows)", hourly_path, len(hourly), daily_path, len(daily))
    return outputs


def build_binance_funding(catalog: dict[str, Any], data_dir: Path, workers: int, refresh: bool) -> Path:
    symbols = catalog["crypto_perpetual"]["symbols"]
    prefixes = {
        symbol: f"data/futures/um/monthly/fundingRate/{symbol}/" for symbol in symbols
    }
    archives = download_binance_archives(prefixes, data_dir / "raw" / "binance", workers, refresh)
    frames = []
    for symbol, paths in archives.items():
        pieces = [read_zip_csv(path) for path in paths]
        if not pieces:
            continue
        frame = pd.concat(pieces, ignore_index=True)
        frame["timestamp"] = utc_timestamp(frame["calc_time"])
        frame["funding_rate"] = pd.to_numeric(frame["last_funding_rate"], errors="coerce")
        frame["funding_interval_hours"] = pd.to_numeric(frame["funding_interval_hours"], errors="coerce")
        contract_symbol = symbol.removesuffix("USDT")
        contract_multiplier = 1000 if contract_symbol.startswith("1000") else 1
        frame["symbol"] = contract_symbol.removeprefix("1000") if contract_multiplier == 1000 else contract_symbol
        frame["pair"] = symbol
        frame["venue"] = "binance_usdm"
        frame["contract_multiplier"] = contract_multiplier
        frames.append(frame[["timestamp", "symbol", "pair", "venue", "contract_multiplier", "funding_interval_hours", "funding_rate"]])
    result = (
        pd.concat(frames, ignore_index=True)
        .dropna(subset=["timestamp", "funding_rate"])
        .drop_duplicates(["venue", "pair", "timestamp"], keep="last")
        .sort_values(["timestamp", "pair"])
    )
    path = data_dir / "normalized" / "derivatives" / "funding_binance.parquet"
    write_parquet(result, path)
    return path


def hyperliquid_post(session: requests.Session, payload: dict[str, Any]) -> list[dict[str, Any]]:
    response = request(session, "POST", HYPERLIQUID_INFO_URL, json=payload)
    data = response.json()
    if not isinstance(data, list):
        raise ValueError(f"unexpected Hyperliquid response: {data!r}")
    return data


def fetch_hyperliquid_funding(coin: str, raw_path: Path, refresh: bool) -> pd.DataFrame:
    rows = json.loads(raw_path.read_text()) if raw_path.exists() and not refresh else []
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    cursor = int(rows[-1]["time"]) + 1 if rows else 1_640_000_000_000
    end = int(datetime.now(UTC).timestamp() * 1000)
    while cursor < end - 3_600_000:
        try:
            page = hyperliquid_post(
                session,
                {"type": "fundingHistory", "coin": coin, "startTime": cursor, "endTime": end},
            )
        except RuntimeError as exc:
            LOG.warning("Hyperliquid %s paused after %d cached rows: %s", coin, len(rows), exc)
            break
        if not page:
            break
        rows.extend(page)
        raw_path.write_text(json.dumps(rows))
        next_cursor = int(page[-1]["time"]) + 1
        if next_cursor <= cursor or len(page) < 500:
            break
        cursor = next_cursor
        time.sleep(0.5)
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    frame["timestamp"] = utc_timestamp(frame["time"])
    frame["funding_rate"] = pd.to_numeric(frame["fundingRate"], errors="coerce")
    frame["premium"] = pd.to_numeric(frame.get("premium"), errors="coerce")
    frame["symbol"] = coin
    frame["venue"] = "hyperliquid"
    return frame[["timestamp", "symbol", "venue", "funding_rate", "premium"]]


def build_hyperliquid_funding(
    catalog: dict[str, Any], data_dir: Path, refresh: bool, local_only: bool
) -> Path:
    frames: list[pd.DataFrame] = []
    raw_dir = data_dir / "raw" / "hyperliquid" / "funding"
    if not local_only:
        for coin in catalog["hyperliquid_funding"]:
            frame = fetch_hyperliquid_funding(coin, raw_dir / f"{coin}.json", refresh)
            if not frame.empty:
                frames.append(frame)
                LOG.info("Hyperliquid %s funding: %d rows", coin, len(frame))
    if LEGACY_HYPERLIQUID_FUNDING.exists():
        for source_path in sorted(LEGACY_HYPERLIQUID_FUNDING.glob("*-funding.parquet")):
            frame = pd.read_parquet(source_path).rename(columns={"time": "timestamp", "coin": "symbol"})
            frame["venue"] = "hyperliquid"
            frames.append(frame[["timestamp", "symbol", "venue", "funding_rate", "premium"]])
    if not frames:
        raise RuntimeError("no Hyperliquid funding data was available")
    result = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(["venue", "symbol", "timestamp"], keep="last")
        .sort_values(["timestamp", "symbol"])
    )
    path = data_dir / "normalized" / "derivatives" / "funding_hyperliquid.parquet"
    write_parquet(result, path)
    return path


def build_basis(data_dir: Path) -> Path:
    spot = pd.read_parquet(data_dir / "normalized" / "crypto" / "spot_1h.parquet", columns=["timestamp", "symbol", "close"])
    perp = pd.read_parquet(
        data_dir / "normalized" / "crypto" / "perpetual_1h.parquet",
        columns=["timestamp", "symbol", "close", "contract_multiplier"],
    )
    joined = spot.merge(perp, on=["timestamp", "symbol"], suffixes=("_spot", "_perpetual"))
    joined["basis"] = joined["close_perpetual"] / (joined["close_spot"] * joined["contract_multiplier"]) - 1.0
    path = data_dir / "normalized" / "derivatives" / "spot_perpetual_basis_1h.parquet"
    write_parquet(joined.sort_values(["timestamp", "symbol"]), path)
    return path


def build_fred(catalog: dict[str, Any], data_dir: Path, refresh: bool) -> Path:
    session = requests.Session()
    frames = []
    raw_dir = data_dir / "raw" / "fred"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for series, description in catalog["fred"].items():
        raw_path = raw_dir / f"{series}.csv"
        try:
            if refresh or not raw_path.exists():
                response = request(session, "GET", "https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": series})
                raw_path.write_bytes(response.content)
        except RuntimeError as exc:
            LOG.warning("FRED series unavailable for %s: %s", series, exc)
            continue
        frame = pd.read_csv(raw_path)
        value_column = next(column for column in frame.columns if column != "observation_date")
        frame = frame.rename(columns={"observation_date": "timestamp", value_column: "value"})
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        frame["series"] = series
        frame["description"] = description
        frames.append(frame.dropna(subset=["value"])[["timestamp", "series", "description", "value"]])
    result = pd.concat(frames, ignore_index=True).sort_values(["timestamp", "series"])
    path = data_dir / "normalized" / "macro" / "fred.parquet"
    write_parquet(result, path)
    return path


def build_traditional_markets(catalog: dict[str, Any], data_dir: Path, refresh: bool) -> Path:
    session = requests.Session()
    raw_dir = data_dir / "raw" / "yahoo"
    raw_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    period2 = int(datetime.now(UTC).timestamp()) + 86_400
    for symbol, description in catalog["traditional_markets"].items():
        raw_path = raw_dir / f"{quote(symbol, safe='')}.json"
        if refresh or not raw_path.exists():
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}"
            response = request(
                session, "GET", url,
                params={"period1": "-2208988800", "period2": str(period2), "interval": "1d", "events": "history"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            raw_path.write_bytes(response.content)
        payload = json.loads(raw_path.read_text())["chart"]["result"][0]
        quote_data = payload["indicators"]["quote"][0]
        frame = pd.DataFrame(quote_data)
        frame["timestamp"] = pd.to_datetime(payload["timestamp"], unit="s", utc=True).floor("D")
        adjclose = payload.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose")
        frame["adjusted_close"] = adjclose if adjclose is not None else frame["close"]
        frame = frame.loc[frame["timestamp"] < pd.Timestamp.now(tz="UTC").floor("D")].copy()
        frame["symbol"] = symbol
        frame["description"] = description
        frames.append(frame.dropna(subset=["close"]))
    result = pd.concat(frames, ignore_index=True).sort_values(["timestamp", "symbol"])
    path = data_dir / "normalized" / "markets" / "traditional_daily.parquet"
    write_parquet(result, path)
    return path


def build_coinmetrics(catalog: dict[str, Any], data_dir: Path, refresh: bool) -> Path:
    session = requests.Session()
    config = catalog["coinmetrics"]
    raw_dir = data_dir / "raw" / "coinmetrics"
    raw_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for asset in config["assets"]:
        raw_path = raw_dir / f"{asset}.json"
        if refresh or not raw_path.exists():
            params = {
                "assets": asset,
                "metrics": ",".join(config["metrics"]),
                "frequency": "1d",
                "page_size": "10000",
                "paging_from": "start",
            }
            response = request(
                session, "GET", "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics",
                params=params,
            )
            raw_path.write_bytes(response.content)
        rows = json.loads(raw_path.read_text()).get("data", [])
        frame = pd.DataFrame(rows)
        if frame.empty:
            continue
        frame["timestamp"] = pd.to_datetime(frame.pop("time"), utc=True)
        for metric in config["metrics"]:
            if metric in frame:
                frame[metric] = pd.to_numeric(frame[metric], errors="coerce")
        frames.append(frame)
    result = pd.concat(frames, ignore_index=True).sort_values(["timestamp", "asset"])
    path = data_dir / "normalized" / "onchain" / "coinmetrics_daily.parquet"
    write_parquet(result, path)
    return path


def build_defillama(data_dir: Path, refresh: bool) -> Path:
    session = requests.Session()
    raw_dir = data_dir / "raw" / "defillama"
    raw_dir.mkdir(parents=True, exist_ok=True)
    endpoints = {
        "stablecoin_supply": "https://stablecoins.llama.fi/stablecoincharts/all",
        "defi_tvl": "https://api.llama.fi/v2/historicalChainTvl",
        "dex_volume": "https://api.llama.fi/overview/dexs?excludeTotalDataChartBreakdown=true&excludeTotalDataChart=false",
    }
    series: list[pd.DataFrame] = []
    for name, url in endpoints.items():
        raw_path = raw_dir / f"{name}.json"
        if refresh or not raw_path.exists():
            response = request(session, "GET", url)
            raw_path.write_bytes(response.content)
        payload = json.loads(raw_path.read_text())
        if name == "stablecoin_supply":
            frame = pd.DataFrame(
                {"timestamp": [row["date"] for row in payload],
                 "value": [row.get("totalCirculatingUSD", {}).get("peggedUSD") for row in payload]}
            )
        elif name == "defi_tvl":
            frame = pd.DataFrame(payload).rename(columns={"date": "timestamp", "tvl": "value"})
        else:
            frame = pd.DataFrame(payload["totalDataChart"], columns=["timestamp", "value"])
        frame["timestamp"] = pd.to_datetime(
            pd.to_numeric(frame["timestamp"], errors="coerce"), unit="s", utc=True
        )
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        frame["series"] = name
        series.append(frame.dropna(subset=["value"])[["timestamp", "series", "value"]])
    result = pd.concat(series, ignore_index=True).sort_values(["timestamp", "series"])
    path = data_dir / "normalized" / "defi" / "defillama_daily.parquet"
    write_parquet(result, path)
    return path


def build_fear_greed(data_dir: Path, refresh: bool) -> Path:
    raw_path = data_dir / "raw" / "alternative_me" / "fear_greed.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if refresh or not raw_path.exists():
        response = request(requests.Session(), "GET", "https://api.alternative.me/fng/", params={"limit": "0", "format": "json"})
        raw_path.write_bytes(response.content)
    rows = json.loads(raw_path.read_text())["data"]
    frame = pd.DataFrame(rows)
    frame["timestamp"] = pd.to_datetime(pd.to_numeric(frame["timestamp"]), unit="s", utc=True)
    frame["fear_greed"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.rename(columns={"value_classification": "classification"})
    frame = frame[["timestamp", "fear_greed", "classification"]].sort_values("timestamp")
    path = data_dir / "normalized" / "sentiment" / "fear_greed_daily.parquet"
    write_parquet(frame, path)
    return path


def validate_table(name: str, path: Path) -> dict[str, Any]:
    frame = pd.read_parquet(path)
    timestamp = pd.to_datetime(frame["timestamp"], utc=True) if "timestamp" in frame else None
    symbol_col = "symbol" if "symbol" in frame else "series" if "series" in frame else "asset" if "asset" in frame else None
    entry: dict[str, Any] = {
        "path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": len(frame),
        "columns": list(frame.columns),
        "start": timestamp.min().isoformat() if timestamp is not None and not frame.empty else None,
        "end": timestamp.max().isoformat() if timestamp is not None and not frame.empty else None,
        "duplicate_rows": int(frame.duplicated().sum()),
    }
    if symbol_col:
        entry["members"] = sorted(frame[symbol_col].dropna().astype(str).unique().tolist())
        entry["member_count"] = len(entry["members"])
    issues = []
    if frame.empty:
        issues.append("empty table")
    if timestamp is not None and timestamp.isna().any():
        issues.append(f"{int(timestamp.isna().sum())} invalid timestamps")
    if {"open", "high", "low", "close"}.issubset(frame.columns):
        invalid = (
            (frame["high"] < frame[["open", "close", "low"]].max(axis=1))
            | (frame["low"] > frame[["open", "close", "high"]].min(axis=1))
            | (frame[["open", "high", "low", "close"]] <= 0).any(axis=1)
        )
        if invalid.any():
            issues.append(f"{int(invalid.sum())} invalid OHLC rows")
    entry["validation"] = "pass" if not issues else "warning"
    entry["issues"] = issues
    return entry


def write_manifest(data_dir: Path, outputs: dict[str, Path]) -> Path:
    manifest = {
        "schema_version": 1,
        "built_at": datetime.now(UTC).isoformat(),
        "catalog": str(CATALOG_PATH.relative_to(ROOT)),
        "tables": {name: validate_table(name, path) for name, path in sorted(outputs.items())},
    }
    manifest["validation"] = (
        "pass" if all(item["validation"] == "pass" for item in manifest["tables"].values()) else "warning"
    )
    path = data_dir / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--groups", nargs="+",
        choices=["crypto", "funding", "macro", "markets", "onchain", "defi", "sentiment", "all"],
        default=["all"],
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--refresh", action="store_true", help="redownload existing raw responses")
    parser.add_argument("--skip-hyperliquid", action="store_true")
    parser.add_argument(
        "--hyperliquid-local-only", action="store_true",
        help="use the existing experiment cache without calling the rate-limited API",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    catalog = read_catalog()
    groups = set(args.groups)
    if "all" in groups:
        groups = {"crypto", "funding", "macro", "markets", "onchain", "defi", "sentiment"}
    outputs: dict[str, Path] = {}
    if "crypto" in groups:
        outputs.update(build_binance_prices(catalog, args.data_dir, args.workers, args.refresh))
    if "funding" in groups:
        outputs["funding_binance"] = build_binance_funding(catalog, args.data_dir, args.workers, args.refresh)
        if not args.skip_hyperliquid:
            outputs["funding_hyperliquid"] = build_hyperliquid_funding(
                catalog, args.data_dir, args.refresh, args.hyperliquid_local_only
            )
        spot_path = args.data_dir / "normalized" / "crypto" / "spot_1h.parquet"
        perp_path = args.data_dir / "normalized" / "crypto" / "perpetual_1h.parquet"
        if spot_path.exists() and perp_path.exists():
            outputs["spot_perpetual_basis_1h"] = build_basis(args.data_dir)
    if "macro" in groups:
        outputs["fred"] = build_fred(catalog, args.data_dir, args.refresh)
    if "markets" in groups:
        outputs["traditional_daily"] = build_traditional_markets(catalog, args.data_dir, args.refresh)
    if "onchain" in groups:
        outputs["coinmetrics_daily"] = build_coinmetrics(catalog, args.data_dir, args.refresh)
    if "defi" in groups:
        outputs["defillama_daily"] = build_defillama(args.data_dir, args.refresh)
    if "sentiment" in groups:
        outputs["fear_greed_daily"] = build_fear_greed(args.data_dir, args.refresh)

    normalized = args.data_dir / "normalized"
    for path in normalized.rglob("*.parquet") if normalized.exists() else []:
        name = path.stem
        outputs.setdefault(name, path)
    manifest = write_manifest(args.data_dir, outputs)
    LOG.info("wrote manifest %s", manifest)


if __name__ == "__main__":
    main()
