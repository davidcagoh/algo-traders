# HmmRegime4Rolling multi-asset — CEX bull-window validation — 2026-05-10

**Strategy file:** `user_data/strategies/HmmRegime4Rolling.py` (unchanged; no funding dependency)
**Data:** Binance USDT-margined perp, 4h, 6 pairs (BTC, ETH, SOL, DOGE, AVAX, ARB), 2022-11-01 → 2025-01-01 (warm-up 2 mo + 24 mo evaluation)
**Config:** `user_data/config_binance_multi.json`, `max_open_trades=6`, `--fee 0.00035`

---

## Thesis

Per `wiki/results/2026-05-10-hmm-regime-4-multi-asset.md`: the bear-window 7-majors HL run returned −5.62% with MDD 14.7% and was labelled "structurally bear-blind, not a paper-trade candidate." Bear-window CEX cross-cycle work (`2026-05-10-hmm-regime-4-rolling-cex-validation.md`) confirmed bear-blindness on BTC. This run isolates the bull side: how much *upside* does the bear-blind family actually capture, and does the multi-asset structure work when there *is* a bull regime to detect?

---

## Metrics

| Metric | Bull (this run) | Bear (2025-11→2026-05, 7 HL) |
|---|---:|---:|
| **Total return** | **+65.36%** | −5.62% |
| **Calmar (CT)** | **27.73** | — |
| **Sharpe (CT)** | 1.25 | — |
| **Sortino (CT)** | 5.70 | — |
| **SQN** | 2.38 | — |
| **Profit factor** | 1.60 | — |
| CAGR | 28.49% | — |
| MDD | **5.69%** | 14.7% |
| Win rate | 35.2% | — |
| Trade count | 477 | — |
| Best pair | SOL +18.02% (Win 38.7%) | — |
| Worst pair | ETH +3.18% (all positive) | — |
| Best trade | AVAX +123.69% | — |
| Worst trade | DOGE −11.12% | — |
| Max consecutive losses | 20 | — |
| Market change (basket) | +190.83% | — |

### Per-pair (this run)

| Pair | Trades | Tot % | Win % | MDD % |
|---|---:|---:|---:|---:|
| SOL/USDT:USDT | 75 | +18.02 | 38.7 | 3.70 |
| DOGE/USDT:USDT | 80 | +16.60 | 32.5 | 3.84 |
| BTC/USDT:USDT | 89 | +14.33 | 37.1 | 2.18 |
| AVAX/USDT:USDT | 84 | +7.45 | 33.3 | 6.50 |
| ARB/USDT:USDT | 67 | +5.78 | 38.8 | 5.68 |
| ETH/USDT:USDT | 82 | +3.18 | 31.7 | 3.14 |

---

## What worked

- **All 6 pairs positive.** Unlike FundingCarry (5/6) and HmmCarry (3/6 meaningful), the HMM-only signal generalises across the basket. No regime-specific or coin-specific blowups.
- **AVAX +123.69% best trade.** The HMM correctly held through an extended alt rally. Average winner-duration 7.4 days suggests the strategy captures sustained moves, not noise.
- **MDD 5.69% on +65% return is the best risk-adjusted profile of any bull-window run.** Calmar 27.73 dominates SmaRegime180 BTC-bull windows (Calmar 14–21) — but note this is across 6 coins with leverage of having multiple uncorrelated streams.
- **The bear-blindness is now visible as bull-asymmetry.** −5.62% in bear vs +65.36% in bull is the *largest* asymmetric payoff in the project. As a complement to a bear-aware strategy (e.g. SmaRegime180's slope gate), this is exactly the shape you'd want.

## What didn't

- **35.2% win rate is the lowest of the three bull runs.** The strategy makes money via average-winner-size, not win-rate. Max consecutive losses 20 — psychologically punishing for live trading.
- **6.50% MDD on AVAX** — single-asset drawdown is real even when the basket MDD stays at 5.69%. Per-coin risk caps may be required for live deployment.
- **The bear-window result still rules out single-strategy deployment.** This run only confirms the upside; the downside in bears is structurally negative because of "regime-4 bull state" mis-firing during slow-bleed bears (per the CEX cross-cycle card).

## Next test

1. **HMM × SmaRegime180 slope-gate filter.** Use HMM regime-4 as entry signal but require slope-180 > 0 to actually enter. This is the natural complement: HMM provides high-density bull entries, slope-gate suppresses bear false-positives. Predicted: bull return drops modestly (from +65% to ~+45%?), bear MDD collapses (from 14.7% to ~3%?).
2. **DSR gate.** 477 trades is plenty of N. Run before any leaderboard claim of dominance.
3. **Per-coin parameter sweep.** Even with all 6 pairs positive, return is concentrated (SOL+DOGE+BTC = +49%). A modest per-coin tuning may recover ETH and AVAX without losing the winners. Pareto-search candidate.

---

## Implication for `learnings.md`

Entry #3 ("First real-data Pareto datapoint … HMM family is downgraded; does not generalise across coins") needs major amendment. The 2026-05-10 bear-window multi-asset run showed −5.62% which led to the downgrade. The bull-window run here shows +65.36% on the same universe (less HYPE) with all-positive pairs and Calmar 27.73. **The HMM family is not "structurally weak" — it is structurally asymmetric.** Update the leaderboard verdict from "leaderboard-only diversity, no paper-trade" to "paper-trade candidate *conditional on a bear filter*."

The Pareto frame holds and strengthens: SmaRegime180 (bear-resilient, low-density) and HmmRegime4Rolling-multi (bull-amplifying, high-density) are now confirmed non-dominated across a much wider performance gap.

---

## Reproducibility

```shell
./freqtrade/.venv/bin/freqtrade backtesting \
  --userdir user_data -c user_data/config_binance_multi.json \
  --data-format-ohlcv feather -s HmmRegime4Rolling -i 4h \
  --fee 0.00035 --eps --max-open-trades 6 \
  --timerange 20221101-20250101 --export trades
```

Result archive: `user_data/backtest_results/hmm_multi_binance_bull_2023_2025.zip`

---

## Layer 5 — Tail / Path shape (added 2026-05-16)

Backfilled per decision 005 (`wiki/decisions/005-evaluation-and-diversity-plan.md`). Generated with `scripts/eval_layers.py`.


**Binance bull 2023-2025**

| Metric | Value | Reading |
|---|---:|---|
| Skew | +6.72 | right-tailed (rare big wins) |
| Excess kurtosis | +64.86 | fat-tailed (Sharpe overstates) |
| Tail ratio (\|P95\|/\|P5\|) | 1.44 | winners > losers in size |
| CVaR-5% (daily) | -0.97% | mean loss on worst 5% of days |
| Ulcer Index | 2.82 | path-aware DD (lower = better) |
| Martin ratio | 9.41 | CAGR per unit ulcer (higher = better) |
| Pain index | 2.15 | mean abs drawdown |

_N_obs (daily): 792_

