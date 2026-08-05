# Crypto Carry

**Authors:** Maik Schmeling, Andreas Schrimpf, Karamfil Todorov (BIS / Cass Business School)
**Venue/Source:** Management Science (2026); also BIS Working Paper 1087
**arXiv/DOI:** 10.1287/mnsc.2024.05069
**Date:** 2026 (journal); BIS WP circulated 2022–2023

---

## Core Claim
Crypto carry (long spot + short perpetual on Binance BTC) generated annualised Sharpe 6.45 over August 2020 – May 2025, driven almost entirely by funding payments rather than spot-futures price convergence. The premium has sharply degraded: Sharpe fell to 4.06 in 2024 and turned negative in 2025 as institutional arbitrageurs crowded the trade.

---

## Method
Long spot + short perpetual carry strategy on Binance BTC perpetuals, August 2020 – May 2025. Carry defined per the Koijen et al. (2018) cost-of-carry framework. Period-by-period decomposition separates the funding rate contribution from spot-futures price convergence. Comparison against carry premia in equity, FX, and commodity markets.

---

## Results
| Sub-period | Sharpe |
|---|---|
| Full sample (Aug 2020 – May 2025) | 6.45 |
| 2024 only | 4.06 |
| 2025 | negative |

- Mean annual funding return ≈ 8% p.a. with volatility ≈ 0.8% — extremely high Sharpe when measured as an isolated carry pocket.
- Carry peak reaches ~60% annualised during the 2021 bull run.
- No Calmar or MDD reported; carry is near-flat-market by construction (delta-hedged).
- CEX (Binance) focus; DEX carry (Hyperliquid, Drift) is not studied.

---

## Relevance to this project
**Explains C1's empirical kill and confirms the strategy direction.**

Our `FundingCarry` (C1) strategy on the Binance 5.5y common window returned Calmar 1.93 with MDD 15.65% — real edge but killed by drawdown. This paper shows *why* the edge degraded: the window 2020-09 → 2026-05 spans the exact transition Schmeling et al. document, from the high-carry era (2020-2023, Sharpe 6.45) to the crowded/negative era (2025). A strategy that was profitable in years 1-3 of the window dragged MDD in years 4-5.

**Two direct implications for the P1 pipeline:**

1. **Conditional entry is mandatory.** The carry premium is regime-dependent with a multi-year half-life. A static threshold gate won't be sufficient — the gate threshold itself needs to adapt as the carry era evolves. DAR forecasting (Inan 2025, SSRN 5576424) + OU z-score entry (Le 2026, arXiv:2605.06405) together provide a forward-looking conditional filter rather than a static rate floor.

2. **DEX venue preference is validated by exclusion.** Schmeling et al. study only CEX (Binance). The Zhivkov 2025 paper (`dex-carry-funding-rate-arbitrage-2025.md`) found DEX (Drift) Sharpe 23.55 vs CEX −7.34 over the same period. The combination: CEX carry is dying due to crowding; DEX carry (Hyperliquid) retains premium because CEX-focused arbitrageurs haven't fully bridged the gap. Target Hyperliquid perps, not Binance, for any carry implementation.

No Freqtrade code changes required — use the existing C1 skeleton but add the conditional gates from H11 (OU z-score entry) and H12 (log-basis gate instead of raw rate level).

**Addresses priority:** P1 — documents the regime change in CEX carry profitability (Sharpe 6.45 → negative in 5 years); directly cross-validates our empirical C1 kill finding and confirms that conditional/gated carry on DEX is the correct strategy direction. Note: this paper itself is naive always-on CEX carry; the value is in the regime decomposition, not the strategy.

---

## Concepts
→ [[funding-rate]] | [[carry-strategy]] | [[regime-change]] | [[perpetual-futures]] | [[cost-of-carry]] | [[CEX-vs-DEX]]
