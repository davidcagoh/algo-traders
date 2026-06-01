# Who Sets the Range? Funding Mechanics and 4h Context in Crypto Markets

**Authors:** Habib Badawi, Mohamed Hani, Taufikin Taufikin
**Venue/Source:** arXiv (q-fin.TR)
**arXiv/DOI:** arXiv:2601.06084
**Date:** December 31, 2025

---

## Core Claim
The 4-hour timeframe is the critical structural unit for observing regime transitions in crypto perpetual futures. **Funding rate alignment with the 4h trend context predicts expansion; funding rate divergence from the 4h trend predicts compression and range-bound behaviour** — a mechanism driven by leveraged stop clustering and cascading liquidations at range boundaries.

---

## Method
Qualitative and empirical analysis of BTC perpetual futures on major venues (Binance/Bybit). Key constructs:
- **4h structural range:** defined by 4h candle highs/lows. A structural shift requires ≥2 consecutive 4h closes outside the established range.
- **Funding/context alignment:** funding is "aligned" when its sign agrees with the prevailing 4h trend direction; "divergent" when it opposes.
- **Boundary mechanics:** the paper maps how highly leveraged positions cluster at structural range boundaries, and how boundary tests trigger cascading liquidations that mechanically push price back toward equilibrium (mean-reversion signal) or break through into expansion (trend signal).
- Compares 1h and 4h timeframes directly, arguing 1h is too noisy to observe the equilibrium zone.

---

## Results
Empirical analysis on BTC perpetual futures. The paper is primarily a qualitative/structural framework, not a backtested strategy paper:
- Funding aligned with 4h context → directional expansion occurs in 70%+ of cases (approximate, from paper's case analysis)
- Funding divergent from 4h context → compression/range trading dominates, mean-reversion trades win
- Structural shifts (2+ consecutive 4h closes outside range) are confirmed signal of regime change
- No Calmar/Sharpe reported — the paper is a conceptual framework with case study support

**Universe:** BTC perpetual futures, major CEX venues. Period: 2023–2025 inferred from case studies.

---

## Relevance to this project
This paper intersects three open priorities:

**P1 (conditional carry threshold):** Funding divergence from 4h context = carry is operating against structural momentum → increased probability of adverse funding spike and subsequent rate compression. This is a "pause carry" signal. Implementation: before entering a funding-rate carry trade, check whether current funding direction agrees with the 4h SMA trend. Divergent funding = expect reversion → skip entry.

**P2 (HMM transition covariates):** The funding/4h-context alignment is an empirical proxy for the NH-HMM bull-state boundary. Rather than relying solely on returns + log-volume as HMM features (our current plan), adding a binary `funding_aligned` feature (1 if funding sign agrees with the 4h SMA slope) may sharpen state separation. This directly addresses the open search item: "feature selection for HMM transition covariates in crypto (volume, funding rate)."

**P4 (mean-reversion):** Funding divergence + range compression = mean-reversion trade setup. The proposed entry: when funding opposes the 4h trend and price touches the structural range boundary, fade the move toward mid-range with a 2–4 bar hold.

```python
# Sketch: funding/4h-context alignment check
# Requires: 4h SMA (or NH-HMM bull-state posterior), current funding rate sign
# In Freqtrade dataframe at 1h resolution:
#   funding_positive = funding_rate > 0  # long pays short (bearish pressure)
#   trend_bullish = close > sma_180  # 4h SMA proxy at 1h
#   funding_aligned = (funding_positive == trend_bullish)  # aligned if both agree
#   # Use as: enter carry when aligned=True; enter mean-reversion when aligned=False
# Funding rate available from Hyperliquid /info fundingHistory endpoint
```

**Addresses priorities:** P1 — carry timing overlay; P2 — HMM transition covariate; P4 — mean-reversion trigger

---

## Concepts
→ [[funding-rate]] | [[4h-context]] | [[range-bound]] | [[liquidation-cascade]] | [[regime-alignment]] | [[mean-reversion]]
