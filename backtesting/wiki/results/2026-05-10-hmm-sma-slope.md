# HmmSmaSlope — HMM × Sma-slope gate — 2026-05-10

**Strategy file:** `user_data/strategies/HmmSmaSlope.py`
**Data:** Binance USDT-margined perp 6-coin basket (bull) + Hyperliquid USDC 7-coin basket (bear)
**Config:** `user_data/config_binance_multi.json` (bull), `user_data/config_hl_multi.json` (bear)
**Fee:** `--fee 0.00035`

---

## Thesis

The 2026-05-10 multi-asset bull-window run showed `HmmRegime4Rolling-multi` is bull-amplifying (+65.36%, Calmar 27.73) but bear-blind (−5.62% / MDD 14.7%). `SmaRegime180`'s slope-gate is the opposite shape — flat through bears, modest in bulls. Hypothesis: gating HMM entries by `sma180_slope > 0` should suppress HMM's bear false-positives while preserving most of the bull capture.

If this works, the two-segment Pareto frontier (Sma left, HMM-multi right) collapses to a single dominant point.

---

## Metrics

### Bull window (Binance 6 coins, 2023-01 → 2025-01, 24mo)

| Metric | HmmSmaSlope | HmmRegime4Rolling-multi | Δ |
|---|---:|---:|---|
| **Total return** | **+50.47%** | +65.36% | −15pp |
| **Calmar (CT)** | 23.63 | 27.73 | −15% |
| **Sharpe (CT)** | 0.78 | 1.25 | −38% |
| **Sortino (CT)** | 4.02 | 5.70 | −30% |
| **SQN** | 2.00 | 2.38 | −16% |
| **Profit factor** | 1.77 | 1.60 | **+11%** |
| **MDD** | 5.15% | 5.69% | −10% |
| **Win rate** | 33.2% | 35.2% | −2pp |
| **Trades** | 259 | 477 | **−46%** |
| Best pair | DOGE +19.61% | SOL +18.02% | — |
| Worst pair | ETH −0.37% | ETH +3.18% | — |

### Bear window (Hyperliquid 7 coins, 2025-10-15 → 2026-05-09, ~7mo)

| Metric | HmmSmaSlope | HmmRegime4Rolling-multi |
|---|---:|---:|
| **Total return** | **−4.00%** | −5.62% |
| **MDD** | **8.65%** | 14.7% |
| **Trades** | 50 | (hundreds) |
| **Win rate** | 28.0% | — |
| Best trade | HYPE +17.66% | — |
| Worst trade | HYPE −7.39% | — |

---

## What worked

- **Bear MDD cut by 41%** (14.7% → 8.65%). The slope gate is doing exactly what it was designed to do.
- **Profit Factor improved** (1.60 → 1.77) despite halved trade count. The gate filters trades that are *worse than average*, raising the quality of the survivors. This is the structural argument for using regime filters at all.
- **Worst-pair loss tiny in bull window** (ETH −0.37%). Five of six pairs positive; only ETH-bull-trade selection underperforms, and barely.
- **Bear-trade count crashes from hundreds to 50.** The strategy genuinely stops trading in bears, which is what the kill-criteria framework was designed for.
- **AVAX best-trade +123.69% survives** — same massive winner as unfiltered HMM-multi. The gate doesn't filter out the high-conviction setups, just the marginal ones.

## What didn't

- **No frontier collapse.** Sma is still on the frontier (lower bull return, lower bear MDD); HMM-multi is still on the frontier (higher bull return, higher bear MDD). HmmSmaSlope sits *between* them as a third frontier point. Not a single-strategy dominator.
- **Still in kill-zone for bear MDD.** Decision 004 sets the SmaRegime180 kill rule at MDD > 5.5%; HmmSmaSlope's bear MDD 8.65% breaches that line. It's a better bull-side strategy than HMM-multi, but it's *not paper-trade-ready* under the existing kill criteria.
- **Bull return drops 15pp.** The cost of the gate is real — for a pure bull bet, unfiltered HMM-multi is still the right answer.
- **Sharpe (CT) drops 38%.** Trade-economic improvement is offset by the smoother equity curve having less return per unit risk. The closed-trades Sharpe is misleading for filtered strategies — daily-wallet Sharpe (1.30 vs 1.25 for unfiltered HMM-multi) is the honest read.

