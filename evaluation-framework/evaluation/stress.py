"""Order-book slippage stress and capacity estimation.

Literature: Sepper 2026, *Slippage-at-Risk*
(`../literature/strategy-evaluation/methods/2603.09164-slippage-at-risk.pdf`)
— forward-looking order-book slippage and concentration stress for
perpetual futures. Bieganowski & Ślepaczuk 2026
(`../literature/strategy-evaluation/empirical-audits/2602.00776-explainable-crypto-microstructure.pdf`)
— fee sensitivity, maker/taker comparison, flash-crash stress; notes
latency and queue position remain unmodeled.

No true L2 order-book data is retained anywhere in this repository today.
`depth_from_ohlcv` is an OHLCV-derived proxy, not a substitute — it is
labeled as an upper-bound-quality estimate everywhere it's used, and real
book-snapshot capture is a separate, unstarted data task.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def depth_from_ohlcv(ohlcv: pd.DataFrame, window: int = 20) -> pd.Series:
    """Proxy market depth from OHLCV: dollar volume / (high-low range).

    Larger range relative to volume implies thinner liquidity (price moved
    further per unit traded). This is an *upper bound* on real depth — a
    real order book can be far thinner intraperiod than this rolling proxy
    suggests, since OHLCV aggregates away intraperiod order-flow structure.
    """
    dollar_vol = ohlcv["volume"] * ohlcv["close"]
    rng = (ohlcv["high"] - ohlcv["low"]).replace(0, np.nan)
    depth = (dollar_vol / rng).rolling(window, min_periods=1).mean()
    return depth.bfill()


@dataclass(frozen=True)
class SlippageAtRisk:
    order_size: float
    quantile: float
    slippage_bps: float
    is_proxy: bool


def slippage_at_risk(
    order_size: float,
    depth: pd.Series,
    quantile: float = 0.95,
) -> SlippageAtRisk:
    """Slippage-at-Risk: the `quantile`-worst expected slippage (bps) for
    executing `order_size` against a depth series (proxy or real).

    Square-root market-impact model: slippage_bps ~ k * sqrt(order_size / depth),
    with k calibrated from the empirical dispersion of 1/depth so thinner
    historical periods produce proportionally larger stress estimates.
    """
    if depth.empty or (depth <= 0).all():
        raise ValueError("depth series must have at least one positive value")
    inv_depth = (1.0 / depth[depth > 0]).to_numpy()
    k = float(np.quantile(inv_depth, quantile)) * order_size
    impact_bps = 10_000.0 * np.sqrt(max(k, 0.0))
    return SlippageAtRisk(
        order_size=order_size, quantile=quantile, slippage_bps=impact_bps, is_proxy=True
    )


def flash_crash_scenario(returns: pd.Series, multiplier: float = 3.0) -> pd.Series:
    """Stress test: scale the worst single-period return in `returns` by
    `multiplier`, holding all else equal. Returns the modified series."""
    stressed = returns.copy()
    worst_idx = stressed.idxmin()
    stressed.loc[worst_idx] = stressed.loc[worst_idx] * multiplier
    return stressed


def capacity_curve(
    order_sizes: list[float], depth: pd.Series, quantile: float = 0.95
) -> pd.DataFrame:
    """Position size -> expected slippage bps, for a range of order sizes."""
    rows = []
    for size in order_sizes:
        sar = slippage_at_risk(size, depth, quantile)
        rows.append({"order_size": size, "slippage_bps": sar.slippage_bps})
    return pd.DataFrame(rows).set_index("order_size")
