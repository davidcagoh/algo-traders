# HmmSmaSlopeV2 — continuous slope-strength sizing — 2026-05-10

**Strategy file:** `user_data/strategies/HmmSmaSlopeV2.py`
**Data:** Binance USDT-perp 6-coin (bull) + Hyperliquid USDC 7-coin (bear), 4h, fee 0.00035
**Configs:** `user_data/config_binance_multi.json`, `user_data/config_hl_multi.json`

---

## Thesis

V1 (HmmSmaSlope) used a binary slope gate (`sma180_slope > 0` blocks entry) and cost 15pp of bull return vs unfiltered HMM-multi. The card's next-test list flagged continuous position sizing per `decisions/004` as the natural successor: scale stake by slope strength rather than skip the trade.

Hypothesis: continuous sizing should recover most of the lost bull capture (no entries filtered) while still cutting bear bleed (small sizes when slope is weak/negative).

Implementation: `slope_pct = sma180_slope / sma180`; `size_factor = clip(slope_pct / 0.005, 0, 1)`. `custom_stake_amount` returns `proposed_stake × size_factor`. When `size_factor = 0`, freqtrade auto-skips the entry.

---

## Metrics

### Bull window (Binance 6 coins, 2023-01 → 2025-01)

| Metric | V2 (continuous) | V1 (binary) | HMM-multi (unfiltered) |
|---|---:|---:|---:|
| **Total return** | **+33.44%** | +50.47% | +65.36% |
| **Calmar (CT)** | 13.69 | 23.63 | 27.73 |
| **MDD** | 5.89% | 5.15% | 5.69% |
| **Win rate** | 33.1% | 33.2% | 35.2% |
| **Trades** | 254 | 259 | 477 |
| **Avg stake** | $720 | $1000 | $1000 |
| Best trade | AVAX +123.69% | AVAX +123.69% | AVAX +123.69% |

### Bear window (Hyperliquid 7 coins, 2025-10-15 → 2026-05-09)

| Metric | V2 | V1 | HMM-multi |
|---|---:|---:|---:|
| **Total return** | **−1.58%** | −4.00% | −5.62% |
| **MDD** | **4.44%** | 8.65% | 14.70% |
| **Trades** | 44 | 50 | (hundreds) |
| **Avg stake** | $55 | — | — |

### Per-pair bull window (V2)

| Pair | Trades | Tot % | Win % | MDD % |
|---|---:|---:|---:|---:|
| DOGE | 42 | +15.96 | 33.3 | 1.99 |
| SOL | 48 | +10.80 | 35.4 | 5.35 |
| BTC | 50 | +2.98 | 32.0 | 1.33 |
| ARB | 34 | +2.69 | 23.5 | 4.35 |
| AVAX | 41 | +0.57 | 36.6 | 6.24 |
| ETH | 39 | +0.44 | 35.9 | 2.24 |

---

## The decisive finding

**V2 is the first multi-coin strategy to land below the 5.5% bear-MDD kill criterion.** Bear MDD 4.44% vs Sma's 1.74% single-coin reference — close to the bear-resilient endpoint but on a 6-coin basket.

The trade-off is sharp: 17pp of bull return given up vs V1, 32pp vs unfiltered HMM-multi. In exchange, the strategy graduates to **paper-trade eligibility** under the existing kill rule.

## What worked

- **Bear MDD halved vs V1** (8.65% → 4.44%) and cut by 70% vs unfiltered HMM-multi (14.7%). Continuous sizing during marginal-slope entries is genuinely effective at limiting exposure during regime turns.
- **Best/worst trades identical to V1.** AVAX +123.69% best, DOGE −11.12% worst, same as both V1 and the unfiltered HMM-multi. The entry signal hasn't changed; only the sizing has.
- **Avg stake $720 (bull) vs $55 (bear).** The sizing mechanism behaves as designed — large positions when slope is strong, small positions when it's weak. In bears, the average position is 5.5% of base capital.
- **Crosses the kill threshold for live deployment.** This is the only multi-asset strategy in the project that currently passes K1 (MDD > 5.5% = hard kill).

## What didn't

