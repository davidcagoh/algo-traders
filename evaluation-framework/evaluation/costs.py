"""Fee, slippage, and funding cost models for per-trade P&L.

Literature: Bysik & Ślepaczuk 2026 (`../literature/strategy-evaluation/methods/2606.00060-cost-aware-walk-forward-bitcoin.pdf`)
— cost-aware trade filtering under transaction costs. Chauhan 2026 (SSRN
6861958) — turnover-scaled costs. Fu 2025
(`../literature/strategy-evaluation/surveys/2510.05533-new-quant-llm-survey.pdf`)
— full costs, capacity, latency as deployment-realism requirements.

Funding is not optional here: on this project's own Hyperliquid paper run,
funding drag was 5.4x taker fees (-12.08 vs -2.25 USDC), with 85% of it
falling on the winning trades — a cost model without funding is wrong by a
factor of five on this venue. Freqtrade also silently ignores the config
`"fee"` key in some code paths, so realised cost should be reconstructed
from the trade ledger, not trusted from backtest config (see
`../freqtrade-experiment/hmm-slope-experiment/research/_index.md`).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CostModel:
    model_id: str
    maker_bps: float = 0.0
    taker_bps: float = 0.0
    slippage_bps: float = 0.0
    funding_series: pd.Series | None = None  # indexed by timestamp, rate per funding interval
    borrow_bps: float = 0.0
    min_notional: float = 0.0


def apply_costs(trades: pd.DataFrame, model: CostModel) -> pd.DataFrame:
    """Break a trades frame's gross P&L into net P&L plus fee/slippage/funding.

    `trades` must have columns: `notional` (position size in quote ccy),
    `is_maker` (bool), `open_time`, `close_time`, `profit_abs` (gross P&L
    in quote ccy). Returns a copy with added columns: `fee_cost`,
    `slippage_cost`, `funding_cost`, `net_profit_abs`.
    """
    out = trades.copy()
    fee_bps = out["is_maker"].map({True: model.maker_bps, False: model.taker_bps})
    out["fee_cost"] = out["notional"] * fee_bps / 10_000.0
    out["slippage_cost"] = out["notional"] * model.slippage_bps / 10_000.0

    if model.funding_series is not None and len(model.funding_series):
        out["funding_cost"] = [
            _accrued_funding(
                row["notional"], row["open_time"], row["close_time"], model.funding_series
            )
            for _, row in out.iterrows()
        ]
    else:
        out["funding_cost"] = 0.0

    out["net_profit_abs"] = (
        out["profit_abs"] - out["fee_cost"] - out["slippage_cost"] - out["funding_cost"]
    )
    return out


def _accrued_funding(
    notional: float, open_time: pd.Timestamp, close_time: pd.Timestamp, funding: pd.Series
) -> float:
    """Sum funding payments (rate * notional) over funding events within
    [open_time, close_time). Positive rate means longs pay shorts."""
    window = funding[(funding.index >= open_time) & (funding.index < close_time)]
    return float((window * notional).sum())


def turnover(trades: pd.DataFrame) -> float:
    """Sum of absolute notional traded — a scale-free proxy for cost exposure."""
    return float(trades["notional"].abs().sum())


def cost_drag_summary(trades: pd.DataFrame, model: CostModel) -> dict[str, float]:
    priced = apply_costs(trades, model)
    return {
        "gross_profit": float(priced["profit_abs"].sum()),
        "net_profit": float(priced["net_profit_abs"].sum()),
        "fee_cost": float(priced["fee_cost"].sum()),
        "slippage_cost": float(priced["slippage_cost"].sum()),
        "funding_cost": float(priced["funding_cost"].sum()),
        "turnover": turnover(trades),
        "n_trades": float(len(trades)),
    }


def cost_grid(
    trades: pd.DataFrame,
    models: list[CostModel],
    metric: str = "net_profit",
) -> pd.DataFrame:
    """One row per model, recomputed headline cost metrics."""
    rows: list[dict[str, float | str]] = []
    for m in models:
        row: dict[str, float | str] = dict(cost_drag_summary(trades, m))
        row["model_id"] = m.model_id
        rows.append(row)
    df = pd.DataFrame(rows).set_index("model_id")
    if metric not in df.columns:
        raise ValueError(f"unknown metric {metric!r}; choose from {list(df.columns)}")
    return df.sort_values(metric, ascending=False)


def breakeven_cost(trades: pd.DataFrame, max_bps: float = 500.0, steps: int = 200) -> float:
    """Round-trip cost (bps of notional, symmetric maker=taker=slippage/2
    each) at which net P&L crosses zero. Returns `max_bps` if the strategy
    never breaks even within the search range (i.e. edge is very large or
    already negative before any cost).
    """
    gross = float(trades["profit_abs"].sum())
    if gross <= 0:
        return 0.0
    total_notional = turnover(trades)
    if total_notional == 0:
        return max_bps

    for bps in _linspace(0.0, max_bps, steps):
        cost = total_notional * bps / 10_000.0
        if gross - cost <= 0:
            return bps
    return max_bps


def _linspace(start: float, stop: float, steps: int) -> list[float]:
    if steps <= 1:
        return [start]
    step = (stop - start) / (steps - 1)
    return [start + i * step for i in range(steps)]
