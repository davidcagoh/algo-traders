"""Read-only ClickHouse catalog and reproducible local data snapshots."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from urllib.request import HTTPRedirectHandler
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import pyarrow.parquet as parquet


class ClickHouseError(ValueError):
    """Raised for an unsafe, unsupported, or failed ClickHouse data operation."""


class _RejectRedirects(HTTPRedirectHandler):
    """Prevent forwarding ClickHouse Basic Auth credentials through redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TIMEFRAMES: dict[str, tuple[str, int]] = {
    "1m": ("MINUTE", 1),
    "5m": ("MINUTE", 5),
    "15m": ("MINUTE", 15),
    "30m": ("MINUTE", 30),
    "1h": ("HOUR", 1),
    "4h": ("HOUR", 4),
    "1d": ("DAY", 1),
}
_SOURCE_INTERVALS = {"candles_1m": 1, "candles_5m": 5}
_MAX_ROWS_LIMIT = 10_000_000
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024 * 1024
_MAX_METADATA_BYTES = 16 * 1024 * 1024
_BAR_NORMALIZATION_VERSION = 2
_OPTIONAL_BAR_COLUMNS = (
    "quote_volume",
    "trade_count",
    "taker_buy_volume_base",
    "taker_buy_volume_quote",
)


def parse_dataset_ref(value: str) -> tuple[str, str]:
    """Parse and validate a database.table reference."""
    pieces = value.split(".")
    if len(pieces) != 2 or not all(_IDENTIFIER.fullmatch(piece) for piece in pieces):
        raise ClickHouseError("dataset must be a database.table identifier")
    return pieces[0], pieces[1]