## Next test

1. **Slope-gate parameter sweep.** SMA period 180 + slope lookback 6 is the SmaRegime180 default. A weaker slope filter (e.g. SMA90 or shorter lookback) would let more HMM entries through — possibly recovering bull return without giving back the bear MDD reduction. Pareto-search candidate.
2. **DSR gate on the three frontier strategies.** With Sma, HMM-multi, and HmmSmaSlope now all on the frontier, deflated Sharpe is the right tiebreaker for "is the signal noise-distinguishable?"
3. **Position-size scaling instead of binary gate.** Per `decisions/004-kill-criteria-sma-regime-180.md`'s continuous-shrinkage formula, the right move may be to *shrink* size as slope weakens rather than skip entry entirely. Tests whether the gate's binary cliff is leaving signal on the table.

---

## Implication for the Pareto frame

The frontier has three points now, not two:

| Point | Bull return | Bear MDD | Trades / yr (bull) | Role |
|---|---:|---:|---:|---|
| **SmaRegime180** (BTC) | +20.0% | 1.74% | ~16 | Bear-resilient endpoint |
| **HmmSmaSlope** (6 coins) | +50.5% | 8.65% | ~130 | Middle frontier point |
| **HmmRegime4Rolling-multi** (6 coins) | +65.4% | 14.7% | ~239 | Bull-amplifying endpoint |

The chart now shows a kinked frontier rather than a single segment — Sma → HmmSmaSlope → HMM-multi. Picking a strategy is now a *three-way* tradeoff: capital preservation (Sma), capital growth with bear control (HmmSmaSlope), or pure bull capture (HMM-multi).

For paper-trade graduation under the current kill criteria (MDD > 5.5% = hard kill), only SmaRegime180 still qualifies. HmmSmaSlope is the strongest *candidate-with-modifications*: lower its bear MDD below 5.5% via a tighter slope gate or a continuous-shrinkage size rule, and it would dominate Sma on bull return while preserving the kill-rule compatibility.

---

## Reproducibility

```shell
# Bull window
./freqtrade/.venv/bin/freqtrade backtesting \
  --userdir user_data -c user_data/config_binance_multi.json \
  --data-format-ohlcv feather -s HmmSmaSlope -i 4h \
  --fee 0.00035 --eps --max-open-trades 6 \
  --timerange 20221101-20250101 --export trades

# Bear window
./freqtrade/.venv/bin/freqtrade backtesting \
  --userdir user_data -c user_data/config_hl_multi.json \
  --data-format-ohlcv feather -s HmmSmaSlope -i 4h \
  --fee 0.00035 --eps --max-open-trades 7 \
  --timerange 20251015-20260509 --export trades
```

Result archives: `user_data/backtest_results/hmm_sma_slope_binance_bull.json` and `…_hl_bear.json`.

---

## Layer 5 — Tail / Path shape (added 2026-05-16)

Backfilled per decision 005 (`wiki/decisions/005-evaluation-and-diversity-plan.md`). Generated with `scripts/eval_layers.py`.


**Binance bull**

| Metric | Value | Reading |
|---|---:|---|
| Skew | +9.36 | right-tailed (rare big wins) |
| Excess kurtosis | +111.53 | fat-tailed (Sharpe overstates) |
| Tail ratio (\|P95\|/\|P5\|) | 0.99 | balanced |
| CVaR-5% (daily) | -0.81% | mean loss on worst 5% of days |
| Ulcer Index | 2.79 | path-aware DD (lower = better) |
| Martin ratio | 7.44 | CAGR per unit ulcer (higher = better) |
| Pain index | 2.21 | mean abs drawdown |

_N_obs (daily): 792_


**Hyperliquid bear**

| Metric | Value | Reading |
|---|---:|---|
| Skew | +0.20 | near-symmetric |
| Excess kurtosis | +21.80 | fat-tailed (Sharpe overstates) |
| Tail ratio (\|P95\|/\|P5\|) | 0.00 | losers > winners in size |
| CVaR-5% (daily) | -0.84% | mean loss on worst 5% of days |
| Ulcer Index | 4.53 | path-aware DD (lower = better) |
| Martin ratio | -2.46 | CAGR per unit ulcer (higher = better) |
| Pain index | 3.38 | mean abs drawdown |

_N_obs (daily): 206_

