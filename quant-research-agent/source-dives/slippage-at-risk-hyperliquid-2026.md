# Slippage-at-Risk (SaR): A Forward-Looking Liquidity Risk Framework for Perpetual Futures Exchanges

**Authors:** Otar Sepper
**Venue/Source:** arXiv (q-fin.RM / q-fin.TR)
**arXiv/DOI:** arXiv:2603.09164
**Date:** March 10, 2026

---

## Core Claim
Proposes SaR (Slippage-at-Risk), a forward-looking framework for estimating liquidation execution costs from the *current* order-book microstructure rather than historical return distributions. Applied empirically to Hyperliquid order-book data, including the October 10, 2025 liquidation cascade ($2.1 B of positions closed in 12 minutes, $304.5 M in insurance-fund deficits).

---

## Method
Three nested metrics derived from a cross-sectional sweep of the live order book:
- **SaR(α):** the α-quantile of slippage across all open positions if liquidated at current depth
- **ESaR(α):** expected slippage in the tail beyond SaR(α) (analogous to CVaR)
- **TSaR(α):** aggregate dollar-denominated tail slippage across the full open-interest pool

A **concentration adjustment** penalises liquidity that is nominally deep but dominated by a small number of market makers — fragile depth that evaporates under stress. The paper maps SaR to optimal exchange capital requirements and models how ADL (auto-deleveraging) cascades arise when TSaR exceeds reserve buffers.

---

## Results
Empirical evaluation uses Hyperliquid BTC-PERP order-book snapshots. Key findings:
- During the Oct 10, 2025 event: SaR at the 99th percentile implied slippage rates multiple times the nominal taker fee before the cascade began — the order book was warning of fragility hours before liquidations triggered.
- Concentration adjustment meaningfully increased SaR estimates during periods of thin maker participation (late-night UTC, weekends).
- Calmar/Sharpe not reported — this is a risk-measurement paper, not a trading strategy paper. The output is slippage quantiles and capital adequacy estimates.

**Universe:** Hyperliquid BTC perpetual futures. Period includes Oct 2025 liquidation cascade.

---

## Relevance to this project
**Priority 3 (slippage on Hyperliquid specifically):** This is the only known 2025-2026 paper that uses actual Hyperliquid order-book data to measure execution costs empirically. Direct applications:

1. **Validate Freqtrade zero-slippage assumption:** SaR provides a methodology to estimate realistic fill costs at different trade sizes. Our SmaRegime180 average position is small (~1 BTC unit), but knowing the 95th-percentile slippage at that depth gives a worst-case drag to add to cost modeling.

2. **Avoid trading during high-SaR regimes:** High SaR / high concentration = thin book → widen the entry/exit "no-trade" zone or require a larger slope-gate threshold before entering.

3. **Cascade risk for carry strategies:** The TSaR analysis shows that when OI concentration is high and funding is elevated, liquidation cascades are structurally more likely — exactly the conditions where a carry long is on. Adding a SaR proxy (e.g., bid-ask spread × depth imbalance) as a carry filter may improve Calmar by avoiding the adversely-selected funding drag we already documented (85% of drag falls on winning trades during bull runs).

```python
# Sketch: SaR proxy as carry entry filter
# At entry time, check order-book depth:
#   if (best_ask - best_bid) / mid > threshold_spread:
#       skip entry (fragile book)
#   if top_5_ask_depth < min_depth_usdc:
#       skip entry (concentrated liquidity)
# Requires LOB snapshot endpoint on Hyperliquid API: /info l2Book
```

**Addresses priority:** P3 — Backtest-realistic execution on perps (slippage sub-component)

---

## Concepts
→ [[slippage-at-risk]] | [[liquidation-cascade]] | [[order-book-depth]] | [[hyperliquid-execution]] | [[auto-deleveraging]]
