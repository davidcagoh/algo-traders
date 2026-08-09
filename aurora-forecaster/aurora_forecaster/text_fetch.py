"""Network-touching dispatch from a text-source name to its `fetch_*`
function, normalized into ready-to-tokenize text via `text_adapter`.

Takes `sources`/`api_keys` directly rather than a `StreamConfig` object, so
this module has no dependency on `aurora_forecaster.ablation` -- keeps the
two independently testable and avoids a circular import (`ablation.py` is
the one that knows about `StreamConfig` and calls into this module, not the
other way around).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pandas as pd

from aurora_forecaster.data.price import fetch_dxy_ohlcv, fetch_spy_ohlcv
from aurora_forecaster.data.text_alphavantage import fetch_alpha_vantage_news
from aurora_forecaster.data.text_currents import fetch_currents_news
from aurora_forecaster.data.text_funding import fetch_funding_rate
from aurora_forecaster.data.text_gdelt import fetch_gdelt_events
from aurora_forecaster.text_adapter import TextSource, join_snippets, normalize_source_text


def _gdelt_timestamp_to_epoch_ms(ts: str) -> int:
    """Inverse of `rolling_forecast_btc.py::_gdelt_timestamp`."""
    return int(datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=UTC).timestamp() * 1000)


def _nearest_close_at_or_before(df: pd.DataFrame, ticker: str, at_ms: int) -> float:
    """Nearest OHLCV close at-or-before `at_ms` -- no lookahead. Handles
    yfinance's `(field, ticker)` MultiIndex column shape (confirmed
    2026-08-08, not the simple `"Close"` column the original `fetch_spy_ohlcv`
    docstring implied)."""
    index = df.index if df.index.tz is not None else df.index.tz_localize(UTC)
    index = index.tz_convert(UTC)
    at = pd.Timestamp(at_ms, unit="ms", tz=UTC)
    eligible = df.loc[index <= at]
    if eligible.empty:
        raise ValueError(f"no OHLCV row at or before {at_ms}")
    close_col = ("Close", ticker) if isinstance(df.columns, pd.MultiIndex) else "Close"
    return float(eligible[close_col].iloc[-1])


def fetch_source_snippets(
    source: TextSource,
    query: str,
    start: str,
    end: str,
    api_keys: dict[str, str],
    http_get=None,
) -> list[str]:
    """Fetches raw data from `source` and normalizes it to a list of
    snippets. GDELT needs no API key; Alpha Vantage and Currents require
    `api_keys[source]` and ignore `start`/`end` (their `fetch_*` signatures
    have no date-range parameter today). `funding`/`dxy`/`spy` are numeric
    covariates rendered as text (Aurora has no multivariate numeric input --
    see `text_adapter.py`'s module docstring); they need no API key, ignore
    `query`/`api_keys`, use `end` as the point-in-time to sample (no
    lookahead) and `start` as the lookback-start comparison point for
    dxy/spy's percent change, and don't thread `http_get` through -- their
    own DI (`downloader=`/`http_post=`) lives at the `data/` module layer.
    Raises `ValueError` for an unknown `source`, or `KeyError` (naming
    `source`) if a required API key is missing.
    """
    if source == "gdelt":
        raw = fetch_gdelt_events(query=query, start=start, end=end, http_get=http_get)
    elif source == "alphavantage":
        try:
            api_key = api_keys["alphavantage"]
        except KeyError as e:
            raise KeyError("missing API key for text source 'alphavantage'") from e
        raw = fetch_alpha_vantage_news(ticker=query, api_key=api_key, http_get=http_get)
    elif source == "currents":
        try:
            api_key = api_keys["currents"]
        except KeyError as e:
            raise KeyError("missing API key for text source 'currents'") from e
        raw = fetch_currents_news(keywords=query, api_key=api_key, http_get=http_get)
    elif source == "funding":
        raw = fetch_funding_rate(coin="BTC", at_ms=_gdelt_timestamp_to_epoch_ms(end))
    elif source in ("dxy", "spy"):
        at_ms = _gdelt_timestamp_to_epoch_ms(end)
        start_ms = _gdelt_timestamp_to_epoch_ms(start)
        ticker = "DX-Y.NYB" if source == "dxy" else "SPY"
        df = fetch_dxy_ohlcv() if source == "dxy" else fetch_spy_ohlcv()
        close_at_end = _nearest_close_at_or_before(df, ticker, at_ms)
        close_at_start = _nearest_close_at_or_before(df, ticker, start_ms)
        raw = {"close": close_at_end, "pct_change": (close_at_end - close_at_start) / close_at_start}
    else:
        raise ValueError(f"unknown text source: {source!r}")

    return normalize_source_text(source, raw)


def build_text_context(
    sources: Sequence[TextSource],
    query: str,
    start: str,
    end: str,
    api_keys: dict[str, str],
    http_get=None,
) -> str:
    """Fetches+normalizes every source in `sources`, concatenates all
    snippets across sources (in source order), and joins them into the
    single string a multimodal forecast call needs. One call per
    walk-forward origin."""
    snippets: list[str] = []
    for source in sources:
        snippets.extend(fetch_source_snippets(source, query, start, end, api_keys, http_get))
    return join_snippets(snippets)
