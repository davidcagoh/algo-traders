from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from timeseries_lab import AmbiguousSeries, TimeSeriesLab
from timeseries_lab.regression import ols


def _table(path: Path, frame: pd.DataFrame, members: list[str]) -> dict:
    frame.to_parquet(path, index=False)
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "columns": list(frame.columns),
        "members": members,
        "start": pd.to_datetime(frame["timestamp"], utc=True).min().isoformat(),
        "end": pd.to_datetime(frame["timestamp"], utc=True).max().isoformat(),
    }


@pytest.fixture
def lab(tmp_path: Path) -> TimeSeriesLab:
    index = pd.date_range("2024-01-01", periods=8, freq="1D", tz="UTC")
    spot = pd.DataFrame(
        {
            "timestamp": list(index) * 2,
            "symbol": ["BTC"] * 8 + ["ETH"] * 8,
            "open": list(range(100, 108)) + list(range(200, 208)),
            "high": list(range(100, 108)) + list(range(200, 208)),
            "low": list(range(100, 108)) + list(range(200, 208)),
            "close": list(range(100, 108)) + list(range(200, 208)),
            "volume_base": [1.0] * 16,
            "quote_volume": [1000.0] * 16,
            "trade_count": [10] * 16,
            "taker_buy_volume_base": [0.5] * 16,
            "taker_buy_volume_quote": [500.0] * 16,
        }
    )
    fred = pd.DataFrame(
        {
            "timestamp": index,
            "series": ["VIXCLS"] * 8,
            "description": ["CBOE VIX close"] * 8,
            "value": np.arange(10.0, 18.0),
        }
    )
    spot_path = tmp_path / "spot.parquet"
    fred_path = tmp_path / "fred.parquet"
    spot_metadata = _table(spot_path, spot, ["BTC", "ETH"])
    manifest = {
        "tables": {
            "spot_1d": spot_metadata,
            "perpetual_1d": dict(spot_metadata),
            "fred": _table(fred_path, fred, ["VIXCLS"]),
        }
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return TimeSeriesLab(manifest_path, root=tmp_path, verify_checksums=True)


def test_search_shorthand_and_selective_load(lab: TimeSeriesLab) -> None:
    assert "fred:VIXCLS:value" in lab.search("vix")["id"].tolist()
    series = lab["fred:VIXCLS"]
    assert series.iloc[0] == 10.0
    assert str(series.index.tz) == "UTC"


def test_ambiguous_member_fails_with_suggestions(lab: TimeSeriesLab) -> None:
    with pytest.raises(AmbiguousSeries, match="Suggestions"):
        lab.catalog.resolve("BTC")


def test_transform_and_alignment(lab: TimeSeriesLab) -> None:
    returns = lab["spot_1d:BTC | log_return"]
    assert returns.dropna().iloc[0] == pytest.approx(np.log(101 / 100))
    frame = lab.frame(
        {"btc": "spot_1d:BTC:close", "vix": "fred:VIXCLS"},
        join="inner",
    )
    assert list(frame.columns) == ["btc", "vix"]
    assert len(frame) == 8


def test_ad_hoc_csv_series_can_join_manifest_data(tmp_path: Path, lab: TimeSeriesLab) -> None:
    path = tmp_path / "paper.csv"
    pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3, freq="1D"),
            "signal": [1.0, 2.0, 3.0],
        }
    ).to_csv(path, index=False)
    signal = lab.read_file(path, timestamp="date", value="signal", name="paper")
    frame = lab.frame({"paper": signal, "btc": "spot_1d:BTC:close"}, join="inner")
    assert frame.shape == (3, 2)
    assert str(frame.index.tz) == "UTC"


def test_ols_recovers_known_relationship_with_hac_errors() -> None:
    index = pd.date_range("2020-01-01", periods=100, freq="1D", tz="UTC")
    x = pd.DataFrame({"x": np.linspace(-2, 2, 100)}, index=index)
    y = 1.5 + 2.25 * x["x"]
    result = ols(y, x, hac_lags="auto")
    assert result.coefficients["constant"] == pytest.approx(1.5)
    assert result.coefficients["x"] == pytest.approx(2.25)
    assert result.r_squared == pytest.approx(1.0)


def test_lab_regression_accepts_naive_ad_hoc_series(lab: TimeSeriesLab) -> None:
    index = pd.date_range("2024-01-01", periods=8, freq="1D")
    explanatory = pd.Series(np.arange(8.0), index=index, name="signal")
    dependent = 3.0 + 0.5 * explanatory
    result = lab.regress(dependent, explanatory, hac_lags=None)
    assert result.observations == 8
    assert result.coefficients["signal"] == pytest.approx(0.5)


def test_bad_checksum_is_rejected(tmp_path: Path, lab: TimeSeriesLab) -> None:
    ref = lab.catalog.resolve("fred:VIXCLS")
    manifest = json.loads(lab.catalog.manifest_path.read_text())
    manifest["tables"]["fred"]["sha256"] = "0" * 64
    lab.catalog.manifest_path.write_text(json.dumps(manifest))
    broken = TimeSeriesLab(lab.catalog.manifest_path, root=tmp_path, verify_checksums=True)
    with pytest.raises(ValueError, match="checksum mismatch"):
        broken.get(ref.id)
