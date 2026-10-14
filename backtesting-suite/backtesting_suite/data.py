"""Canonical, point-in-time data access independent of any backtest engine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from backtesting_suite.config import DataConfig, FeatureConfig


class DataError(ValueError):
    """Raised when requested research data is unavailable or ambiguous."""


@dataclass(frozen=True)
class DataBundle:
    fields: dict[str, pd.DataFrame]
    funding: pd.DataFrame
    features: dict[str, pd.DataFrame] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def index(self) -> pd.DatetimeIndex:
        return self.fields["close"].index

    @property
    def symbols(self) -> list[str]:
        return list(self.fields["close"].columns)

    def field(self, name: str) -> pd.DataFrame:
        if name not in self.fields:
            raise DataError(f"price field {name!r} is not loaded")
        return self.fields[name]

    def feature(self, name: str) -> pd.DataFrame:
        if name not in self.features:
            raise DataError(f"feature group {name!r} is not loaded")
        return self.features[name]

    def slice(self, end: pd.Timestamp) -> DataBundle:
        return DataBundle(
            fields={name: frame.loc[:end].copy() for name, frame in self.fields.items()},
            funding=self.funding.loc[:end].copy(),
            features={name: frame.loc[:end].copy() for name, frame in self.features.items()},
            metadata=dict(self.metadata),
        )


def _resolve(path: str, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc(value: str, *, end: bool = False) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    timestamp = timestamp.tz_localize("UTC") if timestamp.tz is None else timestamp.tz_convert("UTC")
    if end and len(value) == 10:
        timestamp += pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
    return timestamp


def _load_feature(config: FeatureConfig, index: pd.DatetimeIndex, root: Path) -> pd.DataFrame:
    path = _resolve(config.path, root)
    if not path.exists():
        raise DataError(f"feature file does not exist: {path}")
    frame = pd.read_parquet(path)
    required = {config.timestamp_column, config.member_column, config.value_column}
    missing = required - set(frame.columns)
    if missing:
        raise DataError(f"feature {config.name!r} is missing columns {sorted(missing)}")
    frame = frame[[config.timestamp_column, config.member_column, config.value_column]].copy()
    frame[config.timestamp_column] = pd.to_datetime(frame[config.timestamp_column], utc=True)
    frame[config.timestamp_column] += pd.Timedelta(config.availability_lag)
    if config.members:
        frame = frame[frame[config.member_column].astype(str).isin(config.members)]
    wide = frame.pivot_table(
        index=config.timestamp_column,
        columns=config.member_column,
        values=config.value_column,
        aggfunc="last",
    ).sort_index()
    aligned = wide.reindex(wide.index.union(index)).sort_index()
    if config.fill_method == "ffill":
        aligned = aligned.ffill()
    return aligned.reindex(index)


def _funding_for_bars(
    manifest: dict[str, Any], market: str, index: pd.DatetimeIndex, symbols: list[str], root: Path
) -> pd.DataFrame:
    empty = pd.DataFrame(0.0, index=index, columns=symbols)
    if market != "perpetual" or "funding_binance" not in manifest["tables"]:
        return empty
    path = root / manifest["tables"]["funding_binance"]["path"]
    frame = pd.read_parquet(path, columns=["timestamp", "symbol", "funding_rate"])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame[frame["symbol"].isin(symbols)]
    if frame.empty:
        return empty

    if len(index) < 2:
        return empty
    bar_size = index.to_series().diff().median()
    origin = index[0]
    bucket = ((frame["timestamp"] - origin) // bar_size).astype(int)
    frame["bar_timestamp"] = origin + bucket * bar_size
    wide = frame.pivot_table(
        index="bar_timestamp", columns="symbol", values="funding_rate", aggfunc="sum"
    )
    return wide.reindex(index=index, columns=symbols).fillna(0.0)


def load_data_bundle(config: DataConfig, root: str | Path = ".") -> DataBundle:
    workspace = Path(root).resolve()
    manifest_path = _resolve(config.manifest, workspace)
    if not manifest_path.exists():
        raise DataError(f"dataset manifest does not exist: {manifest_path}")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    table_name = f"{config.market}_{config.timeframe}"
    table = manifest.get("tables", {}).get(table_name)
    if table is None:
        raise DataError(f"manifest has no table {table_name!r}")
    data_path = workspace / table["path"]
    if not data_path.exists():
        raise DataError(f"manifest table does not exist locally: {data_path}")
    table_hash = _sha256(data_path)
    if table.get("sha256") and table_hash != table["sha256"]:
        raise DataError(
            f"table checksum does not match manifest for {table_name!r}: {data_path}"
        )

    funding_hash = None
    funding_table = manifest.get("tables", {}).get("funding_binance")
    if config.market == "perpetual" and funding_table:
        funding_path = workspace / funding_table["path"]
        if not funding_path.exists():
            raise DataError(f"funding table does not exist locally: {funding_path}")
        funding_hash = _sha256(funding_path)
        if funding_table.get("sha256") and funding_hash != funding_table["sha256"]:
            raise DataError(
                f"funding checksum does not match manifest: {funding_path}"
            )

    columns = [
        "timestamp", "symbol", "open", "high", "low", "close", "volume_base",
        "quote_volume", "trade_count", "taker_buy_volume_base", "taker_buy_volume_quote",
    ]
    frame = pd.read_parquet(data_path, columns=columns)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    start = _utc(config.start)
    end = _utc(config.end, end=True)
    frame = frame[
        frame["symbol"].isin(config.universe)
        & frame["timestamp"].between(start, end, inclusive="both")
    ]
    present = set(frame["symbol"].unique())
    missing = set(config.universe) - present
    if missing:
        raise DataError(f"no rows in requested window for symbols {sorted(missing)}")
    if frame.duplicated(["timestamp", "symbol"]).any():
        raise DataError("price data contains duplicate timestamp/symbol rows")

    fields = {}
    for column in columns[2:]:
        fields[column] = (
            frame.pivot(index="timestamp", columns="symbol", values=column)
            .sort_index()
            .reindex(columns=list(config.universe))
        )
    index = fields["close"].index
    funding = _funding_for_bars(manifest, config.market, index, list(config.universe), workspace)
    features = {}
    feature_hashes = {}
    for feature in config.features:
        features[feature.name] = _load_feature(feature, index, workspace)
        feature_hashes[feature.name] = _sha256(_resolve(feature.path, workspace))
    dataset_fingerprint = hashlib.sha256(
        json.dumps(
            {
                "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                "table_sha256": table_hash,
                "funding_sha256": funding_hash,
                "feature_sha256": feature_hashes,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    metadata = {
        "manifest_path": str(manifest_path),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "dataset_built_at": manifest.get("built_at"),
        "table": table_name,
        "table_sha256": table_hash,
        "funding_sha256": funding_hash,
        "feature_sha256": feature_hashes,
        "dataset_sha256": dataset_fingerprint,
        "start": index.min().isoformat(),
        "end": index.max().isoformat(),
        "timeframe": config.timeframe,
        "market": config.market,
    }
    return DataBundle(fields=fields, funding=funding, features=features, metadata=metadata)
