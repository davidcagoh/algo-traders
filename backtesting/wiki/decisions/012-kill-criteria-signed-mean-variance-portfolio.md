# Decision 012: Kill Criteria - Signed Mean-Variance Portfolio

Date: 2026-06-02

## Scope

Signed perp extension of Decision 011 on the 9-coin Hyperliquid universe.

## Implementation

- Data: daily close-to-close returns from `1h` OHLCV.
- Funding: daily sum of Hyperliquid funding rates.
- Signed return: `position * (price_return - funding_rate)`.
- Rebalance: weekly after a 60-day lookback.
- Fee: `0.00035 * turnover`.
- Constraints:
  - `-0.20 <= weight_i <= 0.20`
  - gross exposure target/limit `<= 1.0`
  - cash allowed for mean-variance

## Useful If

- Sharpe > equal-weight long Sharpe
- Calmar > equal-weight long Calmar
- MDD better than equal-weight long MDD
- average gross exposure >= 0.50
- average effective assets >= 4
- average turnover per rebalance <= 0.75

## Kill If

- Sharpe <= equal-weight long Sharpe
- Calmar <= equal-weight long Calmar
- MDD worse than equal-weight long
- average effective assets < 3
- average turnover per rebalance > 1.25

## Notes

This test permits shorts but does not model borrow constraints, liquidation mechanics, slippage, or margin interest.