- **Bull return cost is bigger than V1's, not smaller.** V1 took 259 full-size trades; V2 took 254 variable-size trades. Same entries, less capital per trade — strictly worse for bull capture. The continuous sizing penalised weak-positive-slope entries that were *still profitable in aggregate*. The slope-strength signal doesn't carry useful sizing information beyond its sign.
- **Calmar dropped to 13.69** from V1's 23.63. The continuous-shrinkage formula trades efficiency for safety; the efficiency loss is real.
- **Bull MDD slightly worse** (5.89% vs V1's 5.15%) — within noise but counterintuitive. Likely because reduced size lets losing trades run longer before triggering a meaningful equity dent.
- **V2 doesn't dominate V1.** Both sit on the Pareto frontier — V1 owns higher bull return / higher bear MDD; V2 owns lower bull return / lower bear MDD. Picking between them is a choice about whether you're paper-trade-bound.

## Next test

1. **Asymmetric sizing.** Current `clip(slope/0.005, 0, 1)` is linear. A convex curve (`slope_pct^0.5 / threshold^0.5`) would give weak-positive entries more size, recovering some bull return without giving back bear protection.
2. **Per-coin SLOPE_STRONG.** 0.005 (0.5% / 24h) is BTC-calibrated. Faster-moving coins (DOGE, SOL) probably have higher natural slope variance. Per-coin thresholds calibrated from rolling slope distribution might tune the sizing.
3. **Hybrid v3.** Take V1's entry-binary gate (recovers full size for clean entries) plus V2's continuous *reduction* for marginal cases. Roughly: full size if slope > strong_threshold, scaled size if slope > 0, no entry if slope ≤ 0. Best of both extremes if the slope-strength signal carries any real information.

---

## Implication for the Pareto frame

The frontier now has **four non-dominated points**:

| Point | Bull return | Bear MDD | Trades / yr | Kill rule (MDD ≤ 5.5%)? |
|---|---:|---:|---:|:---:|
| **SmaRegime180** (BTC) | +20.0% | 1.74% | 16 | ✓ |
| **HmmSmaSlopeV2** (6 coins) | +33.4% | 4.44% | 127 | ✓ |
| **HmmSmaSlope** (6 coins) | +50.5% | 8.65% | 130 | ✗ |
| **HmmRegime4Rolling-multi** (6 coins) | +65.4% | 14.70% | 239 | ✗ |

Only two of the four are paper-trade eligible under the existing kill rule. Of the two, **V2 is the only multi-coin option** — it captures 67% more bull return than Sma while staying under the kill threshold. This is the strongest multi-asset paper-trade candidate the project has produced.

The chart's narrative tightens: there is now a *kill-zone-respecting frontier segment* (Sma → V2) and a *yield-maximising frontier segment* (V1 → HMM-multi). Picking between them is no longer just "which regime" — it's also "do you want to trade live or just simulate."

---

## Reproducibility

```shell
# Bull
./freqtrade/.venv/bin/freqtrade backtesting \
  --userdir user_data -c user_data/config_binance_multi.json \
  --data-format-ohlcv feather -s HmmSmaSlopeV2 -i 4h \
  --fee 0.00035 --eps --max-open-trades 6 \
  --timerange 20221101-20250101 --export trades

# Bear
./freqtrade/.venv/bin/freqtrade backtesting \
  --userdir user_data -c user_data/config_hl_multi.json \
  --data-format-ohlcv feather -s HmmSmaSlopeV2 -i 4h \
  --fee 0.00035 --eps --max-open-trades 7 \
  --timerange 20251015-20260509 --export trades
```

Archives: `user_data/backtest_results/hmm_sma_slope_v2_binance_bull.zip`, `…_hl_bear.zip`.

---

## Layer 5 — Tail / Path shape (added 2026-05-16)

Backfilled per decision 005 (`wiki/decisions/005-evaluation-and-diversity-plan.md`). Generated with `scripts/eval_layers.py`.


**Binance bull**

| Metric | Value | Reading |
|---|---:|---|
| Skew | +9.71 | right-tailed (rare big wins) |
| Excess kurtosis | +130.78 | fat-tailed (Sharpe overstates) |
| Tail ratio (\|P95\|/\|P5\|) | 0.49 | losers > winners in size |
| CVaR-5% (daily) | -0.80% | mean loss on worst 5% of days |
| Ulcer Index | 2.59 | path-aware DD (lower = better) |
| Martin ratio | 5.49 | CAGR per unit ulcer (higher = better) |
| Pain index | 1.91 | mean abs drawdown |

_N_obs (daily): 792_


**Hyperliquid bear**

| Metric | Value | Reading |
|---|---:|---|
| Skew | +3.16 | right-tailed (rare big wins) |
| Excess kurtosis | +51.53 | fat-tailed (Sharpe overstates) |
| Tail ratio (\|P95\|/\|P5\|) | 0.00 | losers > winners in size |
| CVaR-5% (daily) | -0.48% | mean loss on worst 5% of days |
| Ulcer Index | 2.21 | path-aware DD (lower = better) |
| Martin ratio | -2.35 | CAGR per unit ulcer (higher = better) |
| Pain index | 1.60 | mean abs drawdown |

_N_obs (daily): 206_

