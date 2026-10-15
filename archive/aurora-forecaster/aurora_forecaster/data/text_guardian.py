from urllib.parse import urlencode

GUARDIAN_ENDPOINT = "https://content.guardianapis.com/search"


def build_guardian_url(query: str, api_key: str, section: str | None = None) -> str:
    params = {"q": query, "api-key": api_key}
    if section:
        params["section"] = section
    return f"{GUARDIAN_ENDPOINT}?{urlencode(params)}"


def fetch_guardian_articles(query: str, api_key: str, section: str | None = None, http_get=None):
    if http_get is None:
        import requests

        http_get = requests.get

    url = build_guardian_url(query, api_key, section)
    response = http_get(url)
    response.raise_for_status()
    return response.json()
