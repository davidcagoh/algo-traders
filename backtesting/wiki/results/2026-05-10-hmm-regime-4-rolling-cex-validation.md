# HmmRegime4Rolling — CEX cross-cycle validation — 2026-05-10

**Strategy:** `user_data/strategies/HmmRegime4Rolling.py` (rolling-window refit, no look-ahead)
**Data:** Binance perp **BTC/USDT:USDT**, 4h, 2020-02-26 → 2026-05-10 (~6.2 years effective after rolling-window warm-up; full file is 2019-09 → 2026-05)
**Source:** Same Feather as `2026-05-10-sma-regime-180-cex-bull-validation.md`
**Fee:** `--fee 0.00035`

---

## Why this run

Per follow-up #1 of the SmaRegime180 CEX validation card. HmmRegime4Rolling's only existing evidence was a single Hyperliquid 2024-02 → 2026-04 window — same regime the rolling refit was tuned in. Without independent cycles, we couldn't tell whether HMM's weaker SQN (0.59 on Hyperliquid Rolling vs 1.02 for SmaRegime180) was structural or regime-specific.

Highest-information experiment: same window, same fee, same data as SmaRegime180. Either outcome reshapes the leaderboard.

---

## Headline — full window (2020-02-26 → 2026-05-10)

| Metric | HmmRegime4Rolling | SmaRegime180 (CEX) | Δ |
|---|---:|---:|---|
| **Calmar (CT)** | **3.87** | 7.23 | −47% |
| **SQN** | **1.80** | 1.73 | +4% |
| Profit factor | 1.47 | 2.85 | −48% |
| Sharpe (CT) | 0.25 | 0.13 | +92% |
| Sortino (CT) | 0.75 | n/a | — |
| MDD | 4.35% | 2.22% | +96% |
| Win rate | 39.7% | 21.7% | +83% |
| Trade count | 267 | 92 | +190% |
| Total return | +19.99% | +20.24% | flat |
| CAGR | +2.98% | +2.84% | flat |

**Reading.** Total return is essentially identical (+20%) over 6+ years. The two strategies arrive at the same destination via **structurally different paths**:

- **SmaRegime180:** rare big wins (best +64%), tiny losses, 22% win rate, 92 trades. Slope-gate keeps the strategy flat through bears — capital preservation by design.
- **HmmRegime4Rolling:** balanced wins/losses, 40% win rate, 267 trades. Trades *through* bears with regime-4 mis-identifications.

This is a clean Pareto datapoint: HMM dominates on **win rate, trade density, Sharpe, SQN**; Sma dominates on **Calmar, MDD, Profit Factor**. Neither is dominated on the full vector.

---

## Sub-window decomposition (matches SmaRegime180 windows)

| Window | Period | Trades | Calmar | SQN | PF | Return | MDD |
|---|---|---:|---:|---:|---:|---:|---:|
| **2020-21 bull** | 2020-01 → 2022-01 | 86 | 6.86 | 1.27 | 1.60 | +9.44% | 3.90% |
| **2022 bear** | 2022-01 → 2023-01 | 40 | **−3.73** | **−1.24** | 0.60 | **−2.87%** | 4.02% |
| **2023-24 bull** | 2023-01 → 2025-01 | 88 | 7.94 | 1.12 | 1.51 | +6.94% | 2.28% |
| **2025 bear** | 2025-01 → 2026-05 | 49 | **−1.56** | −0.36 | 0.84 | **−1.24%** | 3.09% |

### Side-by-side vs SmaRegime180

| Window | Sma Calmar | HMM Calmar | Sma MDD | HMM MDD | Sma Return | HMM Return |
|---|---:|---:|---:|---:|---:|---:|
| 2020-21 bull | **14.04** | 6.86 | 1.83% | 3.90% | +9.84% | +9.44% |
| 2022 bear | **−5.23** | **−3.73** | **0.28%** | 4.02% | **−0.28%** | **−2.87%** |
| 2023-24 bull | **21.13** | 7.94 | 1.14% | 2.28% | +9.21% | +6.94% |
| 2025 bear | **+3.59** | **−1.56** | 1.74% | 3.09% | **+1.61%** | **−1.24%** |

### Reading

