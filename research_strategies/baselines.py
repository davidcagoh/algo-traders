"""Simple examples showing the target-weight-only strategy contract."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from backtesting_suite.data import DataBundle


class BuyAndHoldStrategy:
    """Equal-weight all requested assets after each asset becomes available."""

    def generate_targets(
        self, data: DataBundle, params: Mapping[str, Any]
    ) -> pd.DataFrame:
        available = data.field("close").notna().astype(float)
        denominator = available.sum(axis=1)
        denominator = denominator.where(denominator != 0.0)
        return available.div(denominator, axis=0).fillna(0.0)


class SmaCrossStrategy:
    """Long (or long/short) each asset using only trailing close history."""

    def generate_targets(
        self, data: DataBundle, params: Mapping[str, Any]
    ) -> pd.DataFrame:
        fast = int(params.get("fast_window", 50))
        slow = int(params.get("slow_window", 200))
        if fast <= 0 or slow <= fast:
            raise ValueError("require 0 < fast_window < slow_window")
        long_short = bool(params.get("long_short", False))
        gross = float(params.get("gross_exposure", 1.0))
        close = data.field("close")
        fast_mean = close.rolling(fast, min_periods=fast).mean()
        slow_mean = close.rolling(slow, min_periods=slow).mean()
        if long_short:
            signal = (fast_mean > slow_mean).astype(float) * 2.0 - 1.0
            signal = signal.where(slow_mean.notna(), 0.0)
        else:
            signal = (fast_mean > slow_mean).astype(float)
            signal = signal.where(slow_mean.notna(), 0.0)
        active = signal.abs().sum(axis=1)
        active = active.where(active != 0.0)
        return signal.div(active, axis=0).fillna(0.0) * gross


class TimeSeriesMomentumStrategy:
    """Long positive trailing momentum; optionally short negative momentum."""

    def generate_targets(
        self, data: DataBundle, params: Mapping[str, Any]
    ) -> pd.DataFrame:
        lookback = int(params.get("lookback_periods", 90))
        gross = float(params.get("gross_exposure", 1.0))
        long_short = bool(params.get("long_short", False))
        if lookback <= 0:
            raise ValueError("lookback_periods must be positive")
        if gross <= 0:
            raise ValueError("gross_exposure must be positive")

        momentum = data.field("close").pct_change(lookback, fill_method=None)
        if long_short:
            signal = (momentum > 0.0).astype(float) * 2.0 - 1.0
        else:
            signal = (momentum > 0.0).astype(float)
        signal = signal.where(momentum.notna(), 0.0)
        active = signal.abs().sum(axis=1).replace(0.0, float("nan"))
        return signal.div(active, axis=0).fillna(0.0) * gross


class CrossSectionalMomentumStrategy:
    """Equal-weight recent winners and, optionally, recent losers."""

    def generate_targets(
        self, data: DataBundle, params: Mapping[str, Any]
    ) -> pd.DataFrame:
        lookback = int(params.get("lookback_periods", 90))
        skip = int(params.get("skip_periods", 1))
        long_count = int(params.get("long_count", 3))
        short_count = int(params.get("short_count", 0))
        gross = float(params.get("gross_exposure", 1.0))
        if lookback <= 0 or skip < 0:
            raise ValueError("lookback_periods must be positive and skip_periods non-negative")
        if long_count < 0 or short_count < 0 or long_count + short_count == 0:
            raise ValueError("at least one of long_count or short_count must be positive")
        if long_count + short_count > len(data.symbols):
            raise ValueError("long_count + short_count exceeds the universe size")
        if gross <= 0:
            raise ValueError("gross_exposure must be positive")

        close = data.field("close")
        momentum = close.shift(skip).pct_change(lookback, fill_method=None)
        valid = momentum.notna()
        long_mask = (
            momentum.rank(axis=1, ascending=False, method="first") <= long_count
            if long_count
            else pd.DataFrame(False, index=momentum.index, columns=momentum.columns)
        ) & valid
        short_mask = (
            momentum.rank(axis=1, ascending=True, method="first") <= short_count
            if short_count
            else pd.DataFrame(False, index=momentum.index, columns=momentum.columns)
        ) & valid & ~long_mask

        split_budget = long_count > 0 and short_count > 0
        long_budget = gross / 2.0 if split_budget else gross
        short_budget = gross / 2.0 if split_budget else gross
        targets = pd.DataFrame(0.0, index=close.index, columns=close.columns)
        if long_count:
            counts = long_mask.sum(axis=1).astype(float).replace(0.0, float("nan"))
            targets += long_mask.div(counts, axis=0).fillna(0.0) * long_budget
        if short_count:
            counts = short_mask.sum(axis=1).astype(float).replace(0.0, float("nan"))
            targets -= short_mask.div(counts, axis=0).fillna(0.0) * short_budget
        return targets
