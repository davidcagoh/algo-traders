import pandas as pd

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def fetch_btc_ohlcv(timeframe: str = "1h", limit: int = 500, exchange=None) -> pd.DataFrame:
    if exchange is None:
        import ccxt

        exchange = ccxt.binance()

    raw = exchange.fetch_ohlcv("BTC/USDT", timeframe=timeframe, limit=limit)
    return pd.DataFrame(raw, columns=OHLCV_COLUMNS)


def fetch_spy_ohlcv(period: str = "2y", interval: str = "1h", downloader=None) -> pd.DataFrame:
    if downloader is None:
        import yfinance as yf

        downloader = yf.download

    return downloader("SPY", period=period, interval=interval)
