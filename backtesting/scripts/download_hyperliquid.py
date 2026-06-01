"""
Download Hyperliquid perp OHLCV and funding-rate history from the public
`/info` endpoint.

Freqtrade's native `freqtrade download-data` is disabled for Hyperliquid
(`ohlcv_has_history=False` in the adapter). The Hyperliquid public API serves
at most ~5000 recent candles per (coin, interval) via `candleSnapshot` — that
is the hard public ceiling. This script fetches that window and drops the
result where freqtrade looks for it.

OHLCV output layout:
    user_data/data/hyperliquid/futures/<PAIR_FS>-<TIMEFRAME>-futures.feather
where PAIR_FS is e.g. `BTC_USDC_USDC` for the freqtrade pair `BTC/USDC:USDC`.

Funding-rate output layout (--funding flag):
    user_data/data/hyperliquid/funding/<COIN>-funding.parquet
Columns: time (datetime64[ms, UTC]), coin (str), funding_rate (float),
         premium (float).  Hyperliquid publishes 8-hourly rates; the full
         available history is fetched in paginated 500-record chunks.

Usage:
    # OHLCV only (existing behaviour)
    python scripts/download_hyperliquid.py \\
        --pairs BTC/USDC:USDC ETH/USDC:USDC \\
        --timeframes 1h 4h \\
        --data-dir user_data/data/hyperliquid

    # Funding rates only
    python scripts/download_hyperliquid.py \\
        --coins BTC ETH \\
        --funding \\
        --data-dir user_data/data/hyperliquid

    # Both at once
    python scripts/download_hyperliquid.py \\
        --pairs BTC/USDC:USDC \\
        --timeframes 1h 4h \\
        --coins BTC \\
        --funding \\
        --data-dir user_data/data/hyperliquid
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests


API_URL = "https://api.hyperliquid.xyz/info"
MAX_CANDLES = 5000       # Hyperliquid public cap; not a pagination limit
FUNDING_PAGE_SIZE = 500  # records per fundingHistory request
INTERVAL_TO_MS: dict[str, int] = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "8h": 28_800_000,
    "12h": 43_200_000,
    "1d": 86_400_000,
    "3d": 259_200_000,
    "1w": 604_800_000,
}

logger = logging.getLogger("download_hyperliquid")


@dataclass(frozen=True)
class DownloadRequest:
    pair: str            # freqtrade form: "BTC/USDC:USDC"
    timeframe: str       # e.g. "1h"

    @property
    def coin(self) -> str:
        base, _rest = self.pair.split("/", 1)
        return base

    @property
    def filename_stem(self) -> str:
        return self.pair.replace("/", "_").replace(":", "_")


def fetch_candles(coin: str, interval: str) -> list[dict]:
    """
    Pull up to MAX_CANDLES recent candles for the given perp.
    """
    if interval not in INTERVAL_TO_MS:
        raise ValueError(f"Unsupported interval: {interval}")
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - INTERVAL_TO_MS[interval] * MAX_CANDLES
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
        },
    }
    resp = requests.post(API_URL, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected response shape for {coin}/{interval}: {data!r}")
    return data


def candles_to_frame(candles: list[dict]) -> pd.DataFrame:
    """
    Convert Hyperliquid candleSnapshot rows into the freqtrade OHLCV schema:
    date (datetime64[ms], UTC-naive), open, high, low, close, volume (floats).
    """
    if not candles:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    df = pd.DataFrame(candles)
    df = df.rename(columns={"t": "date", "o": "open", "h": "high", "l": "low",
                            "c": "close", "v": "volume"})
    df["date"] = pd.to_datetime(df["date"], unit="ms", utc=True).astype("datetime64[ms, UTC]")
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    df = (df[["date", "open", "high", "low", "close", "volume"]]
          .sort_values("date")
          .drop_duplicates(subset=["date"])
          .reset_index(drop=True))
    return df


def write_feather(df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_feather(out_path, compression="lz4", compression_level=9)


def download_one(req: DownloadRequest, data_dir: Path) -> Path:
    logger.info("fetching %s %s", req.pair, req.timeframe)
    candles = fetch_candles(req.coin, req.timeframe)
    df = candles_to_frame(candles)
    if df.empty:
        raise RuntimeError(f"No candles returned for {req.pair} {req.timeframe}")
    out_path = data_dir / "futures" / f"{req.filename_stem}-{req.timeframe}-futures.feather"
    write_feather(df, out_path)
    logger.info("wrote %d rows → %s (range %s → %s)",
                len(df), out_path, df["date"].iloc[0], df["date"].iloc[-1])
    return out_path


def fetch_funding_history(coin: str, start_ms: int | None = None) -> list[dict]:
    """
    Fetch complete funding-rate history for *coin* via paginated calls to
    `/info fundingHistory`.  Hyperliquid returns records oldest-first within
    each page; we walk forward in time until we reach the present.

    If *start_ms* is None we start from the earliest available record
    (Hyperliquid epoch — effectively Jan 2022).
    """
    EPOCH_MS = 1_640_000_000_000  # Jan 2022 — before Hyperliquid launched
    cursor_ms = start_ms if start_ms is not None else EPOCH_MS
    now_ms = int(time.time() * 1000)
    all_records: list[dict] = []

    while cursor_ms < now_ms:
        # Note: fundingHistory takes flat fields, NOT a `req` wrapper (unlike
        # candleSnapshot). Hyperliquid changed/diverged this endpoint at some
        # point — wrapping in `req` returns HTTP 422.
        payload = {
            "type": "fundingHistory",
            "coin": coin,
            "startTime": cursor_ms,
            "endTime": now_ms,
        }
        resp = requests.post(API_URL, json=payload, timeout=30)
        resp.raise_for_status()
        page: list[dict] = resp.json()
        if not page:
            break
        all_records.extend(page)
        # Advance cursor past the last record to avoid duplicates.
        last_ts = int(page[-1]["time"])
        if last_ts <= cursor_ms:
            break  # no progress — end reached
        cursor_ms = last_ts + 1
        if len(page) < FUNDING_PAGE_SIZE:
            break  # partial page → last page
        time.sleep(0.2)  # be nice to the API; avoid 429 on long histories

    return all_records


def funding_to_frame(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=["time", "coin", "funding_rate", "premium"])
    df = pd.DataFrame(records)
    df["time"] = pd.to_datetime(df["time"].astype(int), unit="ms", utc=True).astype(
        "datetime64[ms, UTC]"
    )
    df["funding_rate"] = df["fundingRate"].astype(float)
    df["premium"] = df["premium"].astype(float)
    df = (
        df[["time", "coin", "funding_rate", "premium"]]
        .sort_values("time")
        .drop_duplicates(subset=["time"])
        .reset_index(drop=True)
    )
    return df


def download_funding(coin: str, data_dir: Path) -> Path:
    out_path = data_dir / "funding" / f"{coin}-funding.parquet"
    start_ms: int | None = None

    # Incremental update: if file exists, resume from last recorded timestamp.
    if out_path.exists():
        existing = pd.read_parquet(out_path)
        if not existing.empty:
            last_ts = existing["time"].max()
            start_ms = int(last_ts.timestamp() * 1000) + 1
            logger.info("resuming %s funding from %s", coin, last_ts)

    logger.info("fetching funding history for %s", coin)
    records = fetch_funding_history(coin, start_ms=start_ms)
    df_new = funding_to_frame(records)

    if out_path.exists() and start_ms is not None:
        existing = pd.read_parquet(out_path)
        df = (
            pd.concat([existing, df_new], ignore_index=True)
            .drop_duplicates(subset=["time"])
            .sort_values("time")
            .reset_index(drop=True)
        )
    else:
        df = df_new

    if df.empty:
        logger.warning("no funding records returned for %s", coin)
        return out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    logger.info(
        "wrote %d funding records → %s (range %s → %s)",
        len(df), out_path, df["time"].iloc[0], df["time"].iloc[-1],
    )
    return out_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--pairs", nargs="+", default=[],
                        help="Freqtrade pair strings, e.g. BTC/USDC:USDC")
    parser.add_argument("--timeframes", nargs="+", default=[],
                        help=f"Any of: {', '.join(INTERVAL_TO_MS)}")
    parser.add_argument("--coins", nargs="+", default=[],
                        help="Coin symbols for funding-rate download, e.g. BTC ETH")
    parser.add_argument("--funding", action="store_true",
                        help="Download funding-rate history for --coins")
    parser.add_argument("--data-dir", default="user_data/data/hyperliquid", type=Path,
                        help="Root data directory")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)

    if not args.pairs and not args.funding:
        logger.error("Nothing to do: specify --pairs for OHLCV and/or --funding --coins for funding rates.")
        return 1

    failures: list[tuple[str, str, str]] = []

    for pair in args.pairs:
        for tf in args.timeframes:
            req = DownloadRequest(pair=pair, timeframe=tf)
            try:
                download_one(req, args.data_dir)
            except Exception as exc:
                logger.exception("failed: %s %s", pair, tf)
                failures.append((pair, tf, str(exc)))

    if args.funding:
        for coin in args.coins:
            try:
                download_funding(coin, args.data_dir)
            except Exception as exc:
                logger.exception("funding failed: %s", coin)
                failures.append((coin, "funding", str(exc)))

    if failures:
        logger.error("%d failure(s): %s", len(failures), failures)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
