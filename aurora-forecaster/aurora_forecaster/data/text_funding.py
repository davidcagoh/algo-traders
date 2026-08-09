"""Hyperliquid BTC perp funding rate, fetched as a single nearest-before
value per walk-forward origin (not the full history a backtest would want --
see `freqtrade-experiment/hmm-slope-experiment/research/scripts/
download_hyperliquid.py::fetch_funding_history` for that use case).

`fundingHistory` takes a flat payload, NOT the `req` wrapper `candleSnapshot`
uses -- a real, confirmed API divergence, not a typo.
"""

from __future__ import annotations

import time

HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz/info"
FUNDING_LOOKBACK_MS = 3 * 24 * 3_600_000  # 3 days; Hyperliquid pays every 8h,
# so this window always contains at least one real record


def post_funding_history(
    coin: str,
    start_ms: int,
    end_ms: int,
    http_post=None,
    max_attempts: int = 6,
    base_delay_seconds: float = 3.0,
) -> list[dict]:
    """POSTs a single fundingHistory request, retrying on HTTP 429 with
    exponential backoff -- same shape as
    `text_gdelt.py::fetch_gdelt_events` (6 attempts, 3s base), this
    project's established convention for rate-limited external APIs."""
    if http_post is None:
        import requests

        http_post = requests.post

    payload = {"type": "fundingHistory", "coin": coin, "startTime": start_ms, "endTime": end_ms}
    for attempt in range(max_attempts):
        response = http_post(HYPERLIQUID_API_URL, json=payload)
        if getattr(response, "status_code", 200) == 429 and attempt < max_attempts - 1:
            time.sleep(base_delay_seconds * (2**attempt))
            continue
        response.raise_for_status()
        return response.json()


def fetch_funding_rate(
    coin: str,
    at_ms: int,
    lookback_ms: int = FUNDING_LOOKBACK_MS,
    http_post=None,
) -> dict:
    """Nearest funding record at-or-before `at_ms` -- no lookahead, mirrors
    this project's origin_timestamp = last-lookback-bar principle
    (`realized.py`). Raises `ValueError` if nothing qualifies within the
    lookback window."""
    records = post_funding_history(coin, at_ms - lookback_ms, at_ms, http_post=http_post)
    candidates = [r for r in records if int(r["time"]) <= at_ms]
    if not candidates:
        raise ValueError(f"no funding rate at or before {at_ms} for {coin}")
    latest = max(candidates, key=lambda r: int(r["time"]))
    return {"coin": coin, "funding_rate": float(latest["fundingRate"]), "time": int(latest["time"])}
