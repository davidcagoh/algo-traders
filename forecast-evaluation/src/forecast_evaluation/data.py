"""Load and validate immutable bar snapshots for forecasting evaluation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ReturnSeries:
    symbol: str
    timestamps: pd.DatetimeIndex
    values: np.ndarray


@dataclass(frozen=True)
class Snapshot:
    manifest_path: Path
    snapshot_id: str
    data_path: Path
    data_sha256: str
    source_table: str
    symbols: tuple[str, ...]
    bars: pd.DataFrame


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_snapshot(
    manifest_path: str | Path,
    *,
    expected_snapshot_id: str,
    expected_sha256: str,
    workspace: str | Path = ".",
) -> Snapshot:
    """Load a ClickHouse bar snapshot and verify its pinned identity and bytes."""
    manifest_file = Path(manifest_path).resolve()
    try:
        manifest = json.loads(manifest_file.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read snapshot manifest: {manifest_file}") from exc

    if manifest.get("snapshot_id") != expected_snapshot_id:
        raise ValueError("snapshot ID does not match the frozen evaluation protocol")
    source = manifest.get("source", {})
    if source.get("provider") != "clickhouse":
        raise ValueError("evaluation requires a ClickHouse snapshot")
    source_table = source.get("table")
    if source_table != "binance.candles_1m":
        raise ValueError(f"unexpected snapshot source table: {source_table!r}")
    tables = manifest.get("tables", {})
    if len(tables) != 1:
        raise ValueError("expected exactly one normalized bar table in the manifest")
    table = next(iter(tables.values()))
    if table.get("timeframe") != "1h" or table.get("market") != "spot":
        raise ValueError("evaluation requires UTC hourly spot bars")
    if not table.get("backtest_supported"):
        raise ValueError("snapshot is not marked as normalized bar data")
    if table.get("sha256") != expected_sha256:
        raise ValueError("manifest data hash does not match the frozen evaluation protocol")

    declared_path = Path(table.get("path", ""))
    if declared_path.is_absolute():
        data_path = declared_path
    else:
        candidates = [Path(workspace).resolve() / declared_path, manifest_file.parent / declared_path.name]
        data_path = next((candidate for candidate in candidates if candidate.is_file()), candidates[0])
    if not data_path.is_file():
        raise ValueError(f"snapshot data file is missing: {data_path}")
    actual_sha256 = _sha256(data_path)
    if actual_sha256 != expected_sha256:
        raise ValueError("snapshot data hash does not match the frozen evaluation protocol")

    bars = pd.read_parquet(data_path)
    required = {"timestamp", "symbol", "close"}
    if missing := required - set(bars.columns):
        raise ValueError(f"snapshot is missing required columns: {sorted(missing)}")
    symbols = tuple(sorted(str(value) for value in bars["symbol"].unique()))
    expected_symbols = tuple(sorted(str(value) for value in table.get("symbols", [])))
    if symbols != expected_symbols:
        raise ValueError("manifest symbols do not match the snapshot rows")
    return Snapshot(
        manifest_path=manifest_file,
        snapshot_id=expected_snapshot_id,
        data_path=data_path,
        data_sha256=actual_sha256,
        source_table=source_table,
        symbols=symbols,
        bars=bars,
    )


def make_return_series(bars: pd.DataFrame, symbol: str) -> ReturnSeries:
    """Create a validated hourly close-to-close log-return series."""
    frame = bars.loc[bars["symbol"].astype(str) == symbol, ["timestamp", "close"]].copy()
    if frame.empty:
        raise ValueError(f"no bars for symbol {symbol!r}")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    if frame["timestamp"].isna().any() or frame["close"].isna().any():
        raise ValueError(f"{symbol}: timestamps and closes must be finite")
    frame = frame.sort_values("timestamp", kind="stable").reset_index(drop=True)
    timestamps = pd.DatetimeIndex(frame["timestamp"])
    if (
        (timestamps.minute != 0).any()
        or (timestamps.second != 0).any()
        or (timestamps.microsecond != 0).any()
        or (timestamps.nanosecond != 0).any()
    ):
        raise ValueError(f"{symbol}: timestamps must align to UTC hourly bar boundaries")
    if frame["timestamp"].duplicated().any():
        raise ValueError(f"{symbol}: duplicate hourly timestamps are not allowed")
    if (frame["close"] <= 0).any() or not np.isfinite(frame["close"].to_numpy(dtype=float)).all():
        raise ValueError(f"{symbol}: closes must be finite and positive")
    if len(timestamps) < 2 or not (timestamps[1:] - timestamps[:-1] == pd.Timedelta(hours=1)).all():
        raise ValueError(f"{symbol}: expected a complete UTC hourly grid without gaps")

    close = frame["close"].to_numpy(dtype=np.float64)
    returns = np.full(len(close), np.nan, dtype=np.float64)
    returns[1:] = np.diff(np.log(close))
    if not np.isfinite(returns[1:]).all():
        raise ValueError(f"{symbol}: log returns contain nonfinite values")
    return ReturnSeries(symbol=symbol, timestamps=timestamps, values=returns)
