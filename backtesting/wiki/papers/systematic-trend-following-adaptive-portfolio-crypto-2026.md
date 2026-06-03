# Systematic Trend-Following with Adaptive Portfolio Construction: Enhancing Risk-Adjusted Alpha in Cryptocurrency Markets

**Authors:** Duc Bui Thanh Nguyen (Talyxion Research)
**Venue/Source:** arXiv q-fin.TR
**arXiv/DOI:** arXiv:2602.11708
**Date:** February 12, 2026

---

## Core Claim
A 6-hour trend-following framework (AdaptiveTrend) that pairs a volatility-regime-conditional trailing stop with monthly rolling Sharpe-ratio asset selection and an asymmetric 70/30 long-short capital allocation achieves Calmar 3.18 and Sharpe 2.41 on 150+ crypto pairs across a 36-month out-of-sample window (2022–2024), significantly outperforming equal-weight buy-and-hold and plain EMA trend benchmarks.

---

## Method
**Signal**: EMA crossover on 6-hour bars (exact windows not disclosed; calibrated per asset in-sample 2018–2021).

**Three key innovations beyond a plain EMA strategy:**

1. **Volatility-regime trailing stop**: intraday realized volatility is computed per bar, and the trailing stop percentage is scaled inversely — tighter (≈1.5%) in the top-30% volatility regime, looser (≈3.0%) in the bottom-70%. This prevents premature exits during routine noise while cutting losses faster in elevated-volatility conditions.

2. **Rolling Sharpe asset selection**: at month-end, assets are ranked by 30-day rolling Sharpe and only the top tercile (roughly 50 pairs from 150+) are held. Market-cap-aware filter additionally excludes micro-cap pairs in the bottom 10% by liquidity.

3. **Asymmetric 70/30 long-short**: 70% of capital is allocated to longs, 30% to shorts. Motivated by the empirical positive drift of crypto markets — full market-neutral sizing would leave return on the table in bull periods.

**Why 6h?** The paper explicitly notes that 6h aligns with the 4×-daily funding rate settlement cycle on perpetual swap markets, concentrating entries at periods of maximum funding accumulation and reducing funding drag on long positions.

**OOS window**: January 2022 – December 2024 (36 months, includes 2022 bear, 2023 recovery, 2024 bull).

---

## Results
| Metric | AdaptiveTrend | EW Buy-and-Hold | Plain EMA Benchmark |
|--------|:---:|:---:|:---:|
| Calmar | **3.18** | 0.62 | 1.14 |
| Sharpe | **2.41** | 0.58 | 1.03 |
| MDD | −12.7% | −52.4% | −31.8% |

Sample period: 2022–2024 OOS, 150+ crypto pairs (Binance spot + perps), 6h bars.

No per-asset breakdown provided in the abstract; aggregate portfolio metrics only.

---

## Relevance to this project
Our current strategy book (T3 = SmaRegime180, R∧T2 = HmmSmaSlopeV2) achieves Calmar 8.76 and 30.23 on the common window, but both are single-entry strategies without position-size scaling or regime-aware trailing stops. AdaptiveTrend offers two concrete improvements to trial:

1. **Volatility-regime trailing stop in Freqtrade** (`custom_stoploss`): our T3 slope-gate family uses a fixed stop; adding an ATR/realized-vol conditional stop could reduce MDD from 2.21% toward the AdaptiveTrend range without sacrificing Calmar. Particularly relevant because our worst sub-window (2022 bear) shows MDD 0.28% only because the slope gate stays flat — but in any period the strategy *does* trade, adding a vol-conditional stop is cheap insurance.

2. **6h vs 4h timing insight**: the paper's explanation for 6h (aligns with funding settlement) applies equally to our 4h strategies: our `SmaRegime180` and `HmmSmaSlopeV2` use 4h candles, which means we settle at 2/3 of the 8h funding cycle's midpoint — close but not optimally aligned. A 6h variant (or scheduling entries to avoid the 4h near-settlement period) is worth testing.

3. **Asset selection filter**: the rolling Sharpe–ranked top-tercile filter is a simple way to suppress underperforming coins in our 5-coin universe (BTC/ETH/SOL/AVAX/DOGE). If AVAX continues as the outlier it's been (negative in R∧C1ʳ), a rolling Sharpe filter would naturally down-weight or exclude it.

```python
# Freqtrade custom_stoploss() — volatility-regime trailing stop
def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
    dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
    if dataframe.empty:
        return self.stoploss
    last = dataframe.iloc[-1]
    # realized vol over last 24 bars (24 × 4h = 4 days)
    rv = dataframe['close'].pct_change().rolling(24).std().iloc[-1]
    rv_75th = dataframe['close'].pct_change().rolling(24).std().rolling(168).quantile(0.75).iloc[-1]
    high_vol = rv > rv_75th
    stop_pct = 0.015 if high_vol else 0.030
    return max(current_profit - stop_pct, -1)
```

**Addresses priority:** P2 (intraday crypto strategy with Calmar/Sharpe results at 6h frequency, plus regime-conditional position management).

---

## Concepts
→ [[trend following]] | [[trailing stop]] | [[volatility regime]] | [[asset selection]] | [[portfolio construction]] | [[funding rate alignment]]
