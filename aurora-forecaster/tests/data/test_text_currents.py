from aurora_forecaster.data.text_currents import build_currents_url, fetch_currents_news


def test_build_currents_url_includes_keywords_and_key():
    url = build_currents_url(keywords="bitcoin", api_key="fakekey123")

    assert url.startswith("https://api.currentsapi.services/v1/search?")
    assert "keywords=bitcoin" in url
    assert "apiKey=fakekey123" in url


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_currents_news_calls_http_get_and_returns_json():
    calls = []

    def fake_get(url):
        calls.append(url)
        return FakeResponse({"news": [{"title": "BTC rallies"}]})

    result = fetch_currents_news(keywords="bitcoin", api_key="fakekey123", http_get=fake_get)

    assert len(calls) == 1
    assert "keywords=bitcoin" in calls[0]
    assert result == {"news": [{"title": "BTC rallies"}]}
