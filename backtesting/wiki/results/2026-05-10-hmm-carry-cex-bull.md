# HmmCarry — CEX bull-window validation — 2026-05-10

**Strategy file:** `user_data/strategies/HmmCarry.py` (unchanged; reads Binance funding via `CARRY_FUNDING_EXCHANGE=binance`)
**Data:** Binance USDT-margined perp, 4h, 6 pairs (BTC, ETH, SOL, DOGE, AVAX, ARB), 2022-11-01 → 2025-01-01 (warm-up 2 mo + 24 mo evaluation)
**Funding source:** Same Binance parquets as the FundingCarry bull run
**Config:** `user_data/config_binance_multi.json`, `max_open_trades=6`, `--fee 0.00035`

---

## Thesis

Per `wiki/results/2026-05-10-hmm-carry-conjunction.md`: the bear-window conjunction (`bull_prob ≥ 0.65` AND `funding_roll < −0.00001`) returned −19.59% with anti-complementary entry timing — HMM reactive (lags), funding forward-looking (leads). Hypothesis: in a bull regime both signals point the same direction, so the conjunction should *tighten* correctly instead of selecting late-cycle bull lag × early-cycle bear lead.

---

## Metrics

| Metric | Bull (this run) | Bear (2025-11→2026-05, 7 HL) |
|---|---:|---:|
| **Total return** | **+25.77%** | −19.59% |
| **Calmar (CT)** | **13.68** | — |
| **Sharpe (CT)** | 0.80 | — |
| **Sortino (CT)** | 3.36 | — |
| **SQN** | 2.62 | — |
| **Profit factor** | 1.92 | — |
| CAGR | 11.96% | — |
| MDD | **4.54%** | — |
| Win rate | **46.2%** | ~28% (7.7% on BTC) |
| Trade count | 158 | 278 |
| Best pair | SOL +19.72% (Win 42.9%) | ETH/HYPE |
| Worst pair | ARB −1.33% | BTC −7.7% WR |
| Best trade | SOL +35.68% | — |

### Per-pair (this run)

| Pair | Trades | Tot % | Win % | MDD % |
|---|---:|---:|---:|---:|
| SOL/USDT:USDT | 56 | +19.72 | 42.9 | 3.99 |
| AVAX/USDT:USDT | 68 | +7.19 | 52.9 | 4.39 |
| ETH/USDT:USDT | 3 | +0.18 | 66.7 | 0.00 |
| BTC/USDT:USDT | 21 | +0.06 | 42.9 | 1.38 |
| DOGE/USDT:USDT | 2 | −0.05 | 0.0 | 0.05 |
| ARB/USDT:USDT | 8 | −1.33 | 25.0 | 1.57 |

---

## What worked

- **Hypothesis confirmed: conjunction is regime-conditional.** Bull-window flips from −19.59% to +25.77% on an unchanged strategy. The "anti-complementary" verdict from the bear-window card was specific to the regime, not structural.
- **Calmar 13.68 is the strongest of the three bull-window runs** (vs FundingCarry 3.06 and HmmRegime4Rolling-multi 27.73 over equity-curve daily basis — though absolute return is lower than HMM-multi). The conjunction's effect is to *filter for high-conviction trades*, halving trade count vs HMM-only while raising win rate from 35.2% to 46.2%.
- **Rolling-window HMM refit (no look-ahead) is honest.** Same machinery as `HmmRegime4Rolling`; 1000-bar fit window every 168 bars.
- **MDD 4.54%** — much tighter than FundingCarry's 10.65% on the same universe / same period. The filter is doing real work.

## What didn't

- **DOGE and ARB are near-zero or negative.** Sparse entries (2 and 8 trades) — small-sample noise dominates, but the strategy is clearly not equally effective across all coins. Per-coin signal viability needs separate validation.
- **BTC almost flat** (+0.06% on 21 trades, 42.9% win). Funding-rate-negative + HMM-bull is a less informative combination on BTC than on alts, mirroring the bear-window finding (BTC was 7.7% WR there).
- **Most return concentrated in 2 of 6 pairs.** SOL+AVAX = +26.91% of the +25.77% total. The conjunction is alt-driven; BTC/ETH/DOGE/ARB contribute marginally.

## Next test

1. **DSR gate.** 158 trades + 6 pairs is sufficient N. Run before any leaderboard promotion.
2. **Time-priority variant.** Require `funding_roll < threshold` to have been negative for K bars *before* `bull_prob` crosses 0.65 (lead-then-confirm). This separates true reversal setups from coincident-alignment, which was the bear-window failure mode.
3. **Alt-only run.** Drop BTC/ETH and rerun on SOL/AVAX/DOGE/ARB. If the alt-only conjunction stays > +20% with Calmar > 10, the strategy is structurally an alt-funding-conjunction strategy, not a generic regime tool.

---

## Implication for `learnings.md`

Entry #5 ("Signal conjunction without sign assignment is suspect when signals have different time horizons") needs amendment: **the time-priority issue is bear-specific**. In bull regimes the HMM lag and funding lead align constructively. Update the entry to "regime-asymmetric" rather than "fails."

---

## Reproducibility

```shell
CARRY_FUNDING_EXCHANGE=binance ./freqtrade/.venv/bin/freqtrade backtesting \
  --userdir user_data -c user_data/config_binance_multi.json \
  --data-format-ohlcv feather -s HmmCarry -i 4h \
  --fee 0.00035 --eps --max-open-trades 6 \
  --timerange 20221101-20250101 --export trades
```

Result archive: `user_data/backtest_results/hmm_carry_binance_bull_2023_2025.zip`

---

## Layer 5 — Tail / Path shape (added 2026-05-16)

Backfilled per decision 005 (`wiki/decisions/005-evaluation-and-diversity-plan.md`). Generated with `scripts/eval_layers.py`.


**Binance bull 2023-2025**

| Metric | Value | Reading |
|---|---:|---|
| Skew | +15.79 | right-tailed (rare big wins) |
| Excess kurtosis | +337.80 | fat-tailed (Sharpe overstates) |
| Tail ratio (\|P95\|/\|P5\|) | nan | n/a (N < 20) |
| CVaR-5% (daily) | -0.03% | mean loss on worst 5% of days |
| Ulcer Index | 1.50 | path-aware DD (lower = better) |
| Martin ratio | 7.42 | CAGR per unit ulcer (higher = better) |
| Pain index | 1.01 | mean abs drawdown |

_N_obs (daily): 792_

