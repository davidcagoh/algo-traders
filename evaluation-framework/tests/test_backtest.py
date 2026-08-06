from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from evaluation.backtest import (
    build_returns_matrix,
    load_daily_returns,
    load_trade_returns,
    load_wallet_curve,
)

pytest.importorskip("pyarrow")


def _make_freqtrade_zip(path: Path, n_days: int = 30, n_trades: int = 5) -> None:
    rng = np.random.default_rng(0)
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D", tz="UTC")
    wallet = pd.DataFrame(
        {"date": dates, "total_quote": 1000.0 * np.cumprod(1 + rng.normal(0.001, 0.01, n_days))}
    )

    trades = [{"profit_ratio": float(x)} for x in rng.normal(0.01, 0.02, n_trades)]
    result = {"strategy": {"MyStrategy": {"trades": trades}}}

    with zipfile.ZipFile(path, "w") as archive:
        import io

        buf = io.BytesIO()
        wallet.to_feather(buf)
        archive.writestr("backtest-result_wallet.feather", buf.getvalue())
        archive.writestr("backtest-result.json", json.dumps(result))


@pytest.fixture
def ft_zip(tmp_path) -> Path:
    p = tmp_path / "run.zip"
    _make_freqtrade_zip(p)
    return p


def test_load_wallet_curve(ft_zip):
    wallet = load_wallet_curve(ft_zip)
    assert len(wallet) > 0
    assert wallet.iloc[0] > 0


def test_load_wallet_curve_missing_feather_raises(tmp_path):
    p = tmp_path / "empty.zip"
    with zipfile.ZipFile(p, "w") as archive:
        archive.writestr("nothing.json", "{}")
    with pytest.raises(FileNotFoundError):
        load_wallet_curve(p)


def test_load_daily_returns(ft_zip):
    r = load_daily_returns(ft_zip)
    assert (r != 0).any()


def test_load_trade_returns(ft_zip):
    t = load_trade_returns(ft_zip)
    assert len(t) == 5


def test_load_trade_returns_empty_trades(tmp_path):
    p = tmp_path / "notrades.zip"
    result = {"strategy": {"S": {"trades": []}}}
    with zipfile.ZipFile(p, "w") as archive:
        archive.writestr("backtest-result.json", json.dumps(result))
    t = load_trade_returns(p)
    assert t.empty


def test_build_returns_matrix(ft_zip, tmp_path):
    other = tmp_path / "run2.zip"
    _make_freqtrade_zip(other, n_days=30, n_trades=3)
    matrix = build_returns_matrix({"a": ft_zip, "b": other})
    assert set(matrix.columns) == {"a", "b"}
    assert not matrix.isna().any().any()
