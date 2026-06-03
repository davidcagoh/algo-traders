# Order Flow and Cryptocurrency Returns

**Authors:** Alexia Anastasopoulos, Nikola Gradojevic, Fred Liu, Alex Maynard, Ilias Tsiakas
**Venue/Source:** Journal of Financial Markets (online first January 15, 2026)
**arXiv/DOI:** SSRN 5020002
**Date:** January 2026

---

## Core Claim
Lagged daily order flow — measured in 11 fiat currency denominations and normalised to remove price effects — is a statistically significant positive predictor of next-day cross-sectional crypto returns across 84 cryptocurrencies. A machine-learning sorted long-short portfolio achieves daily alpha ≈ 0.79% and annualised Sharpe of 3.63 out-of-sample.

---

## Method
Panel regression and stochastic gradient-boosted tree (ML) applied to daily FX-denomination-adjusted order flow for 84 cryptocurrencies, January 2018 – June 2022. Order flow is measured in each of 11 base currencies (USD, EUR, GBP, KRW, JPY, etc.) and normalised to isolate buying pressure independent of FX currency strength. Fama-MacBeth cross-sectional regressions confirm individual significance; ML model combines all 11 denominations. Portfolio construction: long top OFI-predicted decile, short bottom decile, daily rebalance.

---

## Results
- Daily alpha ≈ 0.79% (full ML model), annualised Sharpe 3.63.
- OOS R² = 0.39% — small but reliably positive across sub-periods.
- Robust to transaction cost adjustments on high-liquidity large-cap subsample.
- No Calmar or MDD reported; long-short portfolio (not directional long-only).
- Sample covers Jan 2018 – Jun 2022 (includes 2021 bull + 2022 deep bear).

---

## Relevance to this project
Two actionable angles:

**1. P4 — OFI frequency scaling (lower-bound evidence).** Daily OFI retains a Sharpe 3.63 signal. If signal decay from 1-second to daily preserves profitability, the 1h intermediate horizon — 24× fewer trades per day vs. daily = 24× lower fee drag — should be at least comparable or better before fees. This paper establishes a "daily works" anchor; H14's open question ("does 1h work?") is now bounded from below.

**2. X2 variant — OFI-ranked cross-sectional strategy.** X2 (`CrossSectionalMomentum`) currently uses price-momentum ranking across 5 coins. Replacing with OFI rank (which coin received the most normalised buying pressure last bar) is a direct implementation of this paper's cross-sectional sorting. An OHLCV-derived proxy — `nbv = (close - open) / (high - low + 1e-9) × volume` — is the data-available substitute for the FX-adjusted flow measure.

Freqtrade sketch for an OFI-ranked X2 variant:
```python
# For each 4h bar, compute NBV proxy for each coin:
nbv = (close - open) / (high - low + 1e-9) * volume
# Rank coins by rolling 3-bar NBV z-score; long top coin, flat others
nbv_z = (nbv.rolling(3).mean() - nbv.rolling(20).mean()) / nbv.rolling(20).std()
```
Compare Calmar vs. current X2 price-momentum version on the 5.5y Binance common window. If OFI-ranked X2 clears the 13.04% MDD barrier that killed the price-momentum version, it may enter the candidate book.

**Addresses priority:** P4 (daily cross-sectional OFI confirmed → 1h single-asset question still open) + X2 variant direction (OFI cross-sectional ranking as alternative signal source).

---

## Concepts
→ [[order-flow-imbalance]] | [[cross-sectional-momentum]] | [[fiat-denomination-adjustment]] | [[machine-learning-portfolio]] | [[daily-crypto-OFI]]
