import pandas as pd
import pytest

from aurora_forecaster.vision_fetch import build_vision_context, fetch_source_series


def test_fetch_source_series_dispatches_funding(monkeypatch):
    calls = []

    def fake_post_funding_history(coin, start_ms, end_ms):
        calls.append((coin, start_ms, end_ms))
        return [
            {"time": 200, "fundingRate": "0.0002", "premium": "0.0"},
            {"time": 100, "fundingRate": "0.0001", "premium": "0.0"},
        ]

    monkeypatch.setattr(
        "aurora_forecaster.vision_fetch.post_funding_history", fake_post_funding_history
    )

    result = fetch_source_series("funding", start_ms=100, end_ms=200)

    assert result == [0.0001, 0.0002]  # sorted by time
    assert calls == [("BTC", 100, 200)]


def _fake_df():
    index = pd.DatetimeIndex(
        ["2026-01-01T00:00:00Z", "2026-01-01T12:00:00Z", "2026-01-02T00:00:00Z"], tz="UTC"
    )
    return pd.DataFrame({("Close", "DX-Y.NYB"): [100.0, 101.0, 102.0]}, index=index)


def test_fetch_source_series_dispatches_dxy(monkeypatch):
    monkeypatch.setattr("aurora_forecaster.vision_fetch.fetch_dxy_ohlcv", lambda: _fake_df())
    start_ms = int(pd.Timestamp("2026-01-01T00:00:00Z").timestamp() * 1000)
    end_ms = int(pd.Timestamp("2026-01-02T00:00:00Z").timestamp() * 1000)

    result = fetch_source_series("dxy", start_ms=start_ms, end_ms=end_ms)

    assert result == [100.0, 101.0, 102.0]


def test_fetch_source_series_dispatches_spy(monkeypatch):
    df = pd.DataFrame(
        {("Close", "SPY"): [500.0, 505.0]},
        index=pd.DatetimeIndex(["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"], tz="UTC"),
    )
    monkeypatch.setattr("aurora_forecaster.vision_fetch.fetch_spy_ohlcv", lambda: df)
    start_ms = int(pd.Timestamp("2026-01-01T00:00:00Z").timestamp() * 1000)
    end_ms = int(pd.Timestamp("2026-01-02T00:00:00Z").timestamp() * 1000)

    result = fetch_source_series("spy", start_ms=start_ms, end_ms=end_ms)

    assert result == [500.0, 505.0]


def test_build_vision_context_returns_none_for_empty_sources():
    assert build_vision_context([], start_ms=0, end_ms=1000) is None


def test_build_vision_context_raises_for_multiple_sources():
    with pytest.raises(NotImplementedError, match="one"):
        build_vision_context(["funding", "dxy"], start_ms=0, end_ms=1000)


def test_build_vision_context_renders_a_chart(monkeypatch):
    monkeypatch.setattr(
        "aurora_forecaster.vision_fetch.post_funding_history",
        lambda coin, start_ms, end_ms: [
            {"time": 100, "fundingRate": "0.0001", "premium": "0.0"},
            {"time": 200, "fundingRate": "0.0002", "premium": "0.0"},
        ],
    )

    image = build_vision_context(["funding"], start_ms=100, end_ms=200)

    assert image is not None
    assert image.size[0] > 0 and image.size[1] > 0
