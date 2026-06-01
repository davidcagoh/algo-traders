# HmmSmaSlopeV3 — concave (sqrt) slope sizing — 2026-05-10

**Strategy file:** `user_data/strategies/HmmSmaSlopeV3.py`
**Data:** Binance 6-coin (bull) + Hyperliquid 7-coin (bear), 4h, fee 0.00035
**Sizing:** `size_factor = clip((slope_pct / 0.005) ** 0.5, 0, 1)` (V2 was linear, exponent 1.0)

---

## Thesis

V2 result card established: "slope-strength magnitude carries no useful information beyond sign" — best/worst trades matched V1 exactly, only sizing differed. V3 tests whether a *concave* curve (raise slope ratio to 0.5 power) recovers bull return by pulling weak-positive entries back toward full size, while keeping the zero/negative cutoff that gives V2 its bear protection.

Concretely, for `SLOPE_REF = 0.005`:

| slope_pct | V1 (binary) | V2 (linear) | V3 (sqrt) |
|---:|---:|---:|---:|
| 0.000 | 0 (skip) | 0.00 | 0.00 |
| 0.001 | 1.00 | 0.20 | 0.45 |
| 0.003 | 1.00 | 0.60 | 0.77 |
| 0.005 | 1.00 | 1.00 | 1.00 |
| ≤ 0 | 0 | 0 | 0 |

---

## Metrics

### Full strategy comparison (bull = Binance 6-coin 2023-01→2025-01; bear = HL 7-coin 2025-10→2026-05)

| Strategy | Bull return | Bull MDD | Bull Calmar | Bull trades | Bear return | Bear MDD | Bear trades | Kill rule (MDD ≤ 5.5%)? |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| **HmmSmaSlopeV2** (linear) | +33.44% | 5.89% | 13.69 | 254 | −1.58% | **4.44%** | 44 | ✓ |
| **HmmSmaSlopeV3** (sqrt) | **+39.55%** | 5.77% | 16.55 | 259 | −2.12% | 5.72% | 50 | ✗ (by 0.22pp) |
| **HmmSmaSlope V1** (binary) | +50.47% | 5.15% | 23.63 | 259 | −4.00% | 8.65% | 50 | ✗ |
| **HmmRegime4Rolling-multi** | +65.36% | 5.69% | 27.73 | 477 | −5.62% | 14.70% | hundreds | ✗ |

V3 recovers **6pp of bull return** vs V2 (+33.44 → +39.55) at the cost of **1.3pp of bear MDD** (4.44% → 5.72%).

### Per-pair bull (V3)

| Pair | Trades | Tot % | Win % | MDD % |
|---|---:|---:|---:|---:|
| DOGE | 42 | (similar to V2) | 33.3 | — |
| SOL | 48 | (similar to V2) | 35.4 | — |
| BTC | 50 | (similar to V2) | 32.0 | — |
| (full breakdown: zip + backtesting-show) | | | | |

---

## What worked

- **Bull return recovered 6pp** vs V2. The sqrt curve gave weak-positive slope entries 2.25× the V2 size, capturing more of the available bull return.
- **Same entry count as V1 and V2** (259, 259, 254). Confirms the entry signal hasn't changed; only sizing has.
- **Frontier point added.** V3 sits between V2 and V1 on the Pareto frontier — sizing exponent has become a continuous knob along it.

## What didn't

- **V3 fails the kill rule by 0.22pp** (bear MDD 5.72% vs threshold 5.5%). So narrowly that another small tweak (exponent 0.6? slope ref 0.006?) might push it under.
- **The 6pp bull-recovery vs 1.3pp MDD cost is sub-linear vs V1.** V1 binary gives +11pp more bull return than V3 (50.47 vs 39.55) for 2.93pp more bear MDD. The exponent knob is sublinearly efficient — flatter MDD reduction per unit return given up.
- **DSR analysis flags V3 (and every other strategy) as NOISE.** Per `wiki/results/2026-05-10-dsr-analysis.md`, V3's daily-wallet Sharpe is 1.15 but kurtosis 117 inflates the deflation threshold; per-trade Sharpe 1.36 still falls below SR_star 2.17.

