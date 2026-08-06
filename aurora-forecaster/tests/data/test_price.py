import pandas as pd

from aurora_forecaster.data.price import fetch_btc_ohlcv, fetch_spy_ohlcv


class FakeExchange:
    def __init__(self):
        self.calls = []

    def fetch_ohlcv(self, symbol, timeframe, limit):
        self.calls.append((symbol, timeframe, limit))
        return [[1700000000000, 100.0, 101.0, 99.0, 100.5, 10.0]]


def test_fetch_btc_ohlcv_queries_binance_btc_usdt():
    exchange = FakeExchange()

    df = fetch_btc_ohlcv(timeframe="4h", limit=200, exchange=exchange)

    assert exchange.calls == [("BTC/USDT", "4h", 200)]
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(df) == 1


class FakeDownloader:
    def __init__(self):
        self.calls = []

    def __call__(self, ticker, period, interval):
        self.calls.append((ticker, period, interval))
        return pd.DataFrame({"Close": [1.0]})


def test_fetch_spy_ohlcv_queries_spy():
    downloader = FakeDownloader()

    df = fetch_spy_ohlcv(period="1y", interval="1h", downloader=downloader)

    assert downloader.calls == [("SPY", "1y", "1h")]
    assert not df.empty
