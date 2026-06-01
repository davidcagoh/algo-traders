# 2026-05-20 — Hedged mechanism HELD-OUT (BINDING)

**Track:** A
**Mechanism:** trend_vol low-vol + market-trend hedge (200d SMA on equal-weighted universe proxy)
**Gate:** [`decisions/004-track-a-hedged-mechanism.md`](../decisions/004-track-a-hedged-mechanism.md)
**Window:** 2023-01-01 → 2026-04-30 (pre-registered held-out, opened 2026-05-20)
**Status:** BINDING. No re-tuning permitted on this dataset.

Params: SGX `top_n=5`, weekly rebalance, `hedge_window=200`. IDX `top_n=8`, monthly rebalance, `hedge_window=200`. Both frozen from tuning.

## Result

### SGX held-out (binding)

| Variant | CAGR | Sharpe | Calmar | MDD | Ulcer | Kurt | N |
|---|---:|---:|---:|---:|---:|---:|---:|
| Buy & hold (beta) | +16.91% | 1.58 | 1.53 | 11.1% | 2.75 | +24.1 | 833 |
| Unhedged (informational) | +15.23% | 1.52 | 1.42 | 10.7% | 2.67 | +11.1 | 833 |
| **HEDGED (binding)** | **+9.83%** | **1.16** | **0.92** | **10.7%** | **3.38** | **+20.2** | 833 |

### IDX held-out (informational only — failed tuning gate)

| Variant | CAGR | Sharpe | Calmar | MDD | Ulcer | Kurt | N |
|---|---:|---:|---:|---:|---:|---:|---:|
| Buy & hold (beta) | +6.42% | 0.45 | 0.24 | 27.0% | 7.95 | +8.0 | 786 |
| Unhedged | +12.74% | 0.78 | 0.54 | 23.7% | 5.58 | +37.8 | 786 |
| Hedged | +0.24% | 0.07 | 0.02 | 14.5% | 8.11 | +6.6 | 786 |

## Gate 004 application — SGX hedged held-out

| Gate criterion | Threshold | SGX hedged | Verdict |
|---|---|---|---|
| L1 — CAGR | > 3% | +9.83% | ✓ |
| L2 — Sharpe | > 0.5 | 1.16 | ✓ |
| L2 — MDD | < 20% | 10.7% | ✓ |
| L2 — Calmar | > 0.5 | 0.92 | ✓ |
| L3 — N | ≥ 50 | 833 | ✓ |
| L4 — DSR binding | kurt < 5 AND N > 250 | kurt 20.2 ≥ 5 | NOT BINDING (humility check only) |
| L5 — Ulcer | < 12 | 3.38 | ✓ |

**SGX hedged passes gate 004 on the binding held-out window.** This is the first strategy in the project to clear a pre-registered held-out gate at any equity venue. **It graduates per the pre-reg protocol.**

## Honest reading — three things to keep in mind

### 1. The held-out window was kind to SGX

The 2023–2026 SGX regime was a strong bull market (buy & hold CAGR +16.91%, MDD 11.1%, Sharpe 1.58). Both unhedged trend_vol and buy-and-hold *also* pass the gate on this window without needing any hedge. The hedge's drawdown-reduction value was not stress-tested because there was no significant drawdown to reduce.

In fact, the hedged variant **underperforms both counterfactuals** on this window: 7pp less CAGR than buy-and-hold, 5pp less than unhedged, lower Sharpe than either. The hedge gave up bull-regime return without earning back the give-up in bear protection (because the bear didn't show up).

### 2. The gate passed because it was calibrated for a long-only equity strategy under any regime

Gate 004 was designed knowing long-only equity strategies have structural drawdown bounded by market beta. The thresholds (MDD < 20%, Calmar > 0.5) are achievable in bull regimes by buy-and-hold alone. The gate's job is to ensure the strategy *clears those bars*, not to prove the strategy is superior to alternatives.

A stricter gate — e.g. "hedged Sharpe > unhedged Sharpe on held-out" — would have failed. That stricter gate would have been the right one to pre-register if the question was "does the hedge improve a strategy you're already running?" Gate 004's question was narrower: "does the hedged mechanism clear a tradability bar on a market it wasn't tuned on?" Yes, it does.

### 3. IDX confirms what we suspected

IDX hedged on held-out: CAGR +0.24%, Sharpe 0.07, MDD 14.5%. The hedge cut drawdown to 14.5% (vs 23.7% unhedged) — it *worked* — but the SMA was so reactive on the IDX equal-weighted basket that the strategy was flat for most of the window, missing the +12.74% the unhedged ran up. IDX hedged was correctly shelved at the tuning gate per pre-reg; the held-out run confirms the shelving was the right call.

## What this licenses

Per pre-reg, **SGX hedged graduates to:**

1. **Pre-registration of kill criteria** (`decisions/005-kill-track-a-hedged.md`) before any further use. Pattern from `../../backtesting/wiki/decisions/004-kill-criteria-sma-regime-180.md` is portable: hard MDD threshold (e.g. 1.5× held-out MDD = 16%), continuous-shrinkage size factor on hedge SMA distance, six-straight-stops kill, rolling-365d-return floor.
2. **Paper-trade eligibility** — once the kill rule is written and a 30d daily-signal log validates the live wiring.
3. **A v2 experiment** that asks the *honest* question: does the hedge add value over the unhedged mechanism *across* regimes? This needs a second held-out window containing a bear regime, or a synthetic stress test on cross-cycle equity venues (e.g. KOSPI 2018–2020, FTSE 100 2015–2016).

It does **not** license:
- Any claim that the hedge is *necessary*.
- Re-tuning of the SGX base params on the held-out window.
- Skipping the kill-rule pre-reg.

## Cross-project promotion candidates

- **Held-out windows that don't span the regime the strategy is designed for produce passing-but-uninformative gates.** This applies to feishu (whose 2026-06 → 2026-12 held-out is calendar-driven, not regime-driven) and backtesting (whose dry-run windows are 30d, much shorter than a regime cycle). Worth promoting to `../learnings.md` as a methodology lesson: pre-register the *regime characteristics* the held-out window should contain, not just the dates.

## Files

- Gate: [`../decisions/004-track-a-hedged-mechanism.md`](../decisions/004-track-a-hedged-mechanism.md)
- Tuning result: [`2026-05-20-hedged-mechanism-tuning.md`](2026-05-20-hedged-mechanism-tuning.md)
- Strategy: [`../../tracks/sgx_idx_trend_vol/strategy.py`](../../tracks/sgx_idx_trend_vol/strategy.py)
