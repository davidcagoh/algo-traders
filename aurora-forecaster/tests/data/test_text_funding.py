import pytest
import requests

from aurora_forecaster.data.text_funding import fetch_funding_rate, post_funding_history


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_post_funding_history_calls_http_post_with_flat_payload_and_returns_json():
    calls = []

    def fake_post(url, json):
        calls.append((url, json))
        return FakeResponse([{"time": 100, "fundingRate": "0.0001", "premium": "0.0"}])

    result = post_funding_history("BTC", start_ms=0, end_ms=1000, http_post=fake_post)

    assert len(calls) == 1
    url, payload = calls[0]
    assert url == "https://api.hyperliquid.xyz/info"
    assert payload == {"type": "fundingHistory", "coin": "BTC", "startTime": 0, "endTime": 1000}
    assert "req" not in payload
    assert result == [{"time": 100, "fundingRate": "0.0001", "premium": "0.0"}]


class RateLimitedResponse:
    def __init__(self, status_code):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return []


def test_post_funding_history_retries_on_429_then_succeeds(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    calls = []
    responses = [RateLimitedResponse(429), RateLimitedResponse(429), FakeResponse([])]

    def fake_post(url, json):
        calls.append(url)
        return responses.pop(0)

    result = post_funding_history("BTC", start_ms=0, end_ms=1000, http_post=fake_post)

    assert len(calls) == 3
    assert result == []


def test_post_funding_history_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    calls = []

    def fake_post(url, json):
        calls.append(url)
        return RateLimitedResponse(429)

    with pytest.raises(requests.HTTPError, match="429"):
        post_funding_history("BTC", start_ms=0, end_ms=1000, http_post=fake_post, max_attempts=3)

    assert len(calls) == 3


def test_post_funding_history_default_backoff_uses_growing_delays(monkeypatch):
    sleeps = []
    monkeypatch.setattr("time.sleep", lambda seconds: sleeps.append(seconds))

    def fake_post(url, json):
        return RateLimitedResponse(429)

    with pytest.raises(requests.HTTPError, match="429"):
        post_funding_history("BTC", start_ms=0, end_ms=1000, http_post=fake_post)

    assert len(sleeps) == 5
    assert sleeps == sorted(sleeps)
    assert sleeps[0] < sleeps[-1]


def test_fetch_funding_rate_returns_nearest_record_at_or_before_at_ms():
    records = [
        {"time": 100, "fundingRate": "0.0001", "premium": "0.0"},
        {"time": 500, "fundingRate": "0.0002", "premium": "0.0"},
        {"time": 900, "fundingRate": "0.0003", "premium": "0.0"},  # after at_ms, excluded
    ]

    def fake_post(url, json):
        return FakeResponse(records)

    result = fetch_funding_rate("BTC", at_ms=700, http_post=fake_post)

    assert result == {"coin": "BTC", "funding_rate": 0.0002, "time": 500}


def test_fetch_funding_rate_raises_when_no_record_at_or_before_at_ms():
    records = [{"time": 900, "fundingRate": "0.0003", "premium": "0.0"}]

    def fake_post(url, json):
        return FakeResponse(records)

    with pytest.raises(ValueError, match="BTC"):
        fetch_funding_rate("BTC", at_ms=100, http_post=fake_post)


def test_fetch_funding_rate_requests_bounded_lookback_window():
    calls = []

    def fake_post(url, json):
        calls.append(json)
        return FakeResponse([{"time": 100, "fundingRate": "0.0001", "premium": "0.0"}])

    fetch_funding_rate("BTC", at_ms=1_000_000, lookback_ms=1000, http_post=fake_post)

    assert calls[0]["startTime"] == 1_000_000 - 1000
    assert calls[0]["endTime"] == 1_000_000
