from urllib.parse import urlencode

GDELT_DOC_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"


def build_gdelt_url(query: str, start: str, end: str, max_records: int = 250) -> str:
    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "startdatetime": start,
        "enddatetime": end,
        "maxrecords": max_records,
    }
    return f"{GDELT_DOC_ENDPOINT}?{urlencode(params)}"


def fetch_gdelt_events(query: str, start: str, end: str, max_records: int = 250, http_get=None):
    if http_get is None:
        import requests

        http_get = requests.get

    url = build_gdelt_url(query, start, end, max_records)
    response = http_get(url)
    response.raise_for_status()
    return response.json()
