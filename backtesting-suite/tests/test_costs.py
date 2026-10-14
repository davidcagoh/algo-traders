from __future__ import annotations

import pandas as pd
import pytest

from backtesting_suite.execution.costs import (
    CostContext,
    CostError,
    FixedCost,
    ProportionalCost,
    SquareRootImpactCost,
)


def context(volume: float = 1_000.0) -> CostContext:
    return CostContext(
        timestamp=pd.Timestamp("2024-01-01", tz="UTC"),
        equity=100.0,
        delta_weights=pd.Series({"BTC": 0.5, "ETH": -0.25}),
        quote_volume=pd.Series({"BTC": volume, "ETH": volume}),
    )


def test_proportional_cost_uses_total_traded_notional() -> None:
    assert ProportionalCost("fee", 100).calculate(context()) == pytest.approx(0.75)


def test_fixed_cost_counts_active_assets() -> None:
    assert FixedCost("ticket", 2.0).calculate(context()) == 4.0


def test_square_root_impact_enforces_participation_limit() -> None:
    model = SquareRootImpactCost("impact", coefficient_bps=20, max_participation=0.01)
    with pytest.raises(CostError, match="participation limit"):
        model.calculate(context(volume=100.0))
