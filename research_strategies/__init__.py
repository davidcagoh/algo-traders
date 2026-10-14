"""Platform-agnostic research strategies for the shared backtesting suite."""

from research_strategies.baselines import BuyAndHoldStrategy, SmaCrossStrategy

__all__ = ["BuyAndHoldStrategy", "SmaCrossStrategy"]
