# Decision 013: Kill Criteria - LSTM Twitter Sentiment

Date: 2026-07-04

## Scope

Daily crypto adaptation of the screenshot strategy:

- Price model: per-coin LSTM over trailing daily OHLCV windows predicts next-day return.
- Sentiment model: Santiment `sentiment_weighted_twitter_1d` per coin, smoothed with a 7-day moving average.
- Fusion score: `score = price_weight * predicted_return + sentiment_weight * sentiment_zscore`.
- Trading rule: long/short/flat each coin independently, then aggregate equal capital across active signals.

## Data Gate

Do not backtest a coin unless:

- local Hyperliquid `1h` OHLCV can produce at least 120 daily closes;
- Santiment has a ticker/slug mapping;
- daily Twitter sentiment coverage is at least 80% over the price/sentiment overlap;
- at least 60 out-of-sample prediction days remain after model warmup.

## Useful If

- LSTM+Twitter beats LSTM-only on Sharpe and Calmar for the MV universe aggregate;
- LSTM+Twitter has positive Calmar on at least 60% of individually tested coins;
- incremental fee-adjusted return exceeds +5 percentage points over LSTM-only on the aggregate;
- average active exposure is at least 25%.

## Kill If

- Twitter sentiment data fails the Data Gate for the MV universe;
- LSTM+Twitter Sharpe <= LSTM-only Sharpe on the MV universe aggregate;
- LSTM+Twitter Calmar <= 0 on the MV universe aggregate;
- LSTM+Twitter underperforms LSTM-only on more than 60% of tested lower-cap coins;
- average turnover exceeds 1.25 notional/day after signal smoothing.

## Notes

This is a research backtest, not a Freqtrade strategy. It omits slippage, borrow constraints, liquidation mechanics, and execution latency. Santiment free API access is delayed and subscription-limited; reruns may fail if entitlement changes.
