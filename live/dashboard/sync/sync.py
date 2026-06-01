#!/usr/bin/env python3
"""
algo-traders live dashboard — VPS sync sidecar.

Reads freqtrade's tradesv3.sqlite (read-only) and upserts trade rows + an
equity snapshot to Supabase. Designed to be invoked by cron/systemd every
~30s. Idempotent: upserts on trade_id, append-only for equity_snapshots.

Env vars (set in /etc/algo-traders-sync.env or systemd EnvironmentFile):
  SUPABASE_URL        e.g. https://wbtyqhccgdjnmsstcovm.supabase.co
  SUPABASE_SERVICE_KEY  service_role key (NOT the publishable one)
  FREQTRADE_DB_PATH   absolute path to tradesv3.sqlite on the VPS
  STARTING_BALANCE    optional, for total_profit_pct (default 1000)
  SYNC_VERSION        optional tag, e.g. git short sha
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
DB_PATH = Path(os.environ["FREQTRADE_DB_PATH"])
STARTING_BALANCE = float(os.environ.get("STARTING_BALANCE", "1000"))
SYNC_VERSION = os.environ.get("SYNC_VERSION", "unknown")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def _post(path: str, payload, prefer: str = "resolution=merge-duplicates") -> None:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in HEADERS.items():
        req.add_header(k, v)
    req.add_header("Prefer", prefer)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {path} -> {e.code}: {body}") from e


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        # freqtrade stores naive UTC strings like '2026-05-22 10:11:12.345678'
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            dt = datetime.strptime(value.split(".")[0], "%Y-%m-%d %H:%M:%S")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def read_trades(db_path: Path) -> list[dict]:
    if not db_path.exists():
        raise FileNotFoundError(f"freqtrade db not found at {db_path}")
    # mode=ro means we will not interfere with freqtrade's writer.
    uri = f"file:{db_path}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=5)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT id, pair, is_open, open_date, close_date,
                   open_rate, close_rate, amount, stake_amount,
                   close_profit, close_profit_abs, exit_reason, strategy
              FROM trades
             ORDER BY id ASC
            """
        )
        return [dict(r) for r in cur.fetchall()]


def build_equity_snapshot(trades: list[dict]) -> dict:
    closed = [t for t in trades if not t["is_open"]]
    open_n = len(trades) - len(closed)
    total_profit = sum((t["close_profit_abs"] or 0.0) for t in closed)
    total_profit_pct = (total_profit / STARTING_BALANCE) * 100 if STARTING_BALANCE else 0.0

    by_pair: dict[str, float] = {}
    for t in closed:
        by_pair[t["pair"]] = by_pair.get(t["pair"], 0.0) + (t["close_profit_abs"] or 0.0)
    best_pair = max(by_pair, key=by_pair.get) if by_pair else None
    worst_pair = min(by_pair, key=by_pair.get) if by_pair else None

    return {
        "balance": STARTING_BALANCE + total_profit,
        "open_trades": open_n,
        "closed_trades": len(closed),
        "total_profit": total_profit,
        "total_profit_pct": total_profit_pct,
        "best_pair": best_pair,
        "worst_pair": worst_pair,
    }


def to_supabase_row(t: dict) -> dict:
    return {
        "trade_id": t["id"],
        "pair": t["pair"],
        "is_open": bool(t["is_open"]),
        "open_date": _iso(t["open_date"]),
        "close_date": _iso(t["close_date"]),
        "open_rate": t["open_rate"],
        "close_rate": t["close_rate"],
        "amount": t["amount"],
        "stake_amount": t["stake_amount"],
        "close_profit": t["close_profit"],
        "close_profit_abs": t["close_profit_abs"],
        "exit_reason": t["exit_reason"],
        "strategy": t["strategy"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def main() -> int:
    trades = read_trades(DB_PATH)

    if trades:
        rows = [to_supabase_row(t) for t in trades]
        for batch in chunked(rows, 500):
            _post("at_trades?on_conflict=trade_id", batch)

    snapshot = build_equity_snapshot(trades)
    _post("at_equity_snapshots", snapshot, prefer="return=minimal")

    # Heartbeat — single row, upsert on id=1.
    _post(
        "at_sync_state?on_conflict=id",
        [{
            "id": 1,
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
            "sync_version": SYNC_VERSION,
            "notes": f"trades={len(trades)} open={snapshot['open_trades']}",
        }],
    )

    print(
        f"[ok] trades={len(trades)} open={snapshot['open_trades']} "
        f"pnl={snapshot['total_profit']:.2f} ({snapshot['total_profit_pct']:.2f}%)"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[err] {exc}", file=sys.stderr)
        sys.exit(1)