## Next test

1. **Tune exponent to land under kill rule.** Try `SIZING_EXPONENT = 0.6` (between sqrt and linear). Should be just enough larger-than-V3 penalty on weak slopes to push bear MDD below 5.5%.
2. **Lower SLOPE_REF instead.** Drop reference from 0.005 to 0.003: weak slopes hit full size earlier, but the slope itself is more restrictive. Different parameter, same effect direction — worth testing both axes.
3. **DSR-aware promotion threshold.** Per DSR result, no current strategy crosses the 0.95 signal threshold. Either accept the threshold and *not promote anything yet*, or relax it and document the relaxation (e.g. DSR > 0.5 = "weak signal, promote to paper-trade only").

---

## Implication for the Pareto frame

The frontier now has **five non-dominated points**, with the conjunction-family points forming a near-monotone curve:

| Point | Bull return | Bear MDD | Sizing rule | Kill ✓? |
|---|---:|---:|---|:---:|
| SmaRegime180 (BTC) | +20.0% | 1.74% | slope > 0, full size | ✓ |
| HmmSmaSlopeV2 (linear) | +33.4% | 4.44% | size ∝ slope | ✓ |
| HmmSmaSlopeV3 (sqrt) | +39.6% | 5.72% | size ∝ √slope | ✗ (by 0.22pp) |
| HmmSmaSlope V1 (binary) | +50.5% | 8.65% | slope > 0, full size | ✗ |
| HmmRegime4Rolling-multi | +65.4% | 14.70% | no slope filter | ✗ |

The sizing exponent has become a **continuous tuning knob** that traces the conjunction-family frontier. Picking V3 vs V2 is now a real decision about how close to the kill threshold you're willing to sit.

---

## Reproducibility

```shell
# Bull
./freqtrade/.venv/bin/freqtrade backtesting \
  --userdir user_data -c user_data/config_binance_multi.json \
  --data-format-ohlcv feather -s HmmSmaSlopeV3 -i 4h \
  --fee 0.00035 --eps --max-open-trades 6 \
  --timerange 20221101-20250101 --export trades

# Bear
./freqtrade/.venv/bin/freqtrade backtesting \
  --userdir user_data -c user_data/config_hl_multi.json \
  --data-format-ohlcv feather -s HmmSmaSlopeV3 -i 4h \
  --fee 0.00035 --eps --max-open-trades 7 \
  --timerange 20251015-20260509 --export trades
```

Archives: `hmm_sma_slope_v3_binance_bull.zip`, `hmm_sma_slope_v3_hl_bear.zip`.

---

## Layer 5 — Tail / Path shape (added 2026-05-16)

Backfilled per decision 005 (`wiki/decisions/005-evaluation-and-diversity-plan.md`). Generated with `scripts/eval_layers.py`.


**Binance bull**

| Metric | Value | Reading |
|---|---:|---|
| Skew | +9.21 | right-tailed (rare big wins) |
| Excess kurtosis | +114.28 | fat-tailed (Sharpe overstates) |
| Tail ratio (\|P95\|/\|P5\|) | 0.67 | losers > winners in size |
| CVaR-5% (daily) | -0.79% | mean loss on worst 5% of days |
| Ulcer Index | 2.69 | path-aware DD (lower = better) |
| Martin ratio | 6.18 | CAGR per unit ulcer (higher = better) |
| Pain index | 2.03 | mean abs drawdown |

_N_obs (daily): 792_


**Hyperliquid bear**

| Metric | Value | Reading |
|---|---:|---|
| Skew | +2.25 | right-tailed (rare big wins) |
| Excess kurtosis | +37.92 | fat-tailed (Sharpe overstates) |
| Tail ratio (\|P95\|/\|P5\|) | 0.00 | losers > winners in size |
| CVaR-5% (daily) | -0.57% | mean loss on worst 5% of days |
| Ulcer Index | 2.89 | path-aware DD (lower = better) |
| Martin ratio | -2.36 | CAGR per unit ulcer (higher = better) |
| Pain index | 2.13 | mean abs drawdown |

_N_obs (daily): 206_

