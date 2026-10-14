"""Composable transaction-cost models, entirely independent of strategies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np
import pandas as pd

from backtesting_suite.config import CostConfig


class CostError(ValueError):
    """Raised when a requested cost model cannot be evaluated honestly."""


@dataclass(frozen=True)
class CostContext:
    timestamp: pd.Timestamp
    equity: float
    delta_weights: pd.Series
    quote_volume: pd.Series

    @property
    def traded_notional(self) -> pd.Series:
        return self.delta_weights.abs() * self.equity

    @property
    def active_trades(self) -> int:
        return int((self.delta_weights.abs() > 1e-12).sum())


@runtime_checkable
class TransactionCost(Protocol):
    name: str

    def calculate(self, context: CostContext) -> float: ...


@dataclass(frozen=True)
class ProportionalCost:
    name: str
    bps: float

    def calculate(self, context: CostContext) -> float:
        return float(context.traded_notional.sum() * self.bps / 10_000.0)


@dataclass(frozen=True)
class FixedCost:
    name: str
    amount_per_trade: float

    def calculate(self, context: CostContext) -> float:
        return float(context.active_trades * self.amount_per_trade)


@dataclass(frozen=True)
class SquareRootImpactCost:
    name: str
    coefficient_bps: float
    max_participation: float

    def calculate(self, context: CostContext) -> float:
        notional = context.traded_notional
        active = notional > 1e-12
        if not active.any():
            return 0.0
        volume = context.quote_volume.reindex(notional.index)
        if volume.loc[active].isna().any() or (volume.loc[active] <= 0).any():
            missing = list(volume.loc[active][volume.loc[active].isna() | (volume.loc[active] <= 0)].index)
            raise CostError(f"square-root impact needs positive quote volume for {missing}")
        participation = notional.loc[active] / volume.loc[active]
        if (participation > self.max_participation).any():
            offenders = participation[participation > self.max_participation]
            raise CostError(
                f"participation limit {self.max_participation:.2%} exceeded: "
                + ", ".join(f"{symbol}={value:.2%}" for symbol, value in offenders.items())
            )
        impact_bps = self.coefficient_bps * np.sqrt(participation)
        return float((notional.loc[active] * impact_bps / 10_000.0).sum())


def build_cost_models(configs: tuple[CostConfig, ...]) -> tuple[TransactionCost, ...]:
    models: list[TransactionCost] = []
    names: set[str] = set()
    for config in configs:
        if config.name in names:
            raise CostError(f"duplicate transaction cost name {config.name!r}")
        names.add(config.name)
        if config.type == "proportional":
            models.append(ProportionalCost(config.name, config.bps))
        elif config.type == "fixed":
            models.append(FixedCost(config.name, config.amount_per_trade))
        elif config.type == "square_root_impact":
            models.append(
                SquareRootImpactCost(
                    config.name, config.coefficient_bps, config.max_participation
                )
            )
        else:  # protected by configuration validation
            raise CostError(f"unknown cost type {config.type!r}")
    return tuple(models)
