# Predictability of Funding Rates

**Authors:** Emre Inan
**Venue/Source:** SSRN Working Paper
**arXiv/DOI:** https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5576424
**Date:** October 7, 2025

---

## Core Claim
Out-of-sample forecasts of the next-period funding rate on Bitcoin perpetual futures (Binance, Bybit) from Double Autoregressive (DAR) models beat the no-change benchmark on both MSFE and directional accuracy, but the predictability is time-varying — it is weakest in 2024–2025 as the carry trade became crowded.

---

## Method
One-step-ahead point forecasts from a family of DAR models (which jointly model the conditional mean and variance, avoiding the spurious-ARCH confound common in AR models on fat-tailed data). Predictability stability is measured via the Lyapunov exponent — a positive Lyapunov exponent indicates chaos / regime sensitivity, meaning the window over which forecasts are useful is bounded. The evaluation compares in-sample fit and out-of-sample MSFE against a no-change (random walk) benchmark.

---

## Results
- DAR forecasts improve upon the no-change model in both MSFE and directional accuracy across most subsamples.
- Lyapunov analysis reveals time-varying predictability: the funding rate process is more stable (and thus more forecastable) in earlier periods; in the 2024–2025 subperiod, predictability degrades as the basis trade attracted institutional capital.
- No Calmar/Sharpe/MDD strategy results are reported (this is a forecasting paper, not a backtest).
- Sample: Bitcoin perpetual futures on Binance and Bybit; exact date range not retrieved but overlaps 2021–2025.

---

## Relevance to this project
The DAR predictability result directly supports building a funding-rate carry signal: if the next funding rate is predictable even one step ahead, a long-when-funding-is-predicted-positive / flat strategy should improve on naive always-on carry. More practically, it tells us when NOT to trade: when the Lyapunov exponent is elevated (chaotic regime), the predicted direction is unreliable and transaction costs will eat carry.

Concrete Freqtrade sketch:
1. Add a `funding_rate` datasource (Hyperliquid API provides 1h snapshots).
2. Fit a DAR(1) online or on a rolling 500-candle window.
3. Enter long only when the DAR point forecast > threshold (e.g. 0.01% per 8h = 13% annualised).
4. Exit when forecasted rate flips negative.

The time-varying predictability result is also a warning: any live system must re-estimate the DAR rolling, not rely on a static fit.

**Addresses priority:** Priority 1 — Crypto perp-specific factors (funding rate carry signal).

---

## Concepts
→ [[funding-rate]] | [[carry-strategy]] | [[double-autoregressive-model]] | [[Lyapunov-exponent]] | [[perpetual-futures]]
