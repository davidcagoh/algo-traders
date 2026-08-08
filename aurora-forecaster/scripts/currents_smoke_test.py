"""
Manual smoke test: confirms CURRENTS_API_KEY (loaded from the repo root
.env, never printed) can fetch real news for BTC and SPY-related keywords.

Usage: python scripts/currents_smoke_test.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from aurora_forecaster.data.text_currents import fetch_currents_news

REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


def main() -> None:
    load_dotenv(REPO_ROOT_ENV)
    api_key = os.environ["CURRENTS_API_KEY"]

    for keywords in ["bitcoin", "S&P 500"]:
        result = fetch_currents_news(keywords=keywords, api_key=api_key)
        news = result.get("news", [])
        print(f"{keywords!r}: {len(news)} articles")
        if news:
            print(f"  sample: {news[0].get('title')!r}")
        else:
            print(f"  raw response keys: {list(result.keys())}")


if __name__ == "__main__":
    main()
