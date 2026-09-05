from __future__ import annotations

import pytest

from backtesting_suite.config import ConfigError, RunConfig


def minimum_config() -> dict:
    return {
        "experiment": "test",
        "data": {
            "manifest": "manifest.json",
            "market": "spot",
            "timeframe": "1d",
            "universe": ["BTC"],
            "start": "2024-01-01",
            "end": "2024-12-31",
        },
        "strategy": {"import": "module:Strategy"},
        "execution": {},
    }


def test_minimum_config_has_safe_timing_and_constraints() -> None:
    config = RunConfig.from_mapping(minimum_config())
    assert config.execution.signal_delay_bars == 1
    assert config.execution.price_field == "open"
    assert config.execution.rebalance_policy == "every_bar"
    assert config.execution.constraints.violation == "raise"


def test_cost_components_are_validated() -> None:
    raw = minimum_config()
    raw["execution"] = {
        "transaction_costs": [{"type": "proportional", "name": "fee", "bps": 5}]
    }
    config = RunConfig.from_mapping(raw)
    assert config.execution.transaction_costs[0].bps == 5


def test_unknown_cost_component_is_rejected() -> None:
    raw = minimum_config()
    raw["execution"] = {"transaction_costs": [{"type": "magic"}]}
    with pytest.raises(ConfigError, match="transaction cost type"):
        RunConfig.from_mapping(raw)


def test_negative_feature_availability_lag_is_rejected() -> None:
    raw = minimum_config()
    raw["data"]["features"] = [
        {"name": "macro", "path": "macro.parquet", "availability_lag": "-1D"}
    ]
    with pytest.raises(ConfigError, match="cannot be negative"):
        RunConfig.from_mapping(raw)


@pytest.mark.parametrize("name", ["transaction_cost", "funding_pnl", "borrow_cost"])
def test_cost_names_cannot_overwrite_accounting_columns(name: str) -> None:
    raw = minimum_config()
    raw["execution"] = {
        "transaction_costs": [{"type": "proportional", "name": name, "bps": 5}]
    }
    with pytest.raises(ConfigError, match="reserved transaction cost names"):
        RunConfig.from_mapping(raw)
