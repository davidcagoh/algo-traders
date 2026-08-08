import pandas as pd

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

_TIMEFRAME_UNIT_MS = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}


def _timeframe_to_ms(timeframe: str) -> int:
    unit = timeframe[-1]
    if unit not in _TIMEFRAME_UNIT_MS:
        raise ValueError(f"unsupported timeframe unit in {timeframe!r}")
    return int(timeframe[:-1]) * _TIMEFRAME_UNIT_MS[unit]


def fetch_btc_ohlcv(
    timeframe: str = "1h",
    limit: int = 500,
    exchange=None,
    since: int | None = None,
    max_page: int = 1000,
) -> pd.DataFrame:
    """Fetch BTC/USDT OHLCV. `since` (ms epoch) pages forward past a single
    exchange call's cap (`max_page`, 1000 for Binance) when `limit` exceeds
    it — needed to reconstruct a specific historical span (e.g. a forecast's
    lookback + horizon window) rather than just "most recent N bars".
    """
    if exchange is None:
        import ccxt

        exchange = ccxt.binance()

    if since is None or limit <= max_page:
        raw = exchange.fetch_ohlcv("BTC/USDT", timeframe=timeframe, since=since, limit=limit)
        return pd.DataFrame(raw, columns=OHLCV_COLUMNS)

    step_ms = _timeframe_to_ms(timeframe)
    rows: list[list[float]] = []
    cursor = since
    while len(rows) < limit:
        page_limit = min(max_page, limit - len(rows))
        page = exchange.fetch_ohlcv(
            "BTC/USDT", timeframe=timeframe, since=cursor, limit=page_limit
        )
        if not page:
            break
        rows.extend(page)
        if len(page) < page_limit:
            break
        cursor = page[-1][0] + step_ms

    return pd.DataFrame(rows, columns=OHLCV_COLUMNS)


def fetch_spy_ohlcv(period: str = "2y", interval: str = "1h", downloader=None) -> pd.DataFrame:
    if downloader is None:
        import yfinance as yf

        downloader = yf.download

    return downloader("SPY", period=period, interval=interval)
