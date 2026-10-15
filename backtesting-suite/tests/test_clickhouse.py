from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import backtesting_suite.clickhouse as clickhouse_module
from backtesting_suite.clickhouse import (
    build_raw_query,
    ClickHouseError,
    ClickHouseClient,
    build_bar_query,
    classify_dataset,
    normalize_bars,
    parse_dataset_ref,
    snapshot_dataset,
    write_bar_snapshot,
)
from backtesting_suite.data import DataBundle, _funding_for_bars
from backtesting_suite.runner import validate_data_execution


def test_dataset_reference_and_identifiers_are_validated() -> None:
    assert parse_dataset_ref("binance.candles_1m") == ("binance", "candles_1m")
    for value in ("binance.candles_1m; DROP TABLE x", "binance", "a.b.c"):
        with pytest.raises(ClickHouseError):
            parse_dataset_ref(value)


def test_client_rejects_non_select_statements() -> None:
    for query in ("INSERT INTO t VALUES (1)", "SELECT 1; DROP TABLE t"):
        with pytest.raises(ClickHouseError, match="read-only SELECT"):
            ClickHouseClient._validate_select(query)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://clickhouse.example",
        "https://user:password@clickhouse.example",
        "https://clickhouse.example/?database=default",
        "https://clickhouse.example/#fragment",
    ],
)
def test_client_rejects_insecure_or_ambiguous_endpoints(endpoint: str) -> None:
    with pytest.raises(ClickHouseError, match="HTTPS URL"):
        ClickHouseClient(endpoint, "user", "secret")


def test_client_rejects_redirects_and_removes_partial_downloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeResponse:
        chunks = iter([b"ab", b"cd"])

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _size):
            return next(self.chunks, b"")

    class FakeOpener:
        def open(self, _request, timeout):
            assert timeout == 60.0
            return FakeResponse()

    assert clickhouse_module._RejectRedirects().redirect_request(
        None, None, 302, "Found", {}, "https://other.example/"
    ) is None
    monkeypatch.setattr(clickhouse_module, "_MAX_RESPONSE_BYTES", 3)
    monkeypatch.setattr(clickhouse_module.urllib.request, "build_opener", lambda *_: FakeOpener())
    destination = tmp_path / "partial.parquet"
    client = ClickHouseClient("https://clickhouse.example", "user", "password")

    with pytest.raises(ClickHouseError, match="2 GiB download limit"):
        client.parquet("SELECT 1", destination)
    assert not destination.exists()


def test_bar_query_uses_bounded_parameters_and_normalizes_symbol() -> None:
    query, params = build_bar_query(
        "binance",
        "candles_1m",
        timeframe="1h",
        market="spot",
        start="2024-01-01",
        end="2024-01-02",
        symbols=["BTCUSDT"],
    )
    assert "SELECT" in query
    assert "binance" in query and "candles_1m" in query
    assert "{start:String}" in query and "{end:String}" in query
    assert "{symbols:Array(String)}" in query
    assert "replaceRegexpOne(source.`symbol`, 'USDT$', '')" in query
    assert "BTCUSDT" not in query
    assert params["symbols"] == "['BTCUSDT']"


def test_bar_query_rejects_unsupported_source_and_timeframe() -> None:
    with pytest.raises(ClickHouseError, match="supported candle table"):
        build_bar_query(
            "crsp", "dsf_v2", timeframe="1d", market="spot",
            start="2024-01-01", end="2024-01-02", symbols=[],
        )


def test_raw_query_has_time_bounds_and_escaped_instrument_parameters() -> None:
    query, params = build_raw_query(
        "prediction", "kalshi_candles_1m", columns=["ticker", "price_close"],
        time_column="end_period_ts", time_type="DateTime64(0, 'UTC')",
        start="2024-01-01", end="2024-01-02", instrument_column="ticker",
        instruments=["ABC' OR 1=1"],
    )
    assert "LIMIT 2000001" in query
    assert "{instruments:Array(String)}" in query
    assert "ABC' OR 1=1" not in query
    assert "end_period_ts" in query
    assert params["instruments"] == "['ABC'' OR 1=1']"
    with pytest.raises(ClickHouseError, match="timeframe"):
        build_bar_query(
            "binance", "candles_1m", timeframe="7m", market="spot",
            start="2024-01-01", end="2024-01-02", symbols=[],
        )


@pytest.mark.parametrize(
    ("database", "table", "expected"),
    [
        ("binance", "candles_1m", "bar"),
        ("hyperliquid", "candles_1m", "bar"),
        ("features", "binance_intraday_features", "features"),
        ("features", "binance_intraday_targets", "targets"),
        ("ivydb", "opprcd2025", "options"),
        ("prediction", "kalshi_candles_1m", "prediction"),
        ("crsp", "dsf_v2", "raw"),
    ],
)
def test_dataset_capability_is_explicit(database: str, table: str, expected: str) -> None:
    assert classify_dataset(database, table) == expected


def test_normalize_bars_aggregates_ohlcv_and_keeps_missing_fields_nullable() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2024-01-01T00:00:00Z", "2024-01-01T00:01:00Z", "2024-01-01T01:00:00Z"]
            ),
            "symbol": ["BTCUSDT", "BTCUSDT", "BTCUSDT"],
            "open": [10.0, 11.0, 13.0],
            "high": [12.0, 14.0, 14.0],
            "low": [9.0, 10.0, 12.0],
            "close": [11.0, 13.0, 12.5],
            "volume_base": [2.0, 3.0, 4.0],
            "trade_count": [5, 6, 7],
        }
    )
    bars = normalize_bars(frame, timeframe="1h", market="spot", venue="binance")
    first = bars.iloc[0]
    assert len(bars) == 2
    assert first["symbol"] == "BTC"
    assert first["open"] == 10.0
    assert first["high"] == 14.0
    assert first["low"] == 9.0
    assert first["close"] == 13.0
    assert first["volume_base"] == 5.0
    assert first["trade_count"] == 11
    assert pd.isna(first["quote_volume"])


def test_binance_multiplier_prefix_remains_part_of_instrument_identity() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01T00:00:00Z"]),
            "symbol": ["1000SATSUSDT"],
            "open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0],
            "volume_base": [1.0],
        }
    )
    bars = normalize_bars(frame, timeframe="1h", market="spot", venue="binance")
    assert bars.iloc[0]["symbol"] == "1000SATS"


def test_write_bar_snapshot_is_hashed_and_manifest_loadable(tmp_path: Path) -> None:
    bars = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01T00:00:00Z"]),
            "symbol": ["BTC"],
            "open": [10.0], "high": [11.0], "low": [9.0], "close": [10.5],
            "volume_base": [2.0], "quote_volume": [None], "trade_count": [3],
            "taker_buy_volume_base": [None], "taker_buy_volume_quote": [None],
        }
    )
    manifest_path = write_bar_snapshot(
        bars, tmp_path, workspace=tmp_path, source="binance.candles_1m", market="spot", timeframe="1h",
        start="2024-01-01", end="2024-01-02", symbols=["BTCUSDT"],
    )
    manifest = json.loads(manifest_path.read_text())
    table = manifest["tables"]["spot_1h"]
    parquet_path = tmp_path / table["path"]
    assert parquet_path.exists()
    assert table["rows"] == 1
    assert table["sha256"] == hashlib.sha256(parquet_path.read_bytes()).hexdigest()
    assert manifest["source"]["table"] == "binance.candles_1m"


def test_write_bar_snapshot_rejects_empty_or_duplicate_bars(tmp_path: Path) -> None:
    with pytest.raises(ClickHouseError, match="no bars"):
        write_bar_snapshot(
            pd.DataFrame(), tmp_path, source="binance.candles_1m", market="spot",
            timeframe="1h", start="2024-01-01", end="2024-01-02", symbols=[],
        )

    duplicate = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01T00:00:00Z"] * 2),
            "symbol": ["BTC", "BTC"],
            "open": [1.0, 1.0], "high": [1.0, 1.0], "low": [1.0, 1.0],
            "close": [1.0, 1.0], "volume_base": [1.0, 1.0],
        }
    )
    with pytest.raises(ClickHouseError, match="duplicate"):
        write_bar_snapshot(
            duplicate, tmp_path, workspace=tmp_path, source="binance.candles_1m",
            market="spot", timeframe="1h", start="2024-01-01", end="2024-01-02", symbols=[],
        )


