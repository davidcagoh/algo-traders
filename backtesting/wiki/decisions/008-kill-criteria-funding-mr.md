# Decision 008 — Pre-registered kill criteria: FundingExtremeMR

**Status:** active (pre-registered before B3 backtest)
**Date:** 2026-05-16
**Strategy:** `user_data/strategies/FundingExtremeMR.py`
**Family:** new — "F" (funding-based mean reversion)

---

## Strategy

Mean-reversion on funding-rate extremes — *counter-funding* position when funding z-score is far above its OU mean.

- Universe: 5-coin Binance perp (BTC/ETH/SOL/AVAX/DOGE) on 4h.
- For each coin, OU-calibrate the funding series (per-coin, walk-forward weekly on prior 60d).
- Compute funding z-score against the rolling OU mean (90d window).
- Entry: when |z| > 2.0, take a *counter-funding* position — short if funding > 0 (longs paying), long if funding < 0 (shorts paying).
- Exit: time-stop at 3 bars (12h at 4h), OR z crosses zero, OR stop at |z| > 4.0.

Hypothesis: funding extremes are mean-reverting on a ~8h half-life per Le 2026 (arXiv 2605.06405). The strategy aims to harvest the spike — taking the opposite side of crowded carry positioning.

---

## Pre-registered kill criteria (binding)

| Code | Criterion | Threshold | Action |
|---|---|---:|---|
| **K1-fmr** | Standalone MDD on common-window backtest | > 5% | Hard kill (this is supposed to be a tight, sharp signal; if MDD blows out, the half-life estimate or threshold is wrong) |
| **K2-fmr** | Half-life drift in OU calibration | > 24h (single bar at 4h) | Hard kill (the mean-reversion premise has broken) |
| **K3-fmr** | MDB-rp vs book {T3, R∧T2} | < 0 robust across all 3 schemes | Don't trade |
| **K4-fmr** | Win rate degradation under fees | post-fee win rate < 45% | Hard kill (the strategy needs structural >50% with sharp small wins; below 45% means edge is fee-eroded) |

---

## Why these specific thresholds

- **K1-fmr = 5%**: short-horizon mean-reversion has a different MDD shape than trend. A *tight* MR strategy shouldn't lose much because each trade is bounded by the half-life time-stop. If MDD > 5%, either the z-threshold is too aggressive, the half-life estimate is stale, or the underlying premise has eroded.
- **K2-fmr**: Le 2026 calibrates 8h half-life on Hyperliquid. We expect Binance similar. > 24h means the mean-reversion is happening on a horizon outside our 3-bar (12h) time stop — strategy is structurally mismatched.
- **K3-fmr**: book = {T3, R∧T2}. Funding MR is a different family entirely (mean reversion, not trend, not regime). If it can't add to the book, it doesn't have a place.
- **K4-fmr = 45% win rate**: this strategy lives on small frequent wins; <45% post-fee win rate means each win isn't covering its losses.

---

## Continuous shrinkage formula

```
size_pct = base_size × hl_factor × pf_factor × zscore_quality_factor
```

where:
- `hl_factor = clip(2.0 - rolling_30d_half_life/12.0, 0, 1)` — shrinks as half-life drifts above 12h
- `pf_factor = clip(rolling_180d_PF / 1.5, 0, 1)`
- `zscore_quality_factor = clip(rolling_30d_max(|z|)/4.0, 0, 1)` — shrinks when z-extremes are absent

---

## Status if K1-K4 are passed

If MDB-rp > 0.3 robust AND standalone Calmar > 3 → **★ paper-trade candidate**.
If MDB-rp > 0 robust AND standalone Calmar > 1.5 → **▲ frontier**.
