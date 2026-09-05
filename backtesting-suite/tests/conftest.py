from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

from backtesting_suite.data import DataBundle


WORKSPACE = Path(__file__).resolve().parents[2]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))


@pytest.fixture
def daily_bundle() -> DataBundle:
    index = pd.date_range("2024-01-01", periods=4, freq="1D", tz="UTC")
    columns = ["BTC"]
    open_prices = pd.DataFrame([100.0, 110.0, 121.0, 133.1], index=index, columns=columns)
    fields = {
        "open": open_prices,
        "high": open_prices,
        "low": open_prices,
        "close": open_prices,
        "volume_base": pd.DataFrame(1_000.0, index=index, columns=columns),
        "quote_volume": pd.DataFrame(1_000_000.0, index=index, columns=columns),
        "trade_count": pd.DataFrame(100, index=index, columns=columns),
        "taker_buy_volume_base": pd.DataFrame(500.0, index=index, columns=columns),
        "taker_buy_volume_quote": pd.DataFrame(500_000.0, index=index, columns=columns),
    }
    return DataBundle(
        fields=fields,
        funding=pd.DataFrame(0.0, index=index, columns=columns),
        metadata={"timeframe": "1d", "market": "spot"},
    )
