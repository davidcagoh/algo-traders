# 2026-05-20 — HSI cross-cycle stress test (BINDING, gate 006)

**Track:** A
**Mechanism:** Frozen SGX-passing hedged trend_vol (`top_n=5`, weekly, `hedge_window=200`)
**Gate:** [`decisions/006-cross-cycle-stress-test.md`](../decisions/006-cross-cycle-stress-test.md)
**Window:** 2014-01-01 → 2024-12-31 on HSI (44 of 45 universe tickers resolved)
**Status:** BINDING. No re-tuning.

## Result

| Variant | CAGR | Sharpe | Calmar | MDD | Ulcer | Kurt | N |
|---|---:|---:|---:|---:|---:|---:|---:|
| HSI buy & hold (beta) | +8.50% | 0.51 | 0.25 | 34.6% | 12.42 | +3.4 | 2708 |
| HSI unhedged | +3.47% | 0.29 | 0.07 | 47.2% | 25.53 | +4.6 | 2708 |
| HSI HEDGED | +4.83% | 0.47 | 0.11 | 42.5% | 20.91 | +14.9 | 2708 |

## Gate 006 application

| Criterion | Threshold | Observed | Verdict |
|---|---|---|---|
| MDD reduction vs unhedged | ≥ 30% relative | 10.0% | **FAIL** |
| Hedged absolute MDD | < 25% | 42.5% | **FAIL** |
| Hedged Sharpe | ≥ 0.5 | 0.47 | **FAIL** (-0.03) |
| Hedge CAGR cost | ≤ 60% of unhedged | -39% (hedge *raises* CAGR) | PASS |
| Hedged kurt < unhedged kurt | reduction | 14.9 vs 4.6 (worse) | **FAIL** |

**4 of 5 criteria fail. The hedge does NOT vindicate cross-cycle.**

Per the pre-registered fail-mode interpretation in `decisions/006`:

> **Hedge doesn't contribute** (MDD reduction < 15%, or hedged MDD ≥ unhedged MDD): SGX result was regime-lucky. Park the hedge mechanism. Methodology lesson stands.

The 10% MDD reduction is below the 15% "doesn't contribute" threshold. **Verdict: PARK the hedged mechanism.** The SGX held-out pass was a regime-lucky outcome. Per pre-reg, FTSE 100 secondary run is *not triggered* because this is an outright fail, not an ambiguous result.

## What actually happened

Three things broke on HSI that didn't break on SGX:

1. **The unhedged base mechanism is bad on HSI.** Sharpe 0.29 vs buy-and-hold 0.51 — low-vol selection on HK names doesn't pick winning stocks the way it does on SGX. The mechanism is structurally venue-sensitive at the *selection* layer, not just the *parameter* layer.
2. **The 200d SMA is too slow for HSI's regime structure.** The 2021–2023 HK bear was a 2-year grinding decline; SMA eventually triggered "out" but had given back too much before responding. SGX's 2014–2022 didn't have a comparable slow bear, so the SMA was responsive enough.
3. **The hedge *raised* excess kurtosis** (4.6 → 14.9). The unhedged distribution was already mildly fat-tailed; the hedge's flat-then-back-in transitions created discrete return jumps that fattened the tails further. The hedge's design assumes it reduces tail risk; on HSI it produces a different kind of tail risk.

The buy-and-hold +8.50% / Sharpe 0.51 of equal-weighted HSI is what a Singapore retail investor with zero strategy would have made over the same window. The hedged mechanism produced 57% of that return at lower Sharpe, more drawdown, more kurtosis. **You'd have been better off doing nothing.**

## Methodology — this is the system working

This is exactly the kind of outcome the cross-cycle stress gate was designed to catch. Without `decisions/006`:

- SGX hedged passes gate 004 on held-out → graduates to paper-trade.
- Paper-trade encounters a real bear → loses money, doesn't recover, eventual realisation that the SGX held-out window was bull-regime.
- That realisation costs real money and 6+ months of wall-clock time.

With `decisions/006`:

- Cost: one extra backtest run on HSI.
- Outcome: SGX hedged correctly parked. Methodology learned the lesson at zero monetary cost.

The Davies quote in `wiki/learnings-archive.md` is operative here: *"quant funds survive in the long term because of fundamentally non-quantitative attributes of their managers; it is a very rare person indeed [who] combines the common sense to turn the model off when it is breaking down."* The cross-cycle gate is the mechanical version of common sense — it turns off the model *before* it breaks live.

## What's now confirmed

- The trend_vol_v4 mechanism does **not** generalise as a tradeable strategy to SGX, IDX, or HSI under retail cost assumptions and the layered eval methodology.
- The hedged variant produces a tuning-window pass on SGX and a held-out window pass on SGX, but the pass is regime-conditional and falsified by HSI cross-cycle stress.
- The 6-layer methodology + pre-registration discipline correctly distinguishes "passes a gate" from "is tradeable."

## What's now parked (with reasons)

| Mechanism | Status | Why parked |
|---|---|---|
| trend_vol_v4 unhedged on SGX | Parked | Fails gate 001 (Sharpe, Calmar, MDD) at any tested params. |
| trend_vol_v4 unhedged on IDX | Parked | Same as SGX, worse. |
| trend_vol_v4 hedged on SGX | Parked | Passes gates 001, 004 on SGX but fails gate 006 cross-cycle on HSI. |
| trend_vol_v4 hedged on IDX | Parked | Failed gate 004 at tuning. |
| trend_vol_v4 unhedged on HSI | Parked | Sharpe below buy-and-hold; mechanism's selection layer is venue-sensitive. |
| trend_vol_v4 hedged on HSI | Parked | Fails gate 006 outright. |

## Cross-project promotion candidates (for `../learnings.md`)

1. **Held-out windows that don't span the strategy's design regime produce passing-but-uninformative gates.** Confirmed by SGX gate-004 pass + HSI gate-006 fail. The pre-reg must specify the *regime characteristics* the held-out window should contain, not just dates.
2. **Mechanism transplants are venue-sensitive at the selection layer, not just the parameter layer.** The trend_vol mechanism's low-vol selection works on A-shares (feishu) and partially on SGX but not on HSI. Cross-cycle stress catches this where parameter tuning would not.
3. **Hedge layers can shift tail-risk shape rather than reduce tail risk.** HSI hedged had higher excess kurtosis than HSI unhedged, despite the hedge "successfully" cutting MDD by 10%. Tail-shape change must be measured separately from MDD; gate 006's "kurt reduction" sub-gate caught this where MDD-only gates would have missed it.

## Files

- Pre-reg gate: [`../decisions/006-cross-cycle-stress-test.md`](../decisions/006-cross-cycle-stress-test.md)
- Prior SGX held-out result: [`2026-05-20-hedged-mechanism-heldout-BINDING.md`](2026-05-20-hedged-mechanism-heldout-BINDING.md)
- Strategy: parked equity source (removed during cleanup)
- Universe (HSI added): parked equity source (removed during cleanup)
