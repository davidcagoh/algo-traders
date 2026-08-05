# Anatomy of Cryptocurrency Perpetual Futures Returns

**Authors:** Yi Cao, Pengfei Luo, Yuhan Cheng, Yizhe Dong
**Venue/Source:** SSRN Working Paper (University of Edinburgh)
**arXiv/DOI:** SSRN 6365329
**Date:** March 7, 2026

---

## Core Claim

Cryptocurrency perpetual futures expected returns can be decomposed into three components via a cost-of-carry model: current log basis, misperception of forward-looking spot price, and expected futures-spot spread. Of 170 cross-sectional return predictors across basis, momentum, liquidity, size, and volatility categories, 63 yield statistically significant long-short portfolio total returns (price movement plus funding fee yield) at the 5% level.

---

## Method

Adapts the classical Cochrane-style cross-sectional asset pricing framework to crypto perps, accounting for the distinctive feature that total returns include funding-rate flows. Builds a cost-of-carry model tailored to digital assets (positive convenience yield, negligible off-chain storage costs). Log-linear approximation decomposes expected return. Each of 170 predictors is used to sort coins into long-short portfolios; statistical significance tested at 5%.

Predictor families:
- **Basis** — current log spread between perp price and spot
- **Momentum** — past price and funding-rate continuation signals
- **Liquidity** — bid-ask spread, order book depth
- **Size** — market cap, open interest
- **Volatility** — realised vol, funding-rate vol

---

## Results

63 out of 170 predictors statistically significant at 5% for total return (price change + funding). Basis predictors are among the strongest — the log basis alone is a significant predictor of next-period total returns. Momentum factors also survive. Liquidity factors (spreads, depth) show significance but with smaller effect sizes. No Calmar ratios are reported; the evaluation is long-short portfolio alpha (t-statistics).

Sample period and universe: multi-coin crypto perpetual futures (major CEX, likely Binance-equivalent); dates not specified in abstract but implied to cover at least 2020–2025.

---

## Relevance to this project

**Actionable idea 1 — Basis as carry entry signal.** The log basis (perp price − spot price, normalised) is among the strongest predictors. This is equivalent to a z-score of funding relative to OU mean. Confirms that threshold-gated carry (enter when basis is meaningfully positive, not when rate is barely non-zero) is directionally correct. Specific implementation: use log basis as the entry gate rather than raw funding rate; pair with OU z-score from Le 2026 (arXiv 2605.06405, half-life 8h).

**Actionable idea 2 — Momentum as carry continuation.** Momentum predictors surviving cross-sectional tests suggests that funding-rate direction persistence is real. Aligns with Inan 2025 (SSRN 5576424) DAR predictability. Validates using a momentum gate (funding rising vs. falling) to decide hold-vs-exit on an open carry position.

**Actionable idea 3 — Liquidity as carry risk filter.** Spread and depth predictors suggest high-spread / shallow-book environments predict lower carry returns. Actionable as a filter: if Hyperliquid L2 book shows wide spread → reduce carry size (links to H8 from wiki/learnings.md).

**Code sketch:**
```python
# Basis-gated carry entry in Freqtrade
log_basis = np.log(perp_price / spot_price)  # from dataframe
entry_signal = (log_basis > basis_z_threshold) & (funding_rate > min_funding)
```

**Addresses priority:** P1 — Identifies which carry signals actually predict future perp returns in cross-sectional tests. Confirms basis (log perp–spot spread) is a stronger gate than raw funding rate level.

---

## Concepts
→ [[cost-of-carry]] | [[log-basis]] | [[cross-sectional-predictors]] | [[funding-rate-carry]] | [[momentum-carry-gate]]
