import pandas as pd

from aurora_forecaster.data.price import fetch_btc_ohlcv, fetch_spy_ohlcv


class FakeExchange:
    def __init__(self):
        self.calls = []

    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=None):
        self.calls.append((symbol, timeframe, since, limit))
        return [[1700000000000, 100.0, 101.0, 99.0, 100.5, 10.0]]


def test_fetch_btc_ohlcv_queries_binance_btc_usdt():
    exchange = FakeExchange()

    df = fetch_btc_ohlcv(timeframe="4h", limit=200, exchange=exchange)

    assert exchange.calls == [("BTC/USDT", "4h", None, 200)]
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(df) == 1


class PaginatingFakeExchange:
    """Returns `since`-anchored pages, advancing by one timeframe step per row."""

    def __init__(self, step_ms: int):
        self.step_ms = step_ms
        self.calls = []

    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=None):
        self.calls.append((symbol, timeframe, since, limit))
        return [
            [since + i * self.step_ms, 100.0, 101.0, 99.0, 100.5, 10.0] for i in range(limit)
        ]


def test_fetch_btc_ohlcv_paginates_when_limit_exceeds_max_page():
    exchange = PaginatingFakeExchange(step_ms=3_600_000)

    df = fetch_btc_ohlcv(
        timeframe="1h", limit=7, exchange=exchange, since=1_000_000, max_page=3
    )

    assert len(df) == 7
    assert [c[2] for c in exchange.calls] == [1_000_000, 1_000_000 + 3 * 3_600_000, 1_000_000 + 6 * 3_600_000]
    assert [c[3] for c in exchange.calls] == [3, 3, 1]
    assert df["timestamp"].is_monotonic_increasing
    assert df["timestamp"].iloc[0] == 1_000_000
    assert df["timestamp"].iloc[-1] == 1_000_000 + 6 * 3_600_000


def test_fetch_btc_ohlcv_stops_early_when_exchange_runs_out_of_data():
    class ExhaustingExchange:
        def __init__(self):
            self.n_calls = 0

        def fetch_ohlcv(self, symbol, timeframe, since=None, limit=None):
            self.n_calls += 1
            if self.n_calls == 1:
                return [[since, 100.0, 101.0, 99.0, 100.5, 10.0] for _ in range(2)]
            return []  # no more data available

    exchange = ExhaustingExchange()

    df = fetch_btc_ohlcv(timeframe="1h", limit=10, exchange=exchange, since=0, max_page=2)

    assert len(df) == 2
    assert exchange.n_calls == 2


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