def _identifier(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ClickHouseError("invalid ClickHouse identifier")
    return f"`{value}`"


def _read_dotenv_value(path: Path, key: str) -> str | None:
    try:
        lines = path.read_text().splitlines()
    except FileNotFoundError:
        return None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name.strip() != key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            return value[1:-1]
        return value
    return None


class ClickHouseClient:
    """Small stdlib HTTP client that accepts SELECT queries only."""

    def __init__(
        self,
        endpoint: str,
        username: str,
        password: str,
        *,
        timeout: float = 60.0,
    ) -> None:
        parsed = urllib.parse.urlsplit(endpoint)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ClickHouseError(
                "ClickHouse endpoint must be an HTTPS URL without credentials, query, or fragment"
            )
        self.endpoint = endpoint.rstrip("/")
        self.username = username
        self._password = password
        self.timeout = timeout

    @classmethod
    def from_env(cls, root: str | Path = ".") -> ClickHouseClient:
        workspace = Path(root)
        password = os.environ.get("CLICKHOUSE_PASSWORD") or _read_dotenv_value(
            workspace / ".env", "CLICKHOUSE_PASSWORD"
        )
        if not password:
            raise ClickHouseError("CLICKHOUSE_PASSWORD is missing from the environment and .env")
        endpoint = os.environ.get("CLICKHOUSE_HOST", "https://clickhouse.gerardwu.com")
        username = os.environ.get("CLICKHOUSE_USER", "gerardwu")
        return cls(endpoint, username, password)

    @staticmethod
    def _validate_select(query: str) -> str:
        statement = query.strip()
        if not statement.casefold().startswith(("select ", "select\n", "select\t")) or ";" in statement:
            raise ClickHouseError("only a single read-only SELECT query is permitted")
        return statement

    def _request(
        self,
        query: str,
        *,
        parameters: Mapping[str, str] | None = None,
        destination: Path | None = None,
    ) -> bytes | None:
        statement = self._validate_select(query)
        request_parameters = {
            f"param_{key}": value for key, value in (parameters or {}).items()
        }
        request_parameters.update(
            {
                "max_execution_time": "120",
                "max_bytes_to_read": str(_MAX_RESPONSE_BYTES),
                "max_result_bytes": str(_MAX_RESPONSE_BYTES),
                "read_overflow_mode": "throw",
            }
        )
        url = f"{self.endpoint}/?{urllib.parse.urlencode(request_parameters)}"
        token = base64.b64encode(f"{self.username}:{self._password}".encode()).decode("ascii")
        request = urllib.request.Request(
            url,
            data=statement.encode("utf-8"),
            headers={
                "Authorization": f"Basic {token}",
                "Content-Type": "text/plain; charset=utf-8",
                "User-Agent": "curl/8.0",
            },
            method="POST",
        )
        temporary_path: Path | None = None
        try:
            opener = urllib.request.build_opener(_RejectRedirects())
            with opener.open(request, timeout=self.timeout) as response:
                if destination is None:
                    payload = response.read(_MAX_METADATA_BYTES + 1)
                    if len(payload) > _MAX_METADATA_BYTES:
                        raise ClickHouseError("ClickHouse metadata response exceeds the 16 MiB limit")
                    return payload
                destination.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    mode="wb", prefix=".clickhouse-download-", suffix=".tmp",
                    dir=destination.parent, delete=False,
                ) as handle:
                    temporary_path = Path(handle.name)
                    total = 0
                    while chunk := response.read(1024 * 1024):
                        total += len(chunk)
                        if total > _MAX_RESPONSE_BYTES:
                            raise ClickHouseError("ClickHouse snapshot exceeds the 2 GiB download limit")
                        handle.write(chunk)
                temporary_path.replace(destination)
                temporary_path = None
                return None
        except urllib.error.HTTPError as exc:
            # ClickHouse returns useful query/settings diagnostics in the body.
            # Scrub credentials before exposing a short excerpt to the CLI.
            detail = exc.read(2048).decode("utf-8", errors="replace")
            for secret in (self._password, self.username, token):
                if secret:
                    detail = detail.replace(secret, "[redacted]")
            detail = " ".join(detail.split())[:500]
            suffix = f": {detail}" if detail else ""
            raise ClickHouseError(
                f"ClickHouse request failed with HTTP {exc.code}{suffix}"
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ClickHouseError(
                f"ClickHouse request failed ({type(exc).__name__})"
            ) from None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def rows(
        self, query: str, *, parameters: Mapping[str, str] | None = None
    ) -> list[dict[str, Any]]:
        statement = f"{query.rstrip()} FORMAT JSONEachRow"
        payload = self._request(statement, parameters=parameters)
        if not payload:
            return []
        try:
            return [json.loads(line) for line in payload.decode("utf-8").splitlines() if line]
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ClickHouseError("ClickHouse returned invalid JSON metadata") from None

    def parquet(
        self,
        query: str,
        destination: Path,
        *,
        parameters: Mapping[str, str] | None = None,
    ) -> None:
        self._request(
            f"{query.rstrip()} FORMAT Parquet",
            parameters=parameters,
            destination=destination,
        )


def _sql_array(values: list[str]) -> str:
    if any(any(ord(character) < 32 for character in value) for value in values):
        raise ClickHouseError("instrument values cannot contain control characters")
    return "[" + ",".join("'" + value.replace("'", "''") + "'" for value in values) + "]"


def _parse_bound(value: str, *, end: bool) -> str:
    try:
        if len(value) == 10:
            parsed = datetime.combine(date.fromisoformat(value), time.min, timezone.utc)
            if end:
                parsed += timedelta(days=1) - timedelta(microseconds=1)
        else:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            parsed = parsed.astimezone(timezone.utc)
    except ValueError:
        raise ClickHouseError(f"invalid {'end' if end else 'start'} timestamp") from None
    return parsed.strftime("%Y-%m-%d %H:%M:%S.%f")


def _validate_range(start: str, end: str) -> tuple[str, str]:
    start_value = _parse_bound(start, end=False)
    end_value = _parse_bound(end, end=True)
    if datetime.fromisoformat(start_value) > datetime.fromisoformat(end_value):
        raise ClickHouseError("start must be before or equal to end")
    return start_value, end_value


def _normalized_binance_symbol(expression: str) -> str:
    # Keep contract multipliers in the identity (for example, 1000SATS != SATS).
    return f"replaceRegexpOne({expression}, 'USDT$', '')"


def build_bar_query(
    database: str,
    table: str,
    *,
    timeframe: str,
    market: str,
    start: str,
    end: str,
    symbols: list[str],
    max_rows: int = 2_000_000,
) -> tuple[str, dict[str, str]]:
    """Build an aggregated query for the verified Binance/Hyperliquid candle tables."""
    database_sql, table_sql = _identifier(database), _identifier(table)
    if database not in {"binance", "hyperliquid"} or table not in _SOURCE_INTERVALS:
        raise ClickHouseError("dataset is not a supported candle table")
    if database == "binance" and market != "spot":
        raise ClickHouseError("ClickHouse Binance candles are only verified for spot use")
    if database == "hyperliquid" and market != "perpetual":
        raise ClickHouseError("ClickHouse Hyperliquid candles are perpetual-market data")
    if timeframe not in _TIMEFRAMES:
        raise ClickHouseError(f"unsupported timeframe {timeframe!r}")
    if max_rows < 1 or max_rows > _MAX_ROWS_LIMIT:
        raise ClickHouseError(f"max_rows must be between 1 and {_MAX_ROWS_LIMIT}")
    start_value, end_value = _validate_range(start, end)
    unit, quantity = _TIMEFRAMES[timeframe]
    target_minutes = quantity * {"MINUTE": 1, "HOUR": 60, "DAY": 1440}[unit]
    source_minutes = _SOURCE_INTERVALS[table]
    if target_minutes < source_minutes or target_minutes % source_minutes:
        raise ClickHouseError("timeframe must be an integer multiple of the source candle interval")

    source_symbol = "source.`symbol`"
    normalized_symbol = _normalized_binance_symbol(source_symbol) if database == "binance" else source_symbol
    if database == "binance":
        volume = "source.`volume_base`"
        trades = "source.`trades`"
        taker_volume = "sum(source.`taker_buy_volume_base`)"
    else:
        volume = "source.`volume`"
        trades = "source.`trades`"
        taker_volume = "CAST(NULL, 'Nullable(Float64)')"
    source_filter = ""
    parameters = {"start": start_value, "end": end_value}
    if symbols:
        source_filter = " AND source.`symbol` IN {symbols:Array(String)}"
        parameters["symbols"] = _sql_array(symbols)

    query = f"""SELECT
    toStartOfInterval(source.`open_time`, INTERVAL {quantity} {unit}) AS timestamp,
    {normalized_symbol} AS symbol,
    argMin(source.`open`, source.`open_time`) AS open,
    max(source.`high`) AS high,
    min(source.`low`) AS low,
    argMax(source.`close`, source.`open_time`) AS close,
    sum({volume}) AS volume_base,
    CAST(NULL, 'Nullable(Float64)') AS quote_volume,
    sum({trades}) AS trade_count,
    {taker_volume} AS taker_buy_volume_base,
    CAST(NULL, 'Nullable(Float64)') AS taker_buy_volume_quote
FROM {database_sql}.{table_sql} AS source
WHERE source.`open_time` >= parseDateTime64BestEffort({{start:String}})
  AND source.`open_time` <= parseDateTime64BestEffort({{end:String}}){source_filter}
GROUP BY timestamp, symbol
ORDER BY timestamp, symbol
LIMIT {max_rows + 1}"""
    return query, parameters


def build_raw_query(
    database: str,
    table: str,
    *,
    columns: list[str],
    time_column: str,
    time_type: str,
    start: str,
    end: str,
    instrument_column: str | None = None,
    instruments: list[str] | None = None,
    max_rows: int = 2_000_000,
) -> tuple[str, dict[str, str]]:
    """Build a bounded generic query; identifiers must come from inspected metadata."""
    database_sql, table_sql = _identifier(database), _identifier(table)
    selected = list(dict.fromkeys(columns))
    if time_column not in selected:
        selected.append(time_column)
    if instrument_column and instrument_column not in selected:
        selected.append(instrument_column)
    if not selected:
        raise ClickHouseError("select at least one column")
    selected_sql = ", ".join(_identifier(column) for column in selected)
    time_sql = _identifier(time_column)
    start_value, end_value = _validate_range(start, end)
    normalized_time_type = _base_type(time_type)
    if normalized_time_type.startswith("DateTime"):
        time_expression = time_sql
        lower = f"{time_expression} >= parseDateTime64BestEffort({{start:String}})"
        upper = f"{time_expression} <= parseDateTime64BestEffort({{end:String}})"
    elif normalized_time_type.startswith("Date"):
        lower = f"{time_sql} >= toDate(parseDateTime64BestEffort({{start:String}}))"
        upper = f"{time_sql} <= toDate(parseDateTime64BestEffort({{end:String}}))"
    elif normalized_time_type.startswith("String"):
        time_expression = f"parseDateTime64BestEffortOrNull({time_sql})"
        lower = f"{time_expression} >= parseDateTime64BestEffort({{start:String}})"
        upper = f"{time_expression} <= parseDateTime64BestEffort({{end:String}})"
    else:
        raise ClickHouseError("time column must have Date, DateTime, or String type")
    parameters = {"start": start_value, "end": end_value}
    filter_sql = ""
    if instruments:
        if not instrument_column:
            raise ClickHouseError("instrument filters require --instrument-column")
        filter_sql = f" AND {_identifier(instrument_column)} IN {{instruments:Array(String)}}"
        parameters["instruments"] = _sql_array(instruments)
    if max_rows < 1 or max_rows > _MAX_ROWS_LIMIT:
        raise ClickHouseError(f"max_rows must be between 1 and {_MAX_ROWS_LIMIT}")
    query = (
        f"SELECT {selected_sql} FROM {database_sql}.{table_sql} "
        f"WHERE {lower} AND {upper}{filter_sql} LIMIT {max_rows + 1}"
    )
    return query, parameters


def classify_dataset(database: str, table: str) -> str:
    """Return a conservative data-family label used to gate backtest inputs."""
    db, name = database.casefold(), table.casefold()
    if db in {"binance", "hyperliquid"} and name in _SOURCE_INTERVALS:
        return "bar"
    if db == "features" and "target" in name:
        return "targets"
    if db == "features":
        return "features"
    if db in {"ivydb"} or "option" in name or "opprcd" in name:
        return "options"
    if db == "prediction" or db == "polymarket" or "kalshi" in name:
        return "prediction"
    return "raw"


def normalize_bars(
    frame: pd.DataFrame, *, timeframe: str, market: str, venue: str
) -> pd.DataFrame:
    """Normalize candle rows to the backtesting suite's long-form bar schema."""
    if timeframe not in _TIMEFRAMES:
        raise ClickHouseError(f"unsupported timeframe {timeframe!r}")
    required = {"timestamp", "symbol", "open", "high", "low", "close", "volume_base"}
    if missing := required - set(frame.columns):
        raise ClickHouseError(f"candle rows are missing columns {sorted(missing)}")
    data = frame.copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
    data = data.dropna(subset=["timestamp", "symbol", "open", "high", "low", "close"])
    if venue.casefold() == "binance":
        data["symbol"] = (
            data["symbol"].astype(str).str.removesuffix("USDT")
        )
    for column in _OPTIONAL_BAR_COLUMNS:
        if column not in data:
            data[column] = pd.NA
    unit, quantity = _TIMEFRAMES[timeframe]
    frequency = {"MINUTE": "min", "HOUR": "h", "DAY": "D"}[unit]
    rule = f"{quantity}{frequency}"
    data["timestamp"] = data["timestamp"].dt.floor(rule)
    if data.duplicated(["timestamp", "symbol"]).any():
        data = data.sort_values("timestamp").groupby(
            ["timestamp", "symbol"], as_index=False, sort=True, observed=True
        ).agg(
            open=("open", "first"), high=("high", "max"), low=("low", "min"),
            close=("close", "last"), volume_base=("volume_base", "sum"),
            quote_volume=("quote_volume", lambda values: values.sum(min_count=1)),
            trade_count=("trade_count", lambda values: values.sum(min_count=1)),
            taker_buy_volume_base=("taker_buy_volume_base", lambda values: values.sum(min_count=1)),
            taker_buy_volume_quote=("taker_buy_volume_quote", lambda values: values.sum(min_count=1)),
        )
    data["market"] = market
    data["venue"] = venue
    data["contract_multiplier"] = 1
    columns = [
        "timestamp", "symbol", "open", "high", "low", "close", "volume_base",
        "quote_volume", "trade_count", "taker_buy_volume_base", "taker_buy_volume_quote",
    ]
    return data[columns].sort_values(["timestamp", "symbol"]).reset_index(drop=True)


def _symbol_list(values: list[str] | None, database: str) -> list[str]:
    if not values:
        return []
    if database == "binance":
        return [value if value.endswith("USDT") else f"{value}USDT" for value in values]
    return values


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot_identity(source: str, parameters: Mapping[str, Any], digest: str) -> str:
    encoded = json.dumps(
        {"source": source, "parameters": parameters, "sha256": digest},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()[:20]


def _snapshot_directory(output_dir: Path, source: str, identity: str) -> Path:
    database, table = parse_dataset_ref(source)
    return output_dir / database / table / identity


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def write_bar_snapshot(
    bars: pd.DataFrame,
    output_dir: str | Path,
    *,
    workspace: str | Path | None = None,
    source: str,
    market: str,
    timeframe: str,
    start: str,
    end: str,
    symbols: list[str],
    source_sha256: str | None = None,
) -> Path:
    """Write a canonical local backtest manifest and its content-addressed bar file."""
    if bars.empty:
        raise ClickHouseError("no bars returned for the requested snapshot")
    required = {"timestamp", "symbol", "open", "high", "low", "close", "volume_base"}
    if missing := required - set(bars.columns):
        raise ClickHouseError(f"normalized bars are missing columns {sorted(missing)}")
    if bars.duplicated(["timestamp", "symbol"]).any():
        raise ClickHouseError("bar snapshot contains duplicate timestamp/symbol rows")
    bars = bars.copy()
    for column in _OPTIONAL_BAR_COLUMNS:
        if column not in bars:
            bars[column] = pd.NA
    output_root = Path(output_dir).resolve()
    workspace_root = Path(workspace or Path.cwd()).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=".snapshot-", dir=output_root))
    try:
        data_path = temp_dir / "bars.parquet"
        bars.to_parquet(data_path, index=False, compression="zstd")
        data_sha256 = _sha256_file(data_path)
        table_name = f"{market}_{timeframe}"
        identity = _snapshot_identity(
            source,
            {"start": start, "end": end, "timeframe": timeframe, "market": market,
             "symbols": symbols, "source_sha256": source_sha256,
             "normalization_version": _BAR_NORMALIZATION_VERSION},
            data_sha256,
        )
        final_dir = _snapshot_directory(output_root, source, identity)
        final_file = final_dir / "bars.parquet"
        relative_file = final_file.resolve().relative_to(workspace_root)
        table_entry = {
            "path": str(relative_file),
            "rows": int(len(bars)),
            "start": pd.Timestamp(bars["timestamp"].min()).isoformat(),
            "end": pd.Timestamp(bars["timestamp"].max()).isoformat(),
            "sha256": data_sha256,
            "symbols": sorted(str(value) for value in bars["symbol"].unique()),
            "venue": source.split(".", 1)[0],
            "market": market,
            "timeframe": timeframe,
            "backtest_supported": True,
        }
        manifest = {
            "schema_version": 1,
            "normalization_version": _BAR_NORMALIZATION_VERSION,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "snapshot_id": identity,
            "source": {
                "provider": "clickhouse",
                "table": source,
                "selected_symbols": symbols,
                "requested_start": start,
                "requested_end": end,
                "source_sha256": source_sha256,
            },
            "tables": {table_name: table_entry},
        }
        _write_json(temp_dir / "manifest.json", manifest)
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        if final_dir.exists():
            shutil.rmtree(temp_dir)
        else:
            temp_dir.rename(final_dir)
        return final_dir / "manifest.json"
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise


def _temporal_columns(columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    temporal = [
        column for column in columns
        if _base_type(str(column.get("type", ""))).startswith(("Date", "DateTime"))
    ]
    priority = {
        "timestamp": 0, "feature_time": 1, "open_time": 2, "date": 3,
        "dlycaldt": 4, "end_period_ts": 5, "source_time": 6,
    }
    return sorted(temporal, key=lambda column: priority.get(str(column["name"]).casefold(), 20))


def _base_type(value: str) -> str:
    """Remove ClickHouse Nullable/LowCardinality wrappers for type checks."""
    result = value
    while result.startswith(("Nullable(", "LowCardinality(")) and result.endswith(")"):
        result = result[result.index("(") + 1 : -1]
    return result


def list_sources(client: ClickHouseClient) -> list[dict[str, Any]]:
    return client.rows(
        "SELECT database, name, engine, total_rows, total_bytes "
        "FROM system.tables WHERE database NOT IN "
        "('system', 'INFORMATION_SCHEMA', 'information_schema') "
        "AND is_temporary = 0 ORDER BY database, name"
    )


def inspect_dataset(
    client: ClickHouseClient, source: str
) -> dict[str, Any]:
    database, table = parse_dataset_ref(source)
    table_rows = client.rows(
        "SELECT engine, total_rows, total_bytes FROM system.tables "
        "WHERE database = {database:String} AND name = {table:String}",
        parameters={"database": database, "table": table},
    )
    if not table_rows:
        raise ClickHouseError(f"dataset {source!r} was not found")
    columns = client.rows(
        "SELECT name, type, position FROM system.columns "
        "WHERE database = {database:String} AND table = {table:String} ORDER BY position",
        parameters={"database": database, "table": table},
    )
    temporal = _temporal_columns(columns)
    coverage = None
    selected_time = temporal[0] if temporal else None
    if selected_time:
        base_time_type = _base_type(str(selected_time["type"]))
        bounds = "min_date" if base_time_type.startswith("Date") and not base_time_type.startswith("DateTime") else "min_time"
        upper_bounds = "max_date" if bounds == "min_date" else "max_time"
        coverage_rows = client.rows(
            f"SELECT min({bounds}) AS coverage_start, max({upper_bounds}) AS coverage_end "
            "FROM system.parts WHERE database = {database:String} "
            "AND table = {table:String} AND active",
            parameters={"database": database, "table": table},
        )
        if coverage_rows:
            candidate = coverage_rows[0]
            start_value = candidate.get("coverage_start")
            # system.parts exposes bounds from temporal partition keys without
            # scanning a potentially multi-billion-row table. Sentinel bounds
            # mean the temporal column is not represented in the partition key.
            if str(start_value) not in {"1970-01-01", "1970-01-01 00:00:00"}:
                coverage = candidate
    stats = table_rows[0]
    return {
        "database": database,
        "table": table,
        "engine": stats.get("engine"),
        "rows_estimate": stats.get("total_rows"),
        "bytes_estimate": stats.get("total_bytes"),
        "kind": classify_dataset(database, table),
        "bar_backtest_supported": classify_dataset(database, table) == "bar",
        "time_column": selected_time.get("name") if selected_time else None,
        "coverage": coverage,
        "coverage_source": "active part temporal bounds" if coverage else None,
        "columns": [{"name": row["name"], "type": row["type"]} for row in columns],
    }


def _write_raw_snapshot(
    parquet_path: Path,
    *,
    source: str,
    output_dir: Path,
    workspace: Path,
    query_details: Mapping[str, Any],
    kind: str,
) -> Path:
    digest = _sha256_file(parquet_path)
    identity = _snapshot_identity(source, query_details, digest)
    final_dir = _snapshot_directory(output_dir, source, identity)
    rows = int(parquet.ParquetFile(parquet_path).metadata.num_rows)
    manifest = {
        "schema_version": 1,
        "snapshot_id": identity,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "provider": "clickhouse",
        "source": source,
        "kind": kind,
        "bar_backtest_supported": False,
        "query": dict(query_details),
        "rows": rows,
        "sha256": digest,
        "data_file": str((final_dir / "data.parquet").resolve().relative_to(workspace)),
    }
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    if final_dir.exists():
        parquet_path.unlink(missing_ok=True)
        shutil.rmtree(parquet_path.parent)
    else:
        temp_dir = parquet_path.parent
        _write_json(temp_dir / "snapshot.json", manifest)
        temp_dir.rename(final_dir)
    return final_dir / "snapshot.json"


def snapshot_dataset(
    client: ClickHouseClient,
    source: str,
    *,
    start: str,
    end: str,
    output_dir: str | Path = "data/clickhouse",
    workspace: str | Path = ".",
    timeframe: str | None = None,
    market: str | None = None,
    symbols: list[str] | None = None,
    columns: list[str] | None = None,
    time_column: str | None = None,
    instrument_column: str | None = None,
    max_rows: int = 2_000_000,
) -> Path:
    """Export a bounded bar dataset or raw table slice to an immutable Parquet snapshot."""
    database, table = parse_dataset_ref(source)
    output_root = Path(output_dir).resolve()
    workspace_root = Path(workspace).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=".snapshot-", dir=output_root))
    parquet_path = temp_dir / "data.parquet"
    kind = classify_dataset(database, table)
    try:
        if kind == "bar":
            resolved_market = market or ("spot" if database == "binance" else "perpetual")
            resolved_timeframe = timeframe or "1h"
            source_symbols = _symbol_list(symbols, database)
            query, parameters = build_bar_query(
                database, table, timeframe=resolved_timeframe, market=resolved_market,
                start=start, end=end, symbols=source_symbols, max_rows=max_rows,
            )
            client.parquet(query, parquet_path, parameters=parameters)
            row_count = int(parquet.ParquetFile(parquet_path).metadata.num_rows)
            if row_count == 0:
                raise ClickHouseError("no bars returned for the requested snapshot")
            if row_count > max_rows:
                raise ClickHouseError(
                    f"snapshot exceeds the {max_rows:,}-row limit; narrow the date range or symbols"
                )
            schema_names = parquet.ParquetFile(parquet_path).schema.names
            required = {"timestamp", "symbol", "open", "high", "low", "close", "volume_base"}
            if missing := required - set(schema_names):
                raise ClickHouseError(f"ClickHouse candle query omitted {sorted(missing)}")
            keys = parquet.read_table(parquet_path, columns=["timestamp", "symbol"]).to_pandas()
            if keys.duplicated(["timestamp", "symbol"]).any():
                raise ClickHouseError("ClickHouse returned duplicate timestamp/symbol bars")
            digest = _sha256_file(parquet_path)
            identity = _snapshot_identity(
                source,
                {"start": start, "end": end, "timeframe": resolved_timeframe,
                 "market": resolved_market, "symbols": source_symbols,
                 "normalization_version": _BAR_NORMALIZATION_VERSION},
                digest,
            )
            final_dir = _snapshot_directory(output_root, source, identity)
            final_data = final_dir / "bars.parquet"
            relative_data = str(final_data.resolve().relative_to(workspace_root))
            table_name = f"{resolved_market}_{resolved_timeframe}"
            bar_manifest = {
                "schema_version": 1,
                "normalization_version": _BAR_NORMALIZATION_VERSION,
                "built_at": datetime.now(timezone.utc).isoformat(),
                "snapshot_id": identity,
                "source": {
                    "provider": "clickhouse", "table": source,
                    "selected_symbols": source_symbols, "requested_start": start,
                    "requested_end": end,
                },
                "tables": {
                    table_name: {
                        "path": relative_data,
                        "rows": row_count,
                        "start": str(keys["timestamp"].min()),
                        "end": str(keys["timestamp"].max()),
                        "sha256": digest,
                        "symbols": sorted(keys["symbol"].unique().tolist()),
                        "venue": database,
                        "market": resolved_market,
                        "timeframe": resolved_timeframe,
                        "backtest_supported": True,
                        "normalization": {
                            "timestamp": "open_time bucketed to requested timeframe (UTC)",
                            "ohlc": "first open, maximum high, minimum low, last close",
                            "volume": "sum of source base volume, trades, and available taker volume",
                            "symbol": "Binance USDT suffix removed; exchange multiplier prefixes preserved",
                            "unavailable_fields": [
                                "quote_volume", "taker_buy_volume_quote"
                            ],
                        },
                    }
                },
            }
            final_dir.parent.mkdir(parents=True, exist_ok=True)
            if final_dir.exists():
                shutil.rmtree(temp_dir)
            else:
                parquet_path.rename(temp_dir / "bars.parquet")
                _write_json(temp_dir / "manifest.json", bar_manifest)
                temp_dir.rename(final_dir)
            return final_dir / "manifest.json"

        description = inspect_dataset(client, source)
        column_rows = description["columns"]
        available = {str(column["name"]): str(column["type"]) for column in column_rows}
        resolved_time = time_column or description["time_column"]
        if not resolved_time or resolved_time not in available:
            raise ClickHouseError("table has no recognized time column; provide --time-column")
        selected_columns = columns or list(available)
        if columns is None and int(description.get("bytes_estimate") or 0) > 512 * 1024 * 1024:
            raise ClickHouseError(
                "table is large; choose specific --column values before snapshotting"
            )
        unknown = sorted(set(selected_columns) - set(available))
        if unknown:
            raise ClickHouseError(f"unknown columns: {unknown}")
        if instrument_column and instrument_column not in available:
            raise ClickHouseError("unknown instrument column")
        query, parameters = build_raw_query(
            database, table, columns=selected_columns, time_column=resolved_time,
            time_type=available[resolved_time], start=start, end=end,
            instrument_column=instrument_column, instruments=symbols, max_rows=max_rows,
        )
        client.parquet(query, parquet_path, parameters=parameters)
        row_count = int(parquet.ParquetFile(parquet_path).metadata.num_rows)
        if row_count == 0:
            raise ClickHouseError("no rows returned for the requested snapshot")
        if row_count > max_rows:
            raise ClickHouseError(
                f"snapshot exceeds the {max_rows:,}-row limit; narrow the date range or instruments"
            )
        details = {
            "start": start, "end": end, "time_column": resolved_time,
            "columns": selected_columns, "instrument_column": instrument_column,
            "instruments": symbols or [],
        }
        return _write_raw_snapshot(
            parquet_path, source=source, output_dir=output_root,
            workspace=workspace_root, query_details=details, kind=kind,
        )
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise
