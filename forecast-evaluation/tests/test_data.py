import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from forecast_evaluation.data import load_snapshot, make_return_series


def test_returns_are_hourly_log_close_to_close():
    timestamps = pd.date_range("2026-01-01", periods=4, freq="h", tz="UTC")
    bars = pd.DataFrame({"timestamp": timestamps, "symbol": "BTC", "close": [10, 11, 12, 13]})

    result = make_return_series(bars, "BTC")

    assert np.isnan(result.values[0])
    assert result.values[1] == pytest.approx(np.log(11 / 10))
    assert result.values[2] == pytest.approx(np.log(12 / 11))


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda frame: pd.concat([frame, frame.iloc[[1]]]), "duplicate"),
        (lambda frame: frame.drop(index=2), "hourly grid"),
        (lambda frame: frame.assign(timestamp=frame["timestamp"] + pd.Timedelta(minutes=30)), "hourly bar boundaries"),
        (lambda frame: frame.assign(close=[1, 2, 0, 4]), "positive"),
    ],
)
def test_return_series_rejects_invalid_rows(mutate, message):
    base = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=4, freq="h", tz="UTC"),
        "symbol": "ETH", "close": [1.0, 2.0, 3.0, 4.0],
    })

    with pytest.raises(ValueError, match=message):
        make_return_series(mutate(base), "ETH")


def test_snapshot_loader_checks_manifest_and_parquet_hash(tmp_path):
    bars = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=3, freq="h", tz="UTC"),
        "symbol": ["BTC"] * 3,
        "close": [10.0, 11.0, 12.0],
    })
    data = tmp_path / "bars.parquet"
    bars.to_parquet(data)
    digest = hashlib.sha256(data.read_bytes()).hexdigest()
    manifest = {
        "snapshot_id": "fixed-snapshot",
        "source": {"provider": "clickhouse", "table": "binance.candles_1m"},
        "tables": {"spot_1h": {
            "timeframe": "1h", "market": "spot", "backtest_supported": True,
            "path": "bars.parquet", "sha256": digest, "symbols": ["BTC"],
        }},
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    snapshot = load_snapshot(
        manifest_path, expected_snapshot_id="fixed-snapshot", expected_sha256=digest,
        workspace=tmp_path,
    )

    assert snapshot.snapshot_id == "fixed-snapshot"
    assert snapshot.data_path == data
    assert snapshot.symbols == ("BTC",)

    with pytest.raises(ValueError, match="snapshot ID"):
        load_snapshot(manifest_path, expected_snapshot_id="wrong", expected_sha256=digest)

    data.write_bytes(b"mutated")
    with pytest.raises(ValueError, match="data hash"):
        load_snapshot(
            manifest_path, expected_snapshot_id="fixed-snapshot", expected_sha256=digest,
            workspace=tmp_path,
        )
