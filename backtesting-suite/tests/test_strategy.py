from __future__ import annotations

from typing import Any, Mapping

import pandas as pd
import pytest

from backtesting_suite.data import DataBundle
from backtesting_suite.strategy import StrategyError, assert_no_lookahead, normalize_targets
from research_strategies.baselines import (
    CrossSectionalMomentumStrategy,
    SmaCrossStrategy,
    TimeSeriesMomentumStrategy,
)


class CheatingStrategy:
    def generate_targets(
        self, data: DataBundle, params: Mapping[str, Any]
    ) -> pd.DataFrame:
        future_up = data.field("close").shift(-1) > data.field("close")
        return future_up.astype(float)


def test_trailing_sma_passes_no_lookahead_check(daily_bundle: DataBundle) -> None:
    strategy = SmaCrossStrategy()
    params = {"fast_window": 1, "slow_window": 2}
    targets = normalize_targets(strategy.generate_targets(daily_bundle, params), daily_bundle)
    assert_no_lookahead(strategy, daily_bundle, params, targets)


def test_future_shift_is_rejected(daily_bundle: DataBundle) -> None:
    # Expand the fixture so the checker has enough observations.
    index = pd.date_range("2024-01-01", periods=30, freq="1D", tz="UTC")
    fields = {
        name: frame.reindex(index).ffill() for name, frame in daily_bundle.fields.items()
    }
    fields["close"].iloc[:, 0] = range(30)
    fields["open"].iloc[:, 0] = range(30)
    bundle = DataBundle(
        fields=fields,
        funding=daily_bundle.funding.reindex(index).fillna(0.0),
    )
    strategy = CheatingStrategy()
    targets = normalize_targets(strategy.generate_targets(bundle, {}), bundle)
    with pytest.raises(StrategyError, match="look-ahead"):
        assert_no_lookahead(strategy, bundle, {}, targets)


def test_cross_sectional_momentum_is_market_neutral_after_warmup(
    daily_bundle: DataBundle,
) -> None:
    index = pd.date_range("2024-01-01", periods=6, freq="1D", tz="UTC")
    columns = ["A", "B", "C", "D"]
    close = pd.DataFrame(
        {
            "A": [100, 101, 103, 106, 110, 115],
            "B": [100, 100, 101, 101, 102, 102],
            "C": [100, 99, 97, 94, 90, 85],
            "D": [100, 98, 96, 95, 94, 93],
        },
        index=index,
        dtype=float,
    )
    fields = {
        name: pd.DataFrame(1.0, index=index, columns=columns)
        for name in daily_bundle.fields
    }
    fields["close"] = close
    fields["open"] = close
    bundle = DataBundle(
        fields=fields,
        funding=pd.DataFrame(0.0, index=index, columns=columns),
    )
    strategy = CrossSectionalMomentumStrategy()
    targets = strategy.generate_targets(
        bundle,
        {"lookback_periods": 2, "skip_periods": 0, "long_count": 1, "short_count": 1},
    )
    final = targets.iloc[-1]
    assert final.sum() == pytest.approx(0.0)
    assert final.abs().sum() == pytest.approx(1.0)
    assert final["A"] == pytest.approx(0.5)
    assert final["C"] == pytest.approx(-0.5)


def test_time_series_momentum_is_long_only_after_positive_lookback(
    daily_bundle: DataBundle,
) -> None:
    strategy = TimeSeriesMomentumStrategy()

    targets = strategy.generate_targets(
        daily_bundle, {"lookback_periods": 2, "long_short": False}
    )

    assert targets.iloc[:2, 0].eq(0.0).all()
    assert targets.iloc[2:, 0].eq(1.0).all()
