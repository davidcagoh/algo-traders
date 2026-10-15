from aurora_forecaster.data.text_alphavantage import (
    build_alpha_vantage_url,
    fetch_alpha_vantage_news,
)


def test_build_alpha_vantage_url_includes_ticker_and_key():
    url = build_alpha_vantage_url(ticker="BTC", api_key="fakekey123")

    assert url.startswith("https://www.alphavantage.co/query?")
    assert "function=NEWS_SENTIMENT" in url
    assert "tickers=BTC" in url
    assert "apikey=fakekey123" in url


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_alpha_vantage_news_calls_http_get_and_returns_json():
    calls = []

    def fake_get(url):
        calls.append(url)
        return FakeResponse({"feed": [{"title": "SPY drifts higher"}]})

    result = fetch_alpha_vantage_news(ticker="SPY", api_key="fakekey123", http_get=fake_get)

    assert len(calls) == 1
    assert "tickers=SPY" in calls[0]
    assert result == {"feed": [{"title": "SPY drifts higher"}]}
