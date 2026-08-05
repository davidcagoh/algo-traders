# Trends and Reversion in Financial Markets on Time Scales from Minutes to Decades

**Authors:** Sara A. Safari, Christof Schmidhuber
**Venue/Source:** arXiv (q-fin.TR / q-fin.ST)
**arXiv/DOI:** arXiv:2501.16772
**Date:** January 28, 2025 (revised May 30, 2025)

---

## Core Claim
Markets exhibit a **trending regime at intermediate time scales (hours to years)** and a **reverting regime at sub-hour and multi-decade scales**. This cross-scale structure is empirically stable across equities, rates, currencies, commodities, and — critically — crypto futures. Strong trends revert before reaching statistical significance; weak trends persist due to herding dynamics.

---

## Method
Cross-asset empirical study combining:
- 14 years of futures tick data (intraday, sub-hour to daily)
- Up to 330 years of monthly price series for long-horizon analysis

For each asset class and time scale, the authors measure autocorrelation sign and magnitude in returns. The transition boundary between momentum and mean-reversion is estimated by the horizon at which first-order return autocorrelation crosses zero. Crypto futures are included in the tick-data segment alongside traditional asset classes.

---

## Results
Key empirical findings:
- **Sub-hour:** mean-reverting (negative autocorrelation) — microstructure pressure dissipates
- **Hours to years:** trending (positive autocorrelation) — herding and momentum persist
- **Beyond ~5-10 years:** reverting again (multi-year valuation cycles)
- The transition from reversion to trending occurs somewhere in the 1–4 hour range across most asset classes
- Crypto futures follow the same qualitative pattern, though the transition boundary may sit at a somewhat shorter horizon due to higher turnover and retail participation
- Strong trends reverse before achieving statistical significance — a caution against chasing large recent moves

Calmar/Sharpe not directly reported; the output is autocorrelation profiles by time scale, not strategy backtests.

**Universe:** Multi-asset including crypto futures. Period: up to 14 years tick data.

---

## Relevance to this project
**Priority 4 (mean-reversion at 1h–4h):** This paper provides the empirical foundation for calibrating where to deploy mean-reversion strategies vs. trend strategies in our timeframe hierarchy.

Key implications:

1. **The 1h–4h range is the transition zone.** Sub-1h is reliably reverting; above 4h is reliably trending. Our current strategies (SmaRegime180 on 4h) sit in the trend regime — correctly so. A mean-reversion strategy should target 1h or shorter entries.

2. **Strong-move reversal principle:** "Strong trends revert before reaching statistical significance" is a direct signal design principle — a 2–3σ 1h move (relative to recent volatility) is more likely to revert within 1–4 bars than to continue. This is the actionable form of Priority 4's "intraday momentum reversal" direction.

3. **Strategy separation:** Run the 4h SMA/HMM trend strategy as the primary regime filter; run a separate 1h mean-reversion overlay that fades large intraday moves within a confirmed regime. The two time scales are structurally distinct.

```python
# Sketch: 1h mean-reversion entry condition
# Within a regime that SmaRegime180 labels as "flat/undefined":
#   z_score = (close - close.rolling(20).mean()) / close.rolling(20).std()
#   if z_score < -2.0:  # extreme downmove
#       enter long with tight stop (1-2 bars)
# Backtest target: Calmar > 2 on 1h BTC data, N > 20 trades
```

**Addresses priority:** P4 — Mean-reversion at 1h–4h timeframes in crypto majors

---

## Concepts
→ [[mean-reversion]] | [[momentum]] | [[time-scale]] | [[autocorrelation]] | [[regime-boundary]]
