from aurora_forecaster.data.text_guardian import build_guardian_url, fetch_guardian_articles


def test_build_guardian_url_includes_query_section_and_key():
    url = build_guardian_url(query="bitcoin", api_key="fakekey123", section="business")

    assert url.startswith("https://content.guardianapis.com/search?")
    assert "q=bitcoin" in url
    assert "api-key=fakekey123" in url
    assert "section=business" in url


def test_build_guardian_url_omits_section_when_not_given():
    url = build_guardian_url(query="bitcoin", api_key="fakekey123")

    assert "section=" not in url


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_guardian_articles_calls_http_get_and_returns_json():
    calls = []

    def fake_get(url):
        calls.append(url)
        return FakeResponse({"response": {"results": [{"webTitle": "BTC rallies"}]}})

    result = fetch_guardian_articles(query="bitcoin", api_key="fakekey123", http_get=fake_get)

    assert len(calls) == 1
    assert "q=bitcoin" in calls[0]
    assert result == {"response": {"results": [{"webTitle": "BTC rallies"}]}}
