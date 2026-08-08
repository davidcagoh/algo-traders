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
