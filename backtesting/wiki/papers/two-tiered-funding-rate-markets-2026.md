# The Two-Tiered Structure of Cryptocurrency Funding Rate Markets

**Authors:** Petar Zhivkov
**Venue/Source:** Mathematics (MDPI), Vol. 14, No. 2, Article 346
**arXiv/DOI:** https://doi.org/10.3390/math14020346
**Date:** January 20, 2026

---

## Core Claim
Cryptocurrency funding rate markets exhibit a stable two-tiered structure: centralised exchanges (CEX) dominate price discovery with 61% higher market integration than decentralised exchanges (DEX), and all statistically significant information flow runs CEX→DEX with zero reverse causality. Stated arbitrage spreads of ≥20bps exist in 17% of observations but only ~40% of top opportunities are profitable after transaction costs and spread reversals.

---

## Method
- **Dataset:** 35.7 million 1-minute observations across 26 exchanges (11 CEX, 15 DEX), 749 symbols, 8 consecutive days.
- **Analysis tools:** Time-series econometrics, rolling correlation matrices, Granger causality tests (funding rate levels and first differences).
- **Profitability screen:** Top funding-rate arbitrage windows identified; net P&L computed after taker fees, gas costs (DEX), and empirical spread reversals (i.e. the spread often closes before the next funding settlement).

---

## Results
- CEX integration coefficient: 61% higher than DEX average.
- Granger causality: CEX→DEX in all significant cases; no DEX→CEX.
- Arbitrage spread ≥20bps: 17% of 1-min observations.
- Post-cost profitability of top opportunities: ~40%.
- Implication: **roughly 60% of apparent carry opportunities on DEX venues are illusory** once realistic costs are applied.

No Calmar/Sharpe reported (this is a market-structure paper, not a strategy backtest).

---

## Relevance to this project
This paper sets the execution budget for any funding-rate carry strategy on Hyperliquid (a DEX):

1. **Hyperliquid is a DEX.** The paper shows DEX venues lag CEX on price discovery. This means:
   - Funding rates on Hyperliquid are *set* partly in response to Binance/Bybit rates (the CEX leaders), with some latency.
   - We can potentially use CEX funding rate direction as a leading indicator for Hyperliquid funding rate.

2. **Only 40% of ≥20bps spreads survive costs.** Hyperliquid charges taker fees; any carry strategy must be gated on a higher funding-rate threshold than the naive "positive = collect" rule. A conservative threshold based on Hyperliquid's actual taker fee (~2–5bps per fill) + expected adverse price move on entry is needed.

3. **Freqtrade integration:** Hyperliquid's API provides current funding rate. Before entering a carry position, check that the funding rate exceeds a minimum threshold (e.g. 0.05% per 8h ≈ 22% annualised) to clear the 60%-failure rate documented here.

4. **Pairs with this paper:** Use Inan (2025) to *predict* whether the funding rate will stay high next period; use this paper to *filter out* entries where the stated rate is below a cost-adjusted threshold.

**Addresses priority:** Priority 1 (funding rate carry feasibility) and Priority 3 (backtest-realistic execution on perps — quantifying the cost drag that must be modelled).

---

## Concepts
→ [[funding-rate]] | [[CEX-DEX-arbitrage]] | [[market-microstructure]] | [[Granger-causality]] | [[perpetual-futures]] | [[execution-costs]]