def test_snapshot_dataset_writes_immutable_bar_manifest(tmp_path: Path) -> None:
    class FakeClient:
        def parquet(self, query, destination, *, parameters=None):
            assert query.startswith("SELECT")
            assert parameters["symbols"] == "['BTCUSDT']"
            pd.DataFrame(
                {
                    "timestamp": pd.to_datetime(["2024-01-01T00:00:00Z"]),
                    "symbol": ["BTC"], "open": [10.0], "high": [11.0],
                    "low": [9.0], "close": [10.5], "volume_base": [2.0],
                    "quote_volume": [None], "trade_count": [3],
                    "taker_buy_volume_base": [4.0], "taker_buy_volume_quote": [None],
                }
            ).to_parquet(destination, index=False)

    first = snapshot_dataset(
        FakeClient(), "binance.candles_1m", start="2024-01-01", end="2024-01-02",
        output_dir=tmp_path / "data" / "clickhouse", workspace=tmp_path,
        symbols=["BTC"], timeframe="1h", market="spot",
    )
    second = snapshot_dataset(
        FakeClient(), "binance.candles_1m", start="2024-01-01", end="2024-01-02",
        output_dir=tmp_path / "data" / "clickhouse", workspace=tmp_path,
        symbols=["BTC"], timeframe="1h", market="spot",
    )
    manifest = json.loads(first.read_text())
    assert first == second
    assert manifest["tables"]["spot_1h"]["rows"] == 1
    assert manifest["tables"]["spot_1h"]["symbols"] == ["BTC"]
    assert (tmp_path / manifest["tables"]["spot_1h"]["path"]).exists()


def test_perpetual_backtest_requires_a_funding_series_when_enabled() -> None:
    config = SimpleNamespace(
        data=SimpleNamespace(market="perpetual"),
        execution=SimpleNamespace(funding=True),
    )
    data = DataBundle(fields={}, funding=pd.DataFrame(), metadata={"funding_available": False})
    with pytest.raises(ValueError, match="no funding series"):
        validate_data_execution(config, data)

    funded = DataBundle(fields={}, funding=pd.DataFrame(), metadata={"funding_available": True})
    validate_data_execution(config, funded)


def test_funding_is_available_only_for_aligned_rows_for_every_symbol(tmp_path: Path) -> None:
    funding_path = tmp_path / "funding.parquet"
    pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01T00:00:00Z"]),
            "symbol": ["BTC"], "funding_rate": [0.001],
        }
    ).to_parquet(funding_path, index=False)
    manifest = {"tables": {"funding_binance": {"path": "funding.parquet"}}}
    index = pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC")

    _, btc_available = _funding_for_bars(manifest, "perpetual", index, ["BTC"], tmp_path)
    _, mixed_available = _funding_for_bars(
        manifest, "perpetual", index, ["BTC", "ETH"], tmp_path
    )
    _, wrong_window_available = _funding_for_bars(
        manifest, "perpetual", index + pd.Timedelta(days=1), ["BTC"], tmp_path
    )

    assert btc_available
    assert not mixed_available
    assert not wrong_window_available


def test_sparse_funding_history_is_not_available(tmp_path: Path) -> None:
    pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01T00:00:00Z", "2024-01-04T00:00:00Z"]),
            "symbol": ["BTC", "BTC"], "funding_rate": [0.001, 0.001],
        }
    ).to_parquet(tmp_path / "funding.parquet", index=False)
    manifest = {"tables": {"funding_binance": {"path": "funding.parquet"}}}
    index = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")

    _, available = _funding_for_bars(manifest, "perpetual", index, ["BTC"], tmp_path)

    assert not available


def test_missing_binance_funding_settlement_is_not_treated_as_available(tmp_path: Path) -> None:
    pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01T00:00:00Z", "2024-01-01T16:00:00Z"]),
            "symbol": ["BTC", "BTC"], "funding_rate": [0.001, 0.001],
        }
    ).to_parquet(tmp_path / "funding.parquet", index=False)
    manifest = {"tables": {"funding_binance": {"path": "funding.parquet"}}}
    index = pd.date_range("2024-01-01", periods=24, freq="h", tz="UTC")

    _, available = _funding_for_bars(manifest, "perpetual", index, ["BTC"], tmp_path)

    assert not available


def test_null_funding_rate_does_not_count_as_a_settlement(tmp_path: Path) -> None:
    pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2024-01-01T00:00:00Z", "2024-01-01T08:00:00Z", "2024-01-01T16:00:00Z"]
            ),
            "symbol": ["BTC"] * 3, "funding_rate": [0.001, None, 0.001],
        }
    ).to_parquet(tmp_path / "funding.parquet", index=False)
    manifest = {"tables": {"funding_binance": {"path": "funding.parquet"}}}
    index = pd.date_range("2024-01-01", periods=24, freq="h", tz="UTC")

    _, available = _funding_for_bars(manifest, "perpetual", index, ["BTC"], tmp_path)

    assert not available
