# Temporal Dynamics of Market Microstructure in Cryptocurrency Perpetual Futures: Econometric Evidence from Centralized and Decentralized Exchanges

**Authors:** P. Zhivkov, V. Todorov, S. Georgiev
**Venue/Source:** Journal of Risk and Financial Management (JRFM), Vol. 14(5):103 (MDPI)
**arXiv/DOI:** https://doi.org/10.3390/jrfm14050103
**Date:** April 23, 2026

---

## Core Claim
The two-tiered CEX/DEX structure in crypto perpetual funding rates is temporally unstable — the integration gap fluctuates continuously (−0.041 to 0.222 across rolling windows) with statistically significant intraday and day-of-week patterns, but no discrete regime shifts. CEX-to-DEX Granger causality is confirmed at hourly resolution; the specific price-discovery leader is not solely determined by exchange size.

---

## Method
Dataset: 9.1 million hourly funding rate observations from 26 exchanges (11 CEX, 15 DEX), covering 812 symbols over November 14, 2025 – January 13, 2026 (the companion paper by Zhivkov 2026a, already indexed as `two-tiered-funding-rate-markets-2026.md`, used a static 8-day snapshot; this paper adds temporal dynamics via 53 overlapping 7-day rolling windows).

Econometric pipeline:
- Rolling GARCH(1,1) to track time-varying volatility persistence
- Bai–Perron structural break detection + CUSUM stability testing for discrete shifts
- Bivariate VAR Granger causality tests (hourly, rolling)
- Integration gap = mean(CEX-CEX correlation) − mean(CEX-DEX correlation) across rolling windows

---

## Results
- **Integration gap**: −0.041 to 0.222 (persistent but highly variable; DEX fragmentation is not a constant disadvantage — windows exist where CEX-DEX alignment nearly matches within-CEX alignment).
- **Structural breaks**: Bai–Perron tests detect **no discrete regime shifts** at conventional significance. The market evolves via gradual drift.
- **Intraday + day-of-week effects**: Funding rate spreads exhibit statistically significant periodicity tied to the 8-hour settlement mechanism. Spreads are narrowest at settlement times and peak mid-cycle (around 4h post-settlement).
- **Granger causality**: CEX→DEX direction confirmed. Crucially, the price-discovery leader varies across windows and is **not solely the largest exchange** — implying that Binance dominance is not permanent and smaller CEX (or even specific DEX) can briefly lead.

---

## Relevance to this project
This paper directly extends the companion Zhivkov 2026a (already indexed) by adding temporal resolution. For our carry strategies:

1. **H6 confirmed with timing details**: CEX→DEX Granger causality is confirmed at hourly frequency. More precisely: spreads peak ~4h after settlement and narrow into settlement, which maps directly to our 4h candle structure. Entry at the `3h-post-settlement` bar is likely the widest-spread moment.

2. **Carry timing is intraday, not regime-dependent**: No discrete regime shifts means the carry gate should not be a regime-switching model — an EWMA threshold (smoothed over 8h rolling) is the right carry-gate tool, not a separate HMM for funding state.

3. **DEX fragmentation is variable**: In some windows the gap nearly closes. This means the CEX→Hyperliquid lead may not always be exploitable at 1h; check current integration gap before trade entry.

```python
# In carry strategy: time entries relative to settlement clock
# Binance funding settles at 00:00 / 08:00 / 16:00 UTC
# Enter at ~04:00 / 12:00 / 20:00 (midpoint of 8h cycle, widest spread period)
settlement_hours = {0, 8, 16}
current_hour = pd.Timestamp.now().hour
hours_since_settlement = min((current_hour - h) % 8 for h in settlement_hours)
carry_entry_allowed = (hours_since_settlement >= 3)  # mid-cycle entry
```

**Addresses priority:** P1 (carry timing on DEX perps — confirms intraday settlement-driven pattern) and H6 (CEX→DEX lead-lag quantification at hourly resolution).

---

## Concepts
→ [[funding rate]] | [[CEX-DEX arbitrage]] | [[Granger causality]] | [[intraday seasonality]] | [[market integration]]
