"""
Manual smoke test: confirms GUARDIAN_API_KEY (loaded from the repo root
.env, never printed) can fetch real articles for BTC and SPY-related
queries. Guardian is "verify it works, don't use it yet" per standing
project decision — not wired into any pipeline.

Usage: python scripts/guardian_smoke_test.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from aurora_forecaster.data.text_guardian import fetch_guardian_articles

REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


def main() -> None:
    load_dotenv(REPO_ROOT_ENV)
    api_key = os.environ["GUARDIAN_API_KEY"]

    for query in ["bitcoin", "S&P 500"]:
        result = fetch_guardian_articles(query=query, api_key=api_key, section="business")
        results = result.get("response", {}).get("results", [])
        print(f"{query!r}: {len(results)} articles")
        if results:
            print(f"  sample: {results[0].get('webTitle')!r}")
        else:
            print(f"  raw response: {result.get('response', {})}")


if __name__ == "__main__":
    main()
