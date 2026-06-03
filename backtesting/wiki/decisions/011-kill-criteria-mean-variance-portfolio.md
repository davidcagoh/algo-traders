# Decision 011: Kill Criteria - Mean-Variance Portfolio

Date: 2026-06-02

## Scope

First portfolio-construction baseline on the refreshed Hyperliquid universe:

`BTC, HYPE, PAXG, TRX, WLFI, VVV, TON, ZRO, XPL`

This decision is pre-registered before the first portfolio backtest.

## Implementation

- Data: Hyperliquid futures `1h` OHLCV, converted to daily close-to-close returns.
- Window: common current window from refreshed local data.
- Rebalance: weekly.
- Fees: taker turnover cost `0.00035 * turnover`.
- Portfolio: long-only shrunk mean-variance with cash allowed.
- Baselines: BTC buy-and-hold, equal weight, inverse volatility, minimum variance.
- Expected return estimate: `0.1 * rolling_mean_return`.
- Covariance estimate: Ledoit-Wolf shrinkage.
- Constraints:
  - `0 <= weight <= 0.20`
  - `sum(weights) <= 1.0`
  - unallocated capital is cash at zero return.

## Success Criteria

Treat the mean-variance portfolio as useful only if it beats equal weight on:

- Sharpe
- Calmar
- max drawdown

and does not rely on pathological concentration:

- average exposure >= 50%
- average effective assets >= 4
- average turnover per rebalance <= 0.75

## Kill Criteria

Kill or demote the approach if any hard condition holds:

- Sharpe <= equal weight Sharpe
- Calmar <= equal weight Calmar
- MDD worse than equal weight
- average effective assets < 3
- average turnover per rebalance > 1.25

## Notes

This is a baseline allocator, not a paper-trade candidate. The return estimate is deliberately crude and should be replaced by signal-based expected returns if the baseline is promising.
