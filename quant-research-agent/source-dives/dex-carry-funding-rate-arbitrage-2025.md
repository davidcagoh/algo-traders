# Exploring Risk and Return Profiles of Funding Rate Arbitrage on CEX and DEX

**Authors:** Not retrieved (ScienceDirect 403 on fetch; see DOI link)
**Venue/Source:** Blockchain: Research and Applications (Elsevier), ISSN 2096-7209
**arXiv/DOI:** https://www.sciencedirect.com/science/article/pii/S2096720925000818
**Date:** August 2025

---

## Core Claim
Delta-neutral funding-rate carry on decentralised perp venues (Drift, ApolloX) yields Sharpe ratios an order of magnitude higher than the same strategy on centralised exchanges (Binance, Bitmex), which post *negative* Sharpe over the same period. The divergence is explained by market maturity: less-arbitraged DEX venues retain larger, more persistent funding-rate premia.

---

## Method
60 arbitrage scenarios across BTC, ETH, XRP, BNB, SOL on two CEXs (Binance, Bitmex) and two DEXs (Drift, ApolloX). Each scenario is delta-neutral carry: short perp + long spot, collecting the funding payment when the funding rate is positive. Scenarios vary by asset, exchange, leverage level, and holding period. The benchmark is HODL (spot long only). Correlation between carry P&L and HODL is measured to assess diversification. Maximum drawdown and maximum gain are reported alongside Sharpe.

---

## Results
| Exchange | Sharpe | Notes |
|----------|-------:|-------|
| Drift (DEX) | 23.55 | |
| ApolloX (DEX) | 6.50 | |
| HODL benchmark | 2.89 | spot long |
| Binance (CEX) | -7.34 | |
| Bitmex (CEX) | -7.93 | |

- Maximum return: 115.9% over 6 months
- Maximum loss: 1.92%
- Funding rate carry shows *no correlation* with HODL — pure diversifier
- Leverage raises both gains and risk in a non-linear pattern
- DEX DEX strategies exhibit significantly lower volatility than CEX equivalents

Sample period: 2025 (exact dates not retrieved).

Calmar ratios not reported; Sharpe is the primary risk-adjusted metric.

---

## Relevance to this project
The high DEX Sharpe (23.55 on Drift) and near-zero max loss (1.92%) give strong empirical support to building a funding-rate carry strategy on Hyperliquid — another on-chain perp DEX with similar structural characteristics (limited arbitrageurs, protocol-set funding). The CEX negativity is explained by the bear market compressing or inverting funding rates on mature venues; DEX venues retained positive rates.

**Critical caveat:** These Sharpe ratios look anomalously high and likely reflect a sample period with unusually elevated DEX funding rates. Do not take 23.55 as a forward estimate. Instead use this as evidence that DEX carry *exists* and is *distinct* from CEX carry — direction confirmation for Priority 1.

**Actionable:**
1. Confirm Hyperliquid 8h funding rate history: look for episodes where funding exceeded the break-even threshold (~20–25 bps per 8h as estimated from Zhivkov 2026).
2. The zero-correlation-with-HODL result means a carry strategy can be layered on top of any directional strategy without adding spot exposure.
3. Leverage sensitivity: test unleveraged carry first; leverage the carry leg only after confirming positive expectancy.

Freqtrade sketch (simplified):
```python
# In populate_entry_trend — enter short when funding is positive and above threshold
if funding_rate > 0.0002:          # 0.02% per 8h ≈ break-even estimate
    dataframe.loc[..., 'enter_short'] = 1
# Exit when funding falls below zero or below cost floor
```

**Addresses priority:** Priority 1 — Funding-rate carry on DEX perps: cost-adjusted and conditional. Directly provides empirical return profile for DEX carry vs CEX carry, and shows the mechanism (less arbitrage = persistent premia on DEX).

---

## Concepts
→ [[funding-rate]] | [[carry-strategy]] | [[DEX-perp]] | [[delta-neutral]] | [[Drift]] | [[ApolloX]] | [[Binance]] | [[Sharpe]]
