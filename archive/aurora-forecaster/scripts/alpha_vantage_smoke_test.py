"""
Manual smoke test: confirms ALPHA_VANTAGE_API_KEY (loaded from the repo
root .env, never printed) can fetch real ticker-tagged news for BTC and SPY.

Usage: python scripts/alpha_vantage_smoke_test.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from aurora_forecaster.data.text_alphavantage import fetch_alpha_vantage_news

REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


def main() -> None:
    load_dotenv(REPO_ROOT_ENV)
    api_key = os.environ["ALPHA_VANTAGE_API_KEY"]

    for ticker in ["BTC", "SPY"]:
        result = fetch_alpha_vantage_news(ticker=ticker, api_key=api_key)
        feed = result.get("feed", [])
        print(f"{ticker}: {len(feed)} articles")
        if feed:
            print(f"  sample: {feed[0].get('title')!r}")
        elif "Information" in result or "Note" in result:
            print(f"  api message: {result}")


if __name__ == "__main__":
    main()