1. **HMM does not correctly identify bears.** In 2022, Sma attempted only 6 trades (slope-gate blocked the rest); HMM attempted 40 and was net negative with PF 0.60. In 2025 the gap widens: Sma is the only one positive (+1.61% Calmar +3.59), HMM goes negative. The "regime-4 bull state" detection misfires *exactly* when capital preservation matters most.
2. **HMM is competitive but never dominant in bulls.** Calmar 6.86 / 7.94 in the two bulls vs Sma's 14.04 / 21.13. Same direction, half the risk-adjusted return.
3. **HMM's bear MDD is ~2× Sma's even when negative.** 4.02% vs 0.28% in 2022. The slope-gate is the structural advantage.
4. **2022 bear is the proof.** Both strategies post negative Calmar in 2022, but the difference in mechanism is decisive: Sma's −5.23 comes from 6 attempted trades and 0.28% drawdown (correctly flat); HMM's −3.73 comes from 40 trades and 4.02% drawdown (incorrectly active). Calmar is closer than the underlying behaviour.

---

## Effect on the framing

The user's pre-stated decision rule:

> If HMM Calmar matches its Hyperliquid 12.11, it climbs back onto the leaderboard with credibility. If it collapses, HMM family is structurally weak and we focus exclusively on the slope-gate family.

**Outcome: middle path.** Calmar 3.87 ≪ Hyperliquid 12.11 — the Hyperliquid number was inflated by the milder 2025 bear and likely by the train-test overlap. But it's not a full collapse: total return matches Sma, Sharpe is higher, and the strategy is genuinely Pareto-non-dominated against Sma on win-rate and trade-density axes.

**Updated read of the leaderboard:**
- **SmaRegime180** is the unambiguous bear-resilient strategy. Its slope-gate filter is the structural advantage and cross-cycle validation confirms it.
- **HmmRegime4Rolling** is a *complement* not a competitor. It would only earn a leaderboard slot inside a meta-allocator that specifically wants the higher-trade-density / higher-win-rate shape — and only with bear-detection bolted on (HMM alone is bear-blind).
- The conjunction experiment (HmmCarry, 2026-05-10) already confirmed naive intersection of these signal families fails. Building a meta-allocator over `[Sma, HMM, ...]` needs explicit per-regime weighting, not signal AND.

**Recommendation:** Keep HmmRegime4Rolling on the leaderboard for diversity, but with a Pareto-rank annotation showing it loses to Sma on Calmar/MDD/PF and wins only on win-rate/density/Sharpe. Promotion to paper-trade: **no** — bear behaviour is structurally weak. Sma stays the only paper-trade candidate.

---

## Open follow-ups

1. **Why does HMM mis-identify 2022/2025 bears?** Inspect the rolling refit's regime-state distribution per window. Hypothesis: the 4-state HMM collapses to "trending vs choppy" in bears rather than "bull vs bear", because 4h returns in a slow-bleed bear look like a low-vol regime not a bear regime. If true, **adding a return-sign feature** (rolling N-bar median return) would fix it cheaply. Worth one targeted backtest.
2. **HMM + Sma slope-gate as a filter (not conjunction).** Use HMM regime-4 as the *entry signal* but require Sma slope > 0 to actually enter. This is the opposite topology of HmmCarry (which intersected entries). Predicted result: HMM's higher win rate retained in bulls, HMM's bear false-positives suppressed by slope-gate.
3. **DSR gate.** With 267 trades over 6 years, HmmRegime4Rolling now has enough N for a meaningful Deflated Sharpe Ratio test. Run before any further claims.
4. **Update leaderboard image.** `wiki/assets/leaderboard.png` should now show HMM with cross-cycle data, not just Hyperliquid.

---

## Reproducibility

```shell
# Full window
./freqtrade/.venv/bin/freqtrade backtesting \
  --userdir user_data -c user_data/config_binance.json \
  --data-format-ohlcv feather \
  -s HmmRegime4Rolling -i 4h -p BTC/USDT:USDT \
  --fee 0.00035 --eps --max-open-trades 1 \
  --timerange 20190908-20260510 --export none

# Sub-windows: replace --timerange with each of:
#   20200101-20220101  (2020-21 bull)
#   20220101-20230101  (2022 bear)
#   20230101-20250101  (2023-24 bull)
#   20250101-20260510  (2025 bear)
```
