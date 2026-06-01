# FundingCarry — CEX bull-window validation — 2026-05-10

**Strategy file:** `user_data/strategies/FundingCarry.py` (unchanged; reads Binance funding via `CARRY_FUNDING_EXCHANGE=binance`)
**Data:** Binance USDT-margined perp, 1h, 6 pairs (BTC, ETH, SOL, DOGE, AVAX, ARB), 2023-01-01 → 2025-01-01 (~24mo bull cycle)
**Funding source:** `scripts/download_binance_funding.py` — 6 parquets in `user_data/data/binance/funding/`, 8h cadence, 2,043–2,545 records per coin
**Config:** `user_data/config_binance_multi.json`, `max_open_trades=6`, `--fee 0.00035`

---

## Thesis

Per `wiki/results/2026-05-10-funding-carry.md` follow-up: the bear-window result (−30.16%, 10.6% win rate on 7 Hyperliquid majors) was hypothesised to be regime-specific, not a fundamental failure of the funding-rate-carry signal. This run tests the inverse — does the same unmodified strategy work in a sustained bull?

---

## Metrics

| Metric | Bull (this run) | Bear (2025-11→2026-05, 7 HL) |
|---|---:|---:|
| **Total return** | **+12.47%** | −30.16% |
| **Calmar (CT)** | **3.06** | −7.35 |
| **Sharpe (CT)** | 0.56 | — |
| **Sortino (CT)** | 0.93 | — |
| **SQN** | 1.34 | — |
| **Profit factor** | 1.31 | — |
| CAGR | 6.04% | — |
| MDD | **10.65%** | 42.14% |
| Win rate | **52.4%** | 10.6% |
| Trade count | 252 | 161 |
| Best pair | BTC +3.82% (Win 56.2%) | HYPE +5.04% |
| Worst pair | ARB −1.01% | (all losers) |
| Best trade | SOL +39.01% | — |
| Worst trade | SOL −10.08% (stop) | — |
| Market change (basket) | +505% | — |

### Per-pair (this run)

| Pair | Trades | Tot % | Win % | MDD % |
|---|---:|---:|---:|---:|
| BTC/USDT:USDT | 32 | +3.82 | 56.2 | 0.53 |
| DOGE/USDT:USDT | 45 | +2.88 | 53.3 | 1.56 |
| AVAX/USDT:USDT | 64 | +2.66 | 50.0 | 4.74 |
| ETH/USDT:USDT | 23 | +2.53 | 60.9 | 0.42 |
| SOL/USDT:USDT | 60 | +1.61 | 46.7 | 5.64 |
| ARB/USDT:USDT | 28 | −1.01 | 57.1 | 2.57 |

---

## What worked

- **Hypothesis confirmed.** The naive funding-carry signal flips from disaster to viable when the regime is bull. 5 of 6 pairs positive; win rate 52.4% vs 10.6% in bear. Average loser remains the −10% stop (29 stops hit) — the loss mechanism is identical, but winners now compound.
- **BTC is the best pair** in bull, was a loser in bear. Funding-rate dynamics on BTC track the regime more reliably than on alts.
- **MDD scales with vol, not with the signal.** SOL and AVAX have ~5% MDDs (high-vol alts); BTC and ETH stay under 1%. Position sizing by vol would smooth this.

## What didn't

- **ARB is the only bull-window loser** (−1.01%, 28 trades). Listed in 2023-03 and may have anomalous early-listing funding dynamics; not enough data to disentangle.
- **MDD 10.65% is large relative to bull-only returns.** The drawdown sits in 2023-08 → 2023-10 (the summer 2023 chop window between the early-year rally and Q4 ETF-anticipation rally). The strategy correctly stops out of bad entries but the cluster of stops adds up.
- **Calmar 3.06 is well below SmaRegime180 bull windows** (Calmar 14–21 in 2020-21 and 2023-24 on BTC). The signal is real but the risk-adjusted return is moderate.

## Next test

1. **Add a regime filter.** Slope-up gate (e.g. price > SMA180 like `SmaRegime180`) as a precondition for the carry signal. Expectation: bear-window MDD drops sharply, bull-window return drops modestly. If true, the gated version is a leaderboard candidate.
2. **Inverse-sign test.** Long when funding > positive threshold (longs paying funding = healthy bull confirmation). Tests whether the regime-conditionality is about *direction of funding* or about *price regime*.
3. **DSR gate.** 252 trades is enough N for a Deflated Sharpe Ratio test. Run before promoting any gated variant.

---

## Implication for `learnings.md`

Entry #4 ("Funding-rate carry … fails catastrophically in bear regimes") needs a 2026-05-10 amendment: **the signal is regime-conditional, not broken**. Bull-window result here flips return from −30.16% to +12.47% and win rate from 10.6% to 52.4% on an unmodified strategy. Promote to "open hypothesis: regime-gated funding-carry as leaderboard candidate."

---

## Reproducibility

```shell
# Funding data
./freqtrade/.venv/bin/python scripts/download_binance_funding.py \
  --coins BTC ETH SOL DOGE AVAX ARB \
  --start 2022-11-01 --end 2025-02-01 \
  --data-dir user_data/data/binance

# OHLCV
./freqtrade/.venv/bin/freqtrade download-data \
  --exchange binance \
  --pairs BTC/USDT:USDT ETH/USDT:USDT SOL/USDT:USDT DOGE/USDT:USDT AVAX/USDT:USDT ARB/USDT:USDT \
  -t 1h 4h --timerange 20221101-20250201 \
  --userdir user_data --data-format-ohlcv feather --trading-mode futures

# Backtest
CARRY_FUNDING_EXCHANGE=binance ./freqtrade/.venv/bin/freqtrade backtesting \
  --userdir user_data -c user_data/config_binance_multi.json \
  --data-format-ohlcv feather -s FundingCarry -i 1h \
  --fee 0.00035 --eps --max-open-trades 6 \
  --timerange 20230101-20250101 --export trades
```

Result archive: `user_data/backtest_results/funding_carry_binance_bull_2023_2025.zip`

---

## Layer 5 — Tail / Path shape (added 2026-05-16)

Backfilled per decision 005 (`wiki/decisions/005-evaluation-and-diversity-plan.md`). Generated with `scripts/eval_layers.py`.


**Binance bull 2023-2025**

| Metric | Value | Reading |
|---|---:|---|
| Skew | +1.32 | right-tailed (rare big wins) |
| Excess kurtosis | +30.98 | fat-tailed (Sharpe overstates) |
| Tail ratio (\|P95\|/\|P5\|) | 1.89 | winners > losers in size |
| CVaR-5% (daily) | -0.87% | mean loss on worst 5% of days |
| Ulcer Index | 5.49 | path-aware DD (lower = better) |
| Martin ratio | 1.10 | CAGR per unit ulcer (higher = better) |
| Pain index | 4.05 | mean abs drawdown |

_N_obs (daily): 731_

