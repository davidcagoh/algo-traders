# Explainable Patterns in Cryptocurrency Microstructure

**Authors:** Bartosz Bieganowski, Robert Ślepaczuk
**Venue/Source:** arXiv q-fin.TR
**arXiv/DOI:** arXiv:2602.00776
**Date:** January 31, 2026

---

## Core Claim

Order flow imbalance (OFI) in Binance Futures perpetual contracts exhibits a **predominantly monotone relationship with short-term price changes, with concavity at extremes** — extreme imbalances do not produce proportionally larger price moves. This pattern is stable across five assets spanning an order of magnitude in market cap. A conservative taker-at-best backtest validates tradability; a flash-crash stress test shows asymmetric maker vs. taker performance that empirically confirms adverse selection theory.

---

## Method

Data: Binance Futures perpetual contract order books and trades at **1-second frequency**, January 2022 – October 2025 (3.75 years). Assets: BTC, LTC, ETC, ENJ, ROSE (selected to span market cap range).

Unified CatBoost pipeline with direction-aware GMADL loss (penalises prediction confidence in the wrong direction more severely than correct-direction confidence). SHAP values explain each feature's contribution, connecting machine learning predictions to classic microstructure theory. Time-series cross-validation (no leakage).

Three signal families examined:
- **OFI** (net buyer-initiated volume vs. seller-initiated): monotone with concavity above extreme quantiles
- **Spread** (bid-ask): attenuates predictive signal (wider spread → lower confidence → hold out)
- **VWAP-to-mid deviation**: asymmetric short-horizon mean-reversion (downward deviations revert faster than upward, consistent with inventory pressure followed by depth replenishment)

Backtests: (a) top-of-book taker (most conservative), (b) fixed-depth maker. Flash crash (date not specified, likely Oct 2024 or early 2025) treated as stress test.

---

## Results

- OFI: monotone predictive effect, concavity at extremes. No specific Sharpe/Calmar numbers in abstract (full paper required for backtest metrics).
- Spread: significant SHAP importance; wider spread consistently reduces predictive confidence.
- VWAP-to-mid: short-horizon mean-reversion validated in both taker and maker backtests.
- Flash crash: taker strategy suffers; maker strategy benefits — adverse selection is real and empirically confirmed.
- Cross-asset stability: SHAP rankings consistent across BTC, LTC, ETC, ENJ, ROSE despite very different liquidity.

---

## Relevance to this project

**Actionable idea 1 — OFI as 1h mean-reversion gate.** The monotone-with-concavity OFI finding has a direct 1h implementation: aggregate 1-second signed trades into 1h bars to produce an hourly net-buy-volume (NBV) series. Enter mean-reversion (short) when hourly NBV is in the 70th–90th percentile of its rolling distribution, but NOT above the 95th (concavity = extreme OFI is noisy). This addresses Priority 4 implementation gap (OFI as 1h signal in crypto perps). The key insight is to **exclude extreme OFI values** from entry — consistent with z-score spike exclusion in the carry OU strategy (H11).

**Actionable idea 2 — Spread filter for entries.** Wider spread = attenuated signal. Add Hyperliquid L2 spread (best ask − best bid) as a filter: skip any mean-reversion entry when spread > 1.5× rolling median. Reduces adverse selection during illiquid periods.

**Actionable idea 3 — VWAP-to-mid as asymmetric signal.** Downward VWAP deviations (price below VWAP) revert faster than upward deviations. At 1h: if VWAP(1h) < mid-bar price by > 0.1%, mean-reversion signal has higher confidence than the reverse direction.

**Translation caveat:** Paper operates at 1-second. Hourly aggregation reduces signal-to-noise ratio; whether OFI predictability survives 1h aggregation is an empirical question requiring validation (test: measure 1h return autocorrelation conditioned on hourly NBV percentile buckets on the Binance 5-coin Parquet data already on disk).

**Addresses priority:** P4 — OFI as mean-reversion signal in crypto perps. Provides the mechanism (monotone with concavity at extremes) and the implementation pattern for 1h aggregation.

---

## Concepts
→ [[order-flow-imbalance]] | [[SHAP-explainability]] | [[adverse-selection]] | [[mean-reversion-signal]] | [[spread-filter]] | [[VWAP-deviation]]
