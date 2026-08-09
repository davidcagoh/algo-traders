import pandas as pd
import pytest

from aurora_forecaster.text_fetch import (
    _gdelt_timestamp_to_epoch_ms,
    build_text_context,
    fetch_source_snippets,
)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _fake_get(routes):
    calls = []

    def fake_get(url):
        calls.append(url)
        for substring, payload in routes.items():
            if substring in url:
                return FakeResponse(payload)
        raise AssertionError(f"unexpected URL: {url}")

    fake_get.calls = calls
    return fake_get


def test_fetch_source_snippets_dispatches_gdelt():
    fake_get = _fake_get({"gdeltproject.org": {"articles": [{"title": "BTC rallies"}]}})

    result = fetch_source_snippets(
        "gdelt", query="bitcoin", start="20260101000000", end="20260102000000",
        api_keys={}, http_get=fake_get,
    )

    assert result == ["BTC rallies"]
    assert len(fake_get.calls) == 1


def test_fetch_source_snippets_dispatches_alphavantage():
    fake_get = _fake_get({"alphavantage.co": {"feed": [{"title": "BTC ETF inflows slow"}]}})

    result = fetch_source_snippets(
        "alphavantage", query="BTC", start="a", end="b",
        api_keys={"alphavantage": "test-key"}, http_get=fake_get,
    )

    assert result == ["BTC ETF inflows slow"]


def test_fetch_source_snippets_dispatches_currents():
    fake_get = _fake_get({"currentsapi.services": {"news": [{"title": "Bitcoin surges"}]}})

    result = fetch_source_snippets(
        "currents", query="bitcoin", start="a", end="b",
        api_keys={"currents": "test-key"}, http_get=fake_get,
    )

    assert result == ["Bitcoin surges"]


def test_fetch_source_snippets_rejects_unknown_source():
    with pytest.raises(ValueError):
        fetch_source_snippets(
            "guardian", query="bitcoin", start="a", end="b", api_keys={}, http_get=_fake_get({})
        )


def test_fetch_source_snippets_missing_api_key_raises_with_source_context():
    with pytest.raises(KeyError, match="alphavantage"):
        fetch_source_snippets(
            "alphavantage", query="BTC", start="a", end="b", api_keys={}, http_get=_fake_get({})
        )


def test_build_text_context_concatenates_multiple_sources():
    fake_get = _fake_get(
        {
            "gdeltproject.org": {"articles": [{"title": "BTC rallies"}]},
            "currentsapi.services": {"news": [{"title": "Bitcoin surges"}]},
        }
    )

    result = build_text_context(
        sources=("gdelt", "currents"), query="bitcoin", start="a", end="b",
        api_keys={"currents": "test-key"}, http_get=fake_get,
    )

    assert result == "BTC rallies Bitcoin surges"


def test_build_text_context_falls_back_when_no_sources():
    result = build_text_context(
        sources=(), query="bitcoin", start="a", end="b", api_keys={}, http_get=_fake_get({}),
    )

    assert result == "No text context available for this origin."


def test_gdelt_timestamp_to_epoch_ms_roundtrips_with_rolling_forecast_btc_format():
    from datetime import UTC, datetime

    dt = datetime(2026, 7, 20, 2, 0, 0, tzinfo=UTC)
    ts = dt.strftime("%Y%m%d%H%M%S")  # rolling_forecast_btc.py::_gdelt_timestamp's exact format

    assert _gdelt_timestamp_to_epoch_ms(ts) == int(dt.timestamp() * 1000)


def test_fetch_source_snippets_dispatches_funding(monkeypatch):
    calls = []

    def fake_fetch_funding_rate(coin, at_ms):
        calls.append((coin, at_ms))
        return {"coin": coin, "funding_rate": 0.0001, "time": at_ms}

    monkeypatch.setattr(
        "aurora_forecaster.text_fetch.fetch_funding_rate", fake_fetch_funding_rate
    )

    result = fetch_source_snippets(
        "funding", query="bitcoin", start="20260101000000", end="20260102000000", api_keys={},
    )

    assert result == ["BTC perp funding rate (Hyperliquid): +0.0100%"]
    assert calls == [("BTC", _gdelt_timestamp_to_epoch_ms("20260102000000"))]


def _fake_yfinance_df():
    index = pd.DatetimeIndex(
        ["2026-01-01T00:00:00Z", "2026-01-01T12:00:00Z", "2026-01-02T00:00:00Z"], tz="UTC"
    )
    return pd.DataFrame({("Close", "DX-Y.NYB"): [100.0, 101.0, 102.0]}, index=index)


def test_fetch_source_snippets_dispatches_dxy(monkeypatch):
    monkeypatch.setattr(
        "aurora_forecaster.text_fetch.fetch_dxy_ohlcv", lambda: _fake_yfinance_df()
    )

    result = fetch_source_snippets(
        "dxy", query="bitcoin", start="20260101000000", end="20260102000000", api_keys={},
    )

    # close_at_start=100.0 (nearest <= 2026-01-01T00:00), close_at_end=102.0
    # (nearest <= 2026-01-02T00:00) -> pct_change = (102-100)/100 = 0.02
    assert result == ["DXY: 102.00 (Δ over lookback: +2.0%)"]


def test_fetch_source_snippets_dispatches_spy(monkeypatch):
    df = pd.DataFrame(
        {("Close", "SPY"): [500.0, 505.0]},
        index=pd.DatetimeIndex(["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"], tz="UTC"),
    )
    monkeypatch.setattr("aurora_forecaster.text_fetch.fetch_spy_ohlcv", lambda: df)

    result = fetch_source_snippets(
        "spy", query="bitcoin", start="20260101000000", end="20260102000000", api_keys={},
    )

    assert result == ["S&P 500 (SPY): 505.00 (Δ over lookback: +1.0%)"]


def test_build_text_context_includes_funding_and_gdelt_sources(monkeypatch):
    monkeypatch.setattr(
        "aurora_forecaster.text_fetch.fetch_funding_rate",
        lambda coin, at_ms: {"coin": coin, "funding_rate": 0.0001, "time": at_ms},
    )
    fake_get = _fake_get({"gdeltproject.org": {"articles": [{"title": "BTC rallies"}]}})

    result = build_text_context(
        sources=("gdelt", "funding"), query="bitcoin", start="20260101000000",
        end="20260102000000", api_keys={}, http_get=fake_get,
    )

    assert result == "BTC rallies BTC perp funding rate (Hyperliquid): +0.0100%"
