import time
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


def fetch_gdelt_events(
    query: str,
    start: str,
    end: str,
    max_records: int = 250,
    http_get=None,
    max_attempts: int = 6,
    base_delay_seconds: float = 3.0,
):
    """Fetches GDELT DOC API results, retrying with exponential backoff on
    HTTP 429. GDELT's free endpoint rate-limits bursty callers -- confirmed
    2026-08-08 running the walk-forward loop: a 5-attempt/1s-base backoff
    (max ~31s of waiting) survived 2 of 4 origins in one run before giving
    out, so max_attempts=6 with a 3s base (max ~93s of waiting: 3+6+12+24+48)
    is the hardened default. Same pattern as
    `download_hyperliquid.py::post_with_retry`."""
    if http_get is None:
        import requests

        http_get = requests.get

    url = build_gdelt_url(query, start, end, max_records)
    for attempt in range(max_attempts):
        response = http_get(url)
        if getattr(response, "status_code", 200) == 429 and attempt < max_attempts - 1:
            time.sleep(base_delay_seconds * (2**attempt))
            continue
        response.raise_for_status()
        return response.json()
