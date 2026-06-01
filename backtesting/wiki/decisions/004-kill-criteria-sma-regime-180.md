# 004 — Pre-registered kill criteria for SmaRegime180

**Status:** Active
**Date:** 2026-05-10
**Applies to:** `SmaRegime180` (4h SMA180 + slope gate, BTC/USDC:USDC)
**Related:** `learnings.md` open hypothesis #7 (regime carry-over inflation), `decisions/003-baseline-eval.md`, Davies & Ravagnani 2026 (continuous shrinkage framework)

---

## Why pre-register

`SmaRegime180` is the current leaderboard headline (Calmar 8.68 full-window, 6.59 bear sub-window, SQN 1.02). It is the next candidate for paper-trading. Without a written retirement rule, two failure modes are likely:
1. **Regime decay invisibility** — strategy degrades smoothly; we keep trading because no day looks like the day to stop.
2. **Backfit defence** — when results disappoint we rationalise rather than retire.

Pre-registration eliminates both. Criteria are written before paper-trading begins; deviation requires a new dated decision doc that overrides this one.

---

## Backtest reference baseline (Feb 2024 → Apr 2026, 4h)

| Metric | Value | Source |
|---|---:|---|
| Calmar (CT) — full window | 8.68 | `results/2026-04-30-sma-regime-180.md` |
| Calmar (CT) — bear sub-window | 6.59 | same |
| SQN | 1.02 | same |
| Profit factor | 2.72 | same |
| MDD | 1.74% | same |
| Win rate | 21.9% | same |
| Avg trade duration | 7d 3.75h | same |
| Trade count | 32 (~1/25d) | same |
| Net post-all-costs return | +5.18% (Calmar ~7.2) | cost modelling 2026-05-03 |

These numbers anchor the kill criteria. Each threshold is expressed as a multiple of, or ratio to, a backtest reference.

---

## Hard kill (binary stop, full liquidation)

Triggering any one of these halts the strategy immediately. No discretion.

| ID | Trigger | Rationale |
|----|---------|-----------|
| **K1** | Live MDD exceeds **5.5%** | ≈ 3× backtest MDD (1.74%). Backtests systematically understate DD; 3× is a conservative breach threshold. |
| **K2** | Six consecutive losing trades close at full stop (−10%) | Backtest worst trade was −10.08%, single occurrence. Six straight implies the slope-gate filter has stopped suppressing whipsaw. |
| **K3** | Rolling 365-day net return ≤ 0 for 30 consecutive days | Removes ambiguity around brief drawdowns; a year of zero alpha after costs is a structural break. |
| **K4** | Walk-forward backtest run quarterly produces Calmar < 2.0 on the most recent 365 days | Calmar 2.0 is the project's documented "minimum viable" threshold (`learnings.md` Scoring section). |

If K1–K4 trigger, strategy is **retired**, not paused. Re-listing requires a new strategy file (different name) with a new pre-registered specification.

---

## Continuous shrinkage (Davies–Ravagnani style)

Between healthy and dead, position size scales smoothly with observed evidence. Recompute the multiplier weekly from the trailing 180 calendar days:

```
size_multiplier = min(1.0,
                      pf_factor      ×
                      calmar_factor  ×
                      regime_factor)

pf_factor     = clip( (rolling_180d_PF - 1.0) / 1.0,             0.0, 1.0 )
calmar_factor = clip(  rolling_180d_Calmar / 4.0,                0.0, 1.0 )
regime_factor = clip( 1.0 - abs(log(bull_calmar / bear_calmar)) / log(3),
                                                                  0.25, 1.0)
```

Reading:
- **PF below 1.0** → zero size. PF at backtest level (2.72) → full size. PF at 2.0 → full size (clipped).
- **Rolling Calmar at 4.0 or above** → full size. At 2.0 → half size. Below zero → zero size.
- **Bull-vs-bear Calmar diverges >3×** → quarter size. Backtest had bull/bear ratio 8.68/6.59 = 1.32, well within bound. Triggers when realised regime sensitivity exceeds anything in the historical record.

The **realised position size** is `base_capital × size_multiplier`. Multiplier is reset only by a fresh 180-day window of new data, never by a single good week.

---

## Mandatory re-evaluation triggers (review, not auto-kill)

These force a written review within 5 trading days. Outcome is one of {continue at current size, force-shrink, hard-kill}. Avoiding the review is itself a violation.

| Trigger | Action |
|---------|--------|
| BTC 30d realised vol crosses **2× or 0.5×** backtest median | Re-fit slope-gate parameters on recent data; check if specification still discriminates regimes. |
| Hyperliquid taker fee schedule changes | Re-run cost model. Strategy survived 21.7% cost ratio; new ratio >30% triggers shrinkage. |
| Funding-rate regime shifts (rolling 90d median funding crosses zero) | Re-estimate funding drag. Backtest cost model assumed 18.3% drag from longs paying funding; sign flip changes the carry component materially. |
| Any of the leaderboard's other slope-gate SMA strategies (`SmaRegime720`, future variants) accumulates ≥30 live trades | Compare across the family. If `SmaRegime180` is the family's clear underperformer in live trading, force-review allocation. |

---

## What this document does NOT cover

- **Allocation across strategies.** This doc only governs `SmaRegime180`'s own multiplier. Cross-strategy capital allocation is a separate decision, to be written when ≥2 strategies are live.
- **Entry/exit logic changes.** Tweaking the strategy is *not* an alternative to kill criteria. If kill criteria fire, the strategy retires. A modified version is a new strategy with its own pre-registered criteria.
- **Discretionary pauses.** A "let me think about this" pause is forbidden. Either the rules say continue, shrink, or stop. Discretion enters only at the quarterly walk-forward review.

---

## Open data dependencies

Evaluating these criteria requires:
1. **Live equity curve** — forthcoming once paper trading starts.
2. **180-day walk-forward backtest** — needs CEX BTC 4h history (Binance perps go back to ~2019). Decision doc 005 (in progress) covers this.
3. **Quarterly walk-forward Calmar** — same data dependency as (2).

Until (2) and (3) are in place, K4 and the continuous-shrinkage formula cannot be evaluated. The hard kills (K1–K3) and the re-evaluation triggers can run on Hyperliquid-only data.

---

## Source-of-truth note

This document is the canonical retirement rule. If anything in `_index.md` or a results card conflicts with it, this doc wins until explicitly superseded by a new dated decision doc.
