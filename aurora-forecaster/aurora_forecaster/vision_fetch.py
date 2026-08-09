"""Network-touching dispatch from a covariate source name to a rendered
chart image -- the vision-encoding sibling of `text_fetch.py::build_text_context`.

Reuses the same underlying fetchers already built for the text path
(`fetch_dxy_ohlcv`/`fetch_spy_ohlcv`/`post_funding_history`) -- only the
render step differs (a chart image instead of a rendered sentence).
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
from PIL import Image

from aurora_forecaster.data.price import fetch_dxy_ohlcv, fetch_spy_ohlcv
from aurora_forecaster.data.text_funding import post_funding_history
from aurora_forecaster.text_adapter import VisionSource
from aurora_forecaster.vision import render_line_chart


def fetch_source_series(source: VisionSource, start_ms: int, end_ms: int) -> list[float]:
    """Values for `source` between `start_ms` and `end_ms`, sorted
    chronologically. `funding` uses `post_funding_history`'s raw records;
    `dxy`/`spy` slice the Close column of `fetch_dxy_ohlcv`/`fetch_spy_ohlcv`'s
    OHLCV frame to the window."""
    if source == "funding":
        records = post_funding_history("BTC", start_ms, end_ms)
        ordered = sorted(records, key=lambda r: int(r["time"]))
        return [float(r["fundingRate"]) for r in ordered]
    elif source in ("dxy", "spy"):
        ticker = "DX-Y.NYB" if source == "dxy" else "SPY"
        df = fetch_dxy_ohlcv() if source == "dxy" else fetch_spy_ohlcv()
        return _closes_between(df, ticker, start_ms, end_ms)
    else:
        raise ValueError(f"unknown vision source: {source!r}")


def _closes_between(df: pd.DataFrame, ticker: str, start_ms: int, end_ms: int) -> list[float]:
    index = df.index if df.index.tz is not None else df.index.tz_localize("UTC")
    index = index.tz_convert("UTC")
    start = pd.Timestamp(start_ms, unit="ms", tz="UTC")
    end = pd.Timestamp(end_ms, unit="ms", tz="UTC")
    eligible = df.loc[(index >= start) & (index <= end)]
    close_col = ("Close", ticker) if isinstance(df.columns, pd.MultiIndex) else "Close"
    return [float(v) for v in eligible[close_col]]


def build_vision_context(
    vision_sources: Sequence[VisionSource], start_ms: int, end_ms: int
) -> Image.Image | None:
    """Renders a chart for `vision_sources`. `None` if `vision_sources` is
    empty -- a real, valid state (caller runs with pseudo-vision only, not
    an error). Raises `NotImplementedError` for more than one source --
    multi-source composite charts aren't built yet, fail loud rather than
    silently using only the first."""
    if not vision_sources:
        return None
    if len(vision_sources) > 1:
        raise NotImplementedError(
            f"combining multiple vision sources into one chart isn't built yet, "
            f"pick one: {vision_sources!r}"
        )
    values = fetch_source_series(vision_sources[0], start_ms, end_ms)
    return render_line_chart(values)
