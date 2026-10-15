import pytest
import requests

from aurora_forecaster.data.text_gdelt import build_gdelt_url, fetch_gdelt_events


def test_build_gdelt_url_encodes_query_and_dates():
    url = build_gdelt_url(
        query="bitcoin",
        start="20260101000000",
        end="20260102000000",
        max_records=100,
    )

    assert url.startswith("https://api.gdeltproject.org/api/v2/doc/doc?")
    assert "query=bitcoin" in url
    assert "startdatetime=20260101000000" in url
    assert "enddatetime=20260102000000" in url
    assert "maxrecords=100" in url
    assert "format=json" in url


def test_build_gdelt_url_encodes_multi_word_query():
    url = build_gdelt_url(query="S&P 500", start="a", end="b")

    assert "query=" in url
    assert " " not in url


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.raised = False

    def raise_for_status(self):
        self.raised = True

    def json(self):
        return self._payload


def test_fetch_gdelt_events_calls_http_get_with_built_url_and_returns_json():
    calls = []

    def fake_get(url):
        calls.append(url)
        return FakeResponse({"articles": [{"title": "BTC rallies"}]})

    result = fetch_gdelt_events(
        query="bitcoin", start="20260101000000", end="20260102000000", http_get=fake_get
    )

    assert len(calls) == 1
    assert result == {"articles": [{"title": "BTC rallies"}]}


class RateLimitedResponse:
    def __init__(self, status_code):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return {"articles": []}


def test_fetch_gdelt_events_retries_on_429_then_succeeds(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    calls = []
    responses = [RateLimitedResponse(429), RateLimitedResponse(429), FakeResponse({"articles": []})]

    def fake_get(url):
        calls.append(url)
        return responses.pop(0)

    result = fetch_gdelt_events(
        query="bitcoin", start="20260101000000", end="20260102000000", http_get=fake_get
    )

    assert len(calls) == 3
    assert result == {"articles": []}


def test_fetch_gdelt_events_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    calls = []

    def fake_get(url):
        calls.append(url)
        return RateLimitedResponse(429)

    with pytest.raises(requests.HTTPError, match="429"):
        fetch_gdelt_events(
            query="bitcoin", start="20260101000000", end="20260102000000", http_get=fake_get,
            max_attempts=3,
        )

    assert len(calls) == 3


def test_fetch_gdelt_events_default_backoff_uses_growing_delays(monkeypatch):
    sleeps = []
    monkeypatch.setattr("time.sleep", lambda seconds: sleeps.append(seconds))

    def fake_get(url):
        return RateLimitedResponse(429)

    with pytest.raises(requests.HTTPError, match="429"):
        fetch_gdelt_events(query="bitcoin", start="a", end="b", http_get=fake_get)

    # 6 attempts by default (GDELT's rate-limit window survived 5 in
    # practice, see 2026-08-08 session-log), so 5 sleeps between them,
    # each strictly longer than the last.
    assert len(sleeps) == 5
    assert sleeps == sorted(sleeps)
    assert sleeps[0] < sleeps[-1]
