"""Transparent bar-based execution for target-weight strategies."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from backtesting_suite.config import ConstraintConfig, ExecutionConfig
from backtesting_suite.data import DataBundle
from backtesting_suite.execution.costs import CostContext, build_cost_models
from backtesting_suite.result import BacktestResult


class ExecutionError(ValueError):
    """Raised when requested execution cannot be simulated without inventing data."""


def _constrain(weights: pd.Series, config: ConstraintConfig) -> pd.Series:
    gross = float(weights.abs().sum())
    net = abs(float(weights.sum()))
    largest = float(weights.abs().max()) if len(weights) else 0.0
    cash = 1.0 - float(weights.sum())
    violations = []
    if gross > config.max_gross_exposure + 1e-12:
        violations.append(f"gross={gross:.6f}>{config.max_gross_exposure:.6f}")
    if net > config.max_net_exposure + 1e-12:
        violations.append(f"abs(net)={net:.6f}>{config.max_net_exposure:.6f}")
    if largest > config.max_abs_weight + 1e-12:
        violations.append(f"max_weight={largest:.6f}>{config.max_abs_weight:.6f}")
    if cash < config.min_cash_weight - 1e-12:
        violations.append(f"cash={cash:.6f}<{config.min_cash_weight:.6f}")
    if not violations:
        return weights
    if config.violation == "raise":
        raise ExecutionError("target constraint violation: " + "; ".join(violations))

    factors = [1.0]
    if gross > 0:
        factors.append(config.max_gross_exposure / gross)
    if net > 0:
        factors.append(config.max_net_exposure / net)
    if largest > 0:
        factors.append(config.max_abs_weight / largest)
    positive_net = float(weights.sum())
    if positive_net > 0:
        factors.append((1.0 - config.min_cash_weight) / positive_net)
    return weights * max(0.0, min(factors))


@dataclass(frozen=True)
class BarExecutionModel:
    """Execute delayed targets at a configured bar field and hold to the next bar.

    Positive funding means longs pay and shorts receive. Borrow is charged only
    on short notional. Transaction-cost components are applied to traded
    notional before the next holding-period return.
    """

    def simulate(
        self,
        data: DataBundle,
        targets: pd.DataFrame,
        config: ExecutionConfig,
    ) -> BacktestResult:
        if len(data.index) < 2:
            raise ExecutionError("at least two price bars are required")
        prices = data.field(config.price_field).astype(float)
        quote_volume = data.field("quote_volume").astype(float)
        delayed = targets.shift(config.signal_delay_bars).fillna(0.0)
        cost_models = build_cost_models(config.transaction_costs)

        symbols = prices.columns
        equity = float(config.initial_cash)
        pretrade_weights = pd.Series(0.0, index=symbols)
        equity_points = {data.index[0]: equity}
        return_rows: list[dict[str, float | pd.Timestamp]] = []
        cost_rows: list[dict[str, float | pd.Timestamp]] = []
        trade_rows: list[dict[str, float | str | pd.Timestamp]] = []
        executed_rows: list[pd.Series] = []
        ending_rows: list[pd.Series] = []
        turnover_points: dict[pd.Timestamp, float] = {}
        last_requested: pd.Series | None = None

        for position in range(len(data.index) - 1):
            timestamp = data.index[position]
            next_timestamp = data.index[position + 1]
            start_equity = equity
            requested = delayed.iloc[position].copy()
            target_changed = last_requested is None or not np.allclose(
                requested.to_numpy(), last_requested.to_numpy(), rtol=0.0, atol=1e-12
            )
            should_rebalance = config.rebalance_policy == "every_bar" or target_changed
            desired = (
                _constrain(requested, config.constraints)
                if should_rebalance
                else pretrade_weights.copy()
            )
            last_requested = requested
            current_price = prices.iloc[position]
            next_price = prices.iloc[position + 1]
            required = (desired.abs() > 1e-12) | (pretrade_weights.abs() > 1e-12)
            missing = required & (current_price.isna() | next_price.isna())
            if missing.any() and config.missing_price_policy == "raise":
                raise ExecutionError(
                    f"missing {config.price_field} price over {timestamp} -> {next_timestamp} "
                    f"for {list(symbols[missing])}"
                )
            asset_returns = (next_price / current_price - 1.0).replace([np.inf, -np.inf], np.nan)
            asset_returns = asset_returns.fillna(0.0)

            delta = desired - pretrade_weights
            missing_fill = (delta.abs() > 1e-12) & current_price.isna()
            if missing_fill.any():
                raise ExecutionError(
                    f"cannot fill at missing {config.price_field} price at {timestamp} "
                    f"for {list(symbols[missing_fill])}"
                )
            turnover = float(delta.abs().sum())
            turnover_points[timestamp] = turnover
            context = CostContext(
                timestamp=timestamp,
                equity=start_equity,
                delta_weights=delta,
                quote_volume=quote_volume.iloc[position],
            )
            component_costs = {model.name: model.calculate(context) for model in cost_models}
            transaction_cost = float(sum(component_costs.values()))
            if transaction_cost >= start_equity:
                raise ExecutionError(
                    f"transaction costs {transaction_cost:.2f} exhaust equity {start_equity:.2f}"
                )
            investable = start_equity - transaction_cost
            position_values = desired * investable
            cash = (1.0 - float(desired.sum())) * investable

            elapsed_years = (next_timestamp - timestamp).total_seconds() / (365.0 * 86_400.0)
            borrow_cost = float(
                desired.clip(upper=0.0).abs().sum()
                * investable
                * config.annual_borrow_bps
                / 10_000.0
                * elapsed_years
            )
            funding_rates = data.funding.iloc[position] if config.funding else pd.Series(0.0, index=symbols)
            funding_pnl = float(-(desired * funding_rates).sum() * investable)
            market_pnl = float((position_values * asset_returns).sum())
            ending_position_values = position_values * (1.0 + asset_returns)
            ending_cash = cash + funding_pnl - borrow_cost
            equity = float(ending_position_values.sum() + ending_cash)
            if not np.isfinite(equity) or equity <= 0:
                raise ExecutionError(f"portfolio equity became non-positive at {next_timestamp}")
            ending_weight = ending_position_values / equity

            executed = desired.rename(timestamp)
            ending = ending_weight.rename(next_timestamp)
            executed_rows.append(executed)
            ending_rows.append(ending)
            equity_points[next_timestamp] = equity
            transaction_return = -transaction_cost / start_equity
            funding_return = funding_pnl / start_equity
            borrow_return = -borrow_cost / start_equity
            gross_return = market_pnl / start_equity
            net_return = equity / start_equity - 1.0
            return_rows.append(
                {
                    "timestamp": next_timestamp,
                    "gross_return": gross_return,
                    "transaction_cost_return": transaction_return,
                    "funding_return": funding_return,
                    "borrow_return": borrow_return,
                    "net_return": net_return,
                }
            )
            cost_rows.append(
                {
                    "timestamp": timestamp,
                    **component_costs,
                    "transaction_cost": transaction_cost,
                    "funding_pnl": funding_pnl,
                    "borrow_cost": borrow_cost,
                }
            )
            for symbol in symbols[delta.abs() > 1e-12]:
                trade_rows.append(
                    {
                        "timestamp": timestamp,
                        "symbol": symbol,
                        "side": "buy" if delta[symbol] > 0 else "sell",
                        "pre_weight": float(pretrade_weights[symbol]),
                        "target_weight": float(desired[symbol]),
                        "delta_weight": float(delta[symbol]),
                        "fill_price": float(current_price[symbol]),
                        "notional": float(abs(delta[symbol]) * start_equity),
                    }
                )
            pretrade_weights = ending_weight

        returns = pd.DataFrame(return_rows).set_index("timestamp")
        costs = pd.DataFrame(cost_rows).set_index("timestamp").fillna(0.0)
        trades = pd.DataFrame(
            trade_rows,
            columns=[
                "timestamp", "symbol", "side", "pre_weight", "target_weight",
                "delta_weight", "fill_price", "notional",
            ],
        )
        executed_weights = pd.DataFrame(executed_rows).reindex(columns=symbols)
        executed_weights.index.name = "timestamp"
        ending_weights = pd.DataFrame(ending_rows).reindex(columns=symbols)
        ending_weights.index.name = "timestamp"
        return BacktestResult(
            returns=returns,
            equity=pd.Series(equity_points, name="equity"),
            targets=targets,
            executed_weights=executed_weights,
            ending_weights=ending_weights,
            turnover=pd.Series(turnover_points, name="turnover"),
            trades=trades,
            costs=costs,
            metadata={
                "execution_model": "bar",
                "price_field": config.price_field,
                "signal_delay_bars": config.signal_delay_bars,
                "rebalance_policy": config.rebalance_policy,
                "funding_enabled": config.funding,
                "cost_components": [model.name for model in cost_models],
            },
        )
