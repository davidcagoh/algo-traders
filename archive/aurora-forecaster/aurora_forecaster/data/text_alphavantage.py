from urllib.parse import urlencode

ALPHA_VANTAGE_ENDPOINT = "https://www.alphavantage.co/query"


def build_alpha_vantage_url(ticker: str, api_key: str, topics: str | None = None) -> str:
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": ticker,
        "apikey": api_key,
    }
    if topics:
        params["topics"] = topics
    return f"{ALPHA_VANTAGE_ENDPOINT}?{urlencode(params)}"


def fetch_alpha_vantage_news(ticker: str, api_key: str, topics: str | None = None, http_get=None):
    if http_get is None:
        import requests

        http_get = requests.get

    url = build_alpha_vantage_url(ticker, api_key, topics)
    response = http_get(url)
    response.raise_for_status()
    return response.json()
