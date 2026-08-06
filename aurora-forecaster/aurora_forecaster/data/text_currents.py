from urllib.parse import urlencode

CURRENTS_ENDPOINT = "https://api.currentsapi.services/v1/search"


def build_currents_url(keywords: str, api_key: str) -> str:
    params = {"keywords": keywords, "apiKey": api_key}
    return f"{CURRENTS_ENDPOINT}?{urlencode(params)}"


def fetch_currents_news(keywords: str, api_key: str, http_get=None):
    if http_get is None:
        import requests

        http_get = requests.get

    url = build_currents_url(keywords, api_key)
    response = http_get(url)
    response.raise_for_status()
    return response.json()
