"""
Download Binance USDT-margined perp funding-rate history from the public
`/fapi/v1/fundingRate` endpoint.

Output layout mirrors `download_hyperliquid.py` so FundingCarry / HmmCarry
can load it via the same `_load_funding(coin)` helper when
`CARRY_FUNDING_EXCHANGE=binance` is set:

    user_data/data/binance/funding/<COIN>-funding.parquet

Columns: time (datetime64[ms, UTC]), coin (str), funding_rate (float),
         premium (float, NaN — Binance has no premium field, mark_price
         retained instead for parity).

Binance publishes funding at 8h cadence (occasionally more frequent during
volatile periods). The endpoint returns oldest-first within each page;
walk forward via startTime until we reach the present.

Usage:
    python scripts/download_binance_funding.py \\
        --coins BTC ETH SOL DOGE AVAX ARB \\
        --start 2022-11-01 --end 2025-02-01 \\
        --data-dir user_data/data/binance
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd
import requests


API_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
PAGE_LIMIT = 1000  # Binance hard cap per request

logger = logging.getLogger("download_binance_funding")


def fetch_funding_history(
    coin: str, start_ms: int, end_ms: int
) -> list[dict]:
    """Paginate /fapi/v1/fundingRate forward by startTime until end_ms."""
    symbol = f"{coin}USDT"
    cursor_ms = start_ms
    all_records: list[dict] = []

    while cursor_ms < end_ms:
        params = {
            "symbol": symbol,
            "startTime": cursor_ms,
            "endTime": end_ms,
            "limit": PAGE_LIMIT,
        }
        resp = requests.get(API_URL, params=params, timeout=30)
        resp.raise_for_status()
        page: list[dict] = resp.json()
        if not page:
            break
        all_records.extend(page)
        last_ts = int(page[-1]["fundingTime"])
        if last_ts <= cursor_ms:
            break  # no progress — end reached
        cursor_ms = last_ts + 1
        if len(page) < PAGE_LIMIT:
            break  # partial page → done
        time.sleep(0.25)  # be nice to the API

    return all_records


def funding_to_frame(coin: str, records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=["time", "coin", "funding_rate", "premium"])
    df = pd.DataFrame(records)
    df["time"] = pd.to_datetime(
        df["fundingTime"].astype(int), unit="ms", utc=True
    ).astype("datetime64[ms, UTC]")
    df["coin"] = coin
    # Binance occasionally returns empty strings for markPrice (and rarely
    # fundingRate) on older records; pd.to_numeric coerces those to NaN
    # instead of raising. astype(float) was too strict.
    df["funding_rate"] = pd.to_numeric(df["fundingRate"], errors="coerce")
    df["premium"] = (
        pd.to_numeric(df["markPrice"], errors="coerce")
        if "markPrice" in df.columns
        else float("nan")
    )
    df = (
        df[["time", "coin", "funding_rate", "premium"]]
        .sort_values("time")
        .drop_duplicates(subset=["time"])
        .reset_index(drop=True)
    )
    return df


def download_funding(
    coin: str, data_dir: Path, start_ms: int, end_ms: int,
    force: bool = False,
) -> Path:
    out_path = data_dir / "funding" / f"{coin}-funding.parquet"

    if force and out_path.exists():
        logger.info("--force: removing existing %s", out_path)
        out_path.unlink()

    # Incremental update: if file exists, resume from last recorded timestamp.
    # Note this only moves start forward, never backward — pass --force to
    # backfill an earlier window than what's already on disk.
    if out_path.exists():
        existing = pd.read_parquet(out_path)
        if not existing.empty:
            last_ts = existing["time"].max()
            resume_ms = int(last_ts.timestamp() * 1000) + 1
            if resume_ms > start_ms:
                first_ts = existing["time"].min()
                if int(first_ts.timestamp() * 1000) > start_ms:
                    logger.warning(
                        "%s existing file starts %s — requested start %s would need backfill. "
                        "Pass --force to rewrite from scratch.",
                        coin, first_ts,
                        pd.Timestamp(start_ms, unit="ms", tz="UTC"),
                    )
                start_ms = resume_ms
                logger.info("resuming %s funding from %s", coin, last_ts)

    if start_ms >= end_ms:
        logger.info("%s funding already up to date", coin)
        return out_path

    logger.info("fetching %s funding %s → %s", coin,
                pd.Timestamp(start_ms, unit="ms", tz="UTC"),
                pd.Timestamp(end_ms, unit="ms", tz="UTC"))
    records = fetch_funding_history(coin, start_ms, end_ms)
    df_new = funding_to_frame(coin, records)

    if out_path.exists():
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
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--coins", nargs="+", required=True,
        help="Base coins, e.g. BTC ETH SOL. USDT is appended for the symbol.",
    )
    p.add_argument(
        "--start", required=True,
        help="UTC start date (YYYY-MM-DD).",
    )
    p.add_argument(
        "--end", required=True,
        help="UTC end date (YYYY-MM-DD, exclusive).",
    )
    p.add_argument(
        "--data-dir", type=Path, default=Path("user_data/data/binance"),
        help="Output root; funding files go in <data-dir>/funding/.",
    )
    p.add_argument(
        "--force", action="store_true",
        help="Delete existing parquet before fetching; use to backfill an "
             "earlier window than the file currently covers.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    args = parse_args(argv)
    start_ms = int(pd.Timestamp(args.start, tz="UTC").timestamp() * 1000)
    end_ms = int(pd.Timestamp(args.end, tz="UTC").timestamp() * 1000)

    for coin in args.coins:
        try:
            download_funding(coin, args.data_dir, start_ms, end_ms, force=args.force)
        except requests.HTTPError as e:
            logger.error("HTTP error for %s: %s", coin, e)
        except Exception as e:
            logger.exception("failed for %s: %s", coin, e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
