# Strategy Taxonomy

**Purpose:** every strategy we've built, grouped by what it actually does, with a stable family code so the leaderboard is scannable. Sister doc to `strategy-archetypes.md` (that one is the canonical theory; this one is our concrete project state).

**Convention:** code names are read-only here — actual `.py` files keep their original names. Use the codes in conversation and in result-card cross-references.

**Status tags:**

| Tag | Meaning |
|---|---|
| ★ | Paper-trade candidate (passed cross-cycle validation under decisions/004) |
| ▲ | On Pareto frontier — kept for ensemble/research |
| ~ | Upper bound only (look-ahead or in-sample fit) — not tradeable |
| ✗ | Killed (hard-kill criterion breached or anti-complementary) |
| · | Baseline / placeholder |

---

## Three core families

A strategy is defined by **what generates the entry signal**. We have three signal sources in play:

| Code | Family | Signal source | Question it answers |
|---|---|---|---|
| **T** | Trend | Moving average + slope | "Is price trending up *with confirmation*?" |
| **R** | Regime (HMM) | Hidden Markov state posterior | "Is the latent market state bullish?" |
| **C** | Carry | Funding rate | "Are shorts paying longs (or vice versa)?" |

Conjunctions combine two families with `∧`: e.g. `R∧T` means "regime AND trend must both agree."

---

## T — Trend family

| Code | File | Mechanism | Status | Headline |
|---|---|---|---|---|
| **T0** | `LongOnlyStrategy.py` | SMA cross, no filter | · | Bear-only test: Calmar −4.55, killed by structure |
| **T1** | `TrendFilter200.py` | 1h SMA200 cross-up | ✗ | 200×1h = 8d window, every cross is a bear-trap. Mechanism noted in learnings.md |
| **T2** | `SmaRegime720.py` | 1h SMA720 + 24-bar slope gate | ▲ | Calmar 28.96 on N=6 — Calmar unreliable, kept as frontier point only |
| **T3** | `SmaRegime180.py` | 4h SMA180 + 6-bar slope gate | **★** | Cross-cycle Calmar 7.23 over 6.7y (Binance) — **paper-trade candidate** |

**Family verdict:** the slope gate is the active ingredient. Without it (T1), every regime filter gets whipsawed. With it (T2, T3), bull-window Calmar > 14, MDD bounded < 2.3%, 2022-style deep bears post negative Calmar but MDD stays at 0.28% (strategy correctly stays flat).

---

## R — Regime (HMM) family

| Code | File | Mechanism | Status | Headline |
|---|---|---|---|---|
| **R1** | `HmmRegime4.py` | 4-state GaussianHMM, fit on full window | ~ | Calmar 26.35 with look-ahead — upper bound only |
| **R2** | `HmmRegime4Rolling.py` | Same, walk-forward refit every 168 bars | ✗ | Hyperliquid bear: SQN 0.59, Calmar 12.11. **Binance common-window (2020-09 → 2026-05, A1.5): Calmar 0.47, MDD 7.65%, Ulcer 4.01, Pain 3.47 — chronic underwater, K1 kill doubly justified.** Win rate 35.6% stable but no tradeable edge. |
| **R2-multi** | `HmmRegime4Rolling.py` (5 assets) | Same, multi-asset portfolio | ✗ | **Binance 5-coin common (A1.5): Calmar 3.79, MDD 21.47%, Ulcer 10.25 — catastrophic on multi-asset.** Earlier 7-asset Hyperliquid bear was −5.62%. HMM does not scale across coins without slope-gate. |

**Family verdict:** HMM detects *something* (win rate stable at ~36% across windows) but the signal is regime-flattered on Hyperliquid 2025-26 bear and collapses out-of-sample. Look-ahead absorbed ~50% of the alpha in R1; rolling refit (R2) does not survive cross-cycle. **Family is killed pending per-coin tuning or covariate addition.**

---

## C — Carry family

| Code | File | Mechanism | Status | Headline |
|---|---|---|---|---|
| **C1** | `FundingCarry.py` | Long when funding-negative > threshold | ✗ | 7-asset bear: −30.16%, all stopped at −10%. Naive carry fails in bear. |

**Family verdict:** naive always-on carry is dead in bear regimes (CEX funding compresses to zero, DEX still has premia but our test was perp-USDC). Threshold-gated and reverse-sign variants remain open per `learnings.md` #4.

---

## R∧C — Regime × Carry conjunctions

| Code | File | Mechanism | Status | Headline |
|---|---|---|---|---|
| **R∧C1** | `HmmCarry.py` | HMM bull AND funding-negative | ✗ | 7-asset: −19.59%, **worse than HMM alone**. Signals anti-complementary: HMM reactive, funding forward-looking, intersection picks worst moments. Only HYPE/ETH tightened as expected. |

**Family verdict:** independence assumption failed empirically. Reverse-sign variant (positive funding as bull confirmation) is the open follow-up in `learnings.md`.

---

## R∧T — Regime × Trend conjunctions

| Code | File | Mechanism | Status | Headline |
|---|---|---|---|---|
| **R∧T1** | `HmmSmaSlope.py` | HMM bull AND SMA-slope positive | ▲ | 5-coin common window: Calmar 25.01, MDD 8.21% |
| **R∧T2** | `HmmSmaSlopeV2.py` | Tightened conjunction (V2) | **★?** | **5-coin common window: Calmar 30.23, SQN 2.73, CAGR +21.31%, MDD 6.05%** — breaches K1 by 0.55pp, awaiting A2 MDB to decide kill vs paper-trade |
| **R∧T3** | `HmmSmaSlopeV3.py` | V3 sizing experiment | ▲ | 5-coin common window: Calmar 27.28, MDD 6.91% |

**Family verdict (updated 2026-05-16):** R∧T variants are the new headline frontier — the multi-coin common-window run flipped the family from "DSR-flagged research" to "candidate book material." R∧T2 has 6× the CAGR of T3 (21.31% vs 3.42%) with marginally worse path-metrics. Three variants likely collapse to one effective strategy under correlation (testable in A2). Open question: K1's 5.5% MDD threshold was calibrated on bear-only Hyperliquid data; common-window MDD 6.05% may indicate the threshold is too tight for multi-asset, not that the strategy is broken. DSR still flags the variants — interpret with humility until MDB lands.

---

## Reading the family tree

```
                    ┌─── T (trend / slope)         ★ T3 paper-candidate
   Signal source ───┼─── R (HMM regime)            ✗ R2 killed cross-cycle
                    └─── C (funding carry)         ✗ C1 killed in bear

   Conjunctions:
     R ∧ T  ─── ▲ R∧T1/V2/V3 (Pareto frontier, DSR-flagged)
     R ∧ C  ─── ✗ R∧C1 (anti-complementary)
```

---

## When to update this doc

- New strategy file → add row to the appropriate family (or open a new family).
- Status change (★/▲/~/✗) → update the tag here and the headline note.
- Family-level conclusion changes → rewrite the verdict line.

Do *not* duplicate per-run findings here — those live in `results/<date>-<strategy>.md`. This doc is the family-level map; findings live one level down.
