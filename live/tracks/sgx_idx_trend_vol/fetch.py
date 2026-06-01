"""yfinance pull + parquet cache for SGX + IDX daily OHLC.

Conventions:
  - One parquet per ticker under `data/<market>/<ticker>.parquet`.
  - Auto-adjusted close (yfinance `auto_adjust=True`), so the `Close` column
    is already split/dividend-adjusted. No `adj_factor` math needed.
  - Index is DatetimeIndex (per-market trading days).
  - Cache invalidation is manual: delete the file or call `fetch(force=True)`.

Idiom:
    panel = build_panel("sgx", start="2014-01-01", end="2022-12-31")
    # panel is a (date × ticker) DataFrame of adjusted closes
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from live.tracks.sgx_idx_trend_vol.universe import all_tickers

logger = logging.getLogger(__name__)

DATA_ROOT = Path(__file__).parent / "data"


def _cache_path(market: str, ticker: str) -> Path:
    return DATA_ROOT / market / f"{ticker}.parquet"


def fetch_one(
    ticker: str,
    market: str,
    start: str = "2014-01-01",
    end: str | None = None,
    force: bool = False,
) -> pd.DataFrame | None:
    """Fetch one ticker's OHLC into the parquet cache and return it.

    Returns None if yfinance has no data for the ticker (delisted, bad
    symbol, etc.) — the caller should drop the ticker from the universe.
    """
    path = _cache_path(market, ticker)
    if path.exists() and not force:
        cached = pd.read_parquet(path)
        # Cache covers the request iff its index spans [start, end].
        cached_covers = (
            not cached.empty
            and pd.Timestamp(start) >= cached.index.min().normalize()
            and (end is None or pd.Timestamp(end) <= cached.index.max().normalize())
        )
        if cached_covers:
            return cached

    # Import inside the function so the module imports without yfinance
    # installed (lets the eval tests run independently).
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError(
            "yfinance not installed. Run `pip install yfinance` in your venv."
        ) from exc

    df = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if df is None or df.empty:
        logger.warning("yfinance returned empty for %s", ticker)
        return None

    # yfinance returns a MultiIndex on columns when multiple tickers are
    # passed; for single-ticker calls it's flat. Normalise to flat lowercase.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df.index.name = "date"

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def fetch_market(
    market: str,
    start: str = "2014-01-01",
    end: str | None = None,
    force: bool = False,
) -> dict[str, pd.DataFrame]:
    """Fetch all tickers in `market`. Returns {ticker: ohlc_df}.

    Tickers with no yfinance data are silently dropped.
    """
    out: dict[str, pd.DataFrame] = {}
    for t in all_tickers(market):
        df = fetch_one(t, market, start=start, end=end, force=force)
        if df is not None and not df.empty:
            out[t] = df
        else:
            logger.warning("dropped %s (no data)", t)
    return out


def build_panel(
    market: str,
    field: str = "close",
    start: str = "2014-01-01",
    end: str | None = None,
    min_obs: int = 252,
) -> pd.DataFrame:
    """Build a (date × ticker) panel for one OHLC field.

    Tickers with fewer than `min_obs` observations in the window are
    dropped — keeps young listings from polluting cross-sectional ranks
    with NaN-noise.
    """
    market_data = fetch_market(market, start=start, end=end)
    frames: dict[str, pd.Series] = {}
    for t, df in market_data.items():
        if field not in df.columns:
            continue
        s = df[field].dropna()
        if len(s) < min_obs:
            continue
        frames[t] = s
    panel = pd.DataFrame(frames)
    if start:
        panel = panel.loc[start:]
    if end:
        panel = panel.loc[:end]
    return panel.sort_index()


def build_panels(
    market: str,
    start: str = "2014-01-01",
    end: str | None = None,
    min_obs: int = 252,
) -> dict[str, pd.DataFrame]:
    """Build close + volume + turnover panels in one pass.

    Returns {'close', 'volume', 'amount'} each a (date × ticker) DataFrame.
    `amount` is computed as close × volume (turnover proxy; yfinance does
    not provide native turnover).
    """
    market_data = fetch_market(market, start=start, end=end)
    close: dict[str, pd.Series] = {}
    volume: dict[str, pd.Series] = {}
    for t, df in market_data.items():
        if "close" not in df.columns or "volume" not in df.columns:
            continue
        c = df["close"].dropna()
        v = df["volume"].reindex(c.index)
        if len(c) < min_obs:
            continue
        close[t] = c
        volume[t] = v
    close_df = pd.DataFrame(close).sort_index()
    vol_df = pd.DataFrame(volume).reindex(close_df.index)
    amount_df = close_df * vol_df
    if start:
        close_df = close_df.loc[start:]
        vol_df = vol_df.loc[start:]
        amount_df = amount_df.loc[start:]
    if end:
        close_df = close_df.loc[:end]
        vol_df = vol_df.loc[:end]
        amount_df = amount_df.loc[:end]
    return {"close": close_df, "volume": vol_df, "amount": amount_df}
