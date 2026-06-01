# HmmCarry — 2026-05-10

**Strategy:** `user_data/strategies/HmmCarry.py`

## Setup

- Pairs: `BTC, ETH, SOL, HYPE, ARB, AVAX, DOGE` (all `/USDC:USDC`)
- Timeframe: 1h
- Range: 2025-11-25 → 2026-05-09 (~165 days, post-burn-in)
- Fee: `--fee 0.00035`, `--eps --max-open-trades 7`, stop −10%
- **Entry:** `bull_prob >= 0.65` AND `funding_roll < −0.00001` (newly enters joint regime)
- **Exit:** `bull_prob < 0.45` OR `funding_roll >= 0.00002` (either signal flips)
- HMM is the walk-forward refit version (FIT_WINDOW=1000, REFIT_EVERY=168), no look-ahead.

## Headline

**Conjunction is worse than HmmRegime4Rolling alone (−19.59% vs −5.62%), better than naive FundingCarry alone (−30.16%).** The expected tightening (filter false-positive entries by requiring both signals) only worked on HYPE/ETH. On BTC the conjunction *collapsed* win rate from 41.1% (HMM-only) to 7.7%. **The two signals are anti-complementary in this window**, not independent. Useful structural finding.

## Results

| Metric | HmmCarry (conjunction) | HmmRegime4Rolling alone | FundingCarry alone |
|---|---:|---:|---:|
| Total return | **−19.59%** | −5.62% | −30.16% |
| Win rate | 31.3% | 35.0% | 10.6% |
| Trades | 278 | 504 | 47 |
| MDD | 23.86% | 14.70% | 42.14% |
| Calmar (daily) | −9.51 | −5.62 | −10.27 |
| SQN | (worse than HMM) | −0.59 | −3.60 |
| Avg duration | 22h 39m | 1d 1:38 | 17d 1:18 |

## Per-pair (HmmCarry)

| Pair | Trades | Tot Profit % | Win % | vs HMM-only |
|---|---:|---:|---:|---|
| **HYPE/USDC:USDC** | 8 | **+2.07%** | **87.5%** | HMM-only: +5.63%/32.7%. Conjunction trades fewer, wins much more often, totals less due to losing the one big trade. |
| **ETH/USDC:USDC** | 4 | **+0.31%** | 75.0% | HMM-only: −0.86%/39.6%. **Tightening worked here.** |
| ARB/USDC:USDC | 61 | −1.06% | 41.0% | HMM-only: −6.36%/25.9%. Less negative but still losing — partial improvement. |
| **BTC/USDC:USDC** | 13 | **−1.26%** | **7.7%** | HMM-only: +1.45%/41.1%. **Catastrophic — conjunction picks the worst BTC moments.** |
| DOGE/USDC:USDC | 43 | −3.35% | 34.9% | HMM-only: −1.36%/36.2%. Worse. |
| AVAX/USDC:USDC | 59 | −5.78% | 32.2% | HMM-only: −2.34%/31.7%. Worse. |
| SOL/USDC:USDC | 97 | −9.22% | 24.7% | HMM-only: −2.20%/41.5%. Worse. |
| **TOTAL** | 285 | **−18.29%** | 33.0% | HMM-only: −6.06%/34.7%. |

(Pair table includes left-open trades, summary excludes; numbers differ trivially.)

## Read

**The signals are anti-complementary on most coins.** Required reading: the conjunction filtered HMM trades from 504 to 278 (45% reduction), expecting the surviving entries to be the cleanest. Instead, the surviving entries underperformed the unfiltered set on 5 of 7 pairs, dramatically on BTC. This means the funding-rate-negative condition selected for *worse-than-average* moments within the HMM-bull regime — the opposite of independence.

**Structural explanation.** HmmRegime4 is a *reactive* regime detector — it labels bull on a trailing-window of return-feature evidence. Funding rate is a *forward-looking* sentiment proxy — when funding goes negative, market makers and traders are pricing in further downside. The conjunction "bull regime AND shorts crowded" picks moments where:
- the HMM hasn't yet caught up to a regime turn (late-cycle bull lag);
- the funding market has already turned (early-cycle bear lead).

You're systematically buying tops of small bull rallies right as the venue's positioning turns. On BTC the effect is severe (7.7% win rate, 13 trades) — every BTC funding-stress moment in this window coincided with a top.

**Why HYPE/ETH worked but BTC/SOL/AVAX didn't.** HYPE and ETH had genuine reversal patterns where the conjunction filter helped — funding stress *did* mean reversion was due. BTC, SOL, AVAX in this 6-month window had structural downtrends where any funding stress was a sell signal regardless of HMM state. The strategy works on coins where funding-rate dynamics lead price; fails on coins where they coincide with continuation.

**This rules out the simple HMM × Carry conjunction as a tradable strategy in the bear window.** It does *not* rule out the conditional structure entirely:

1. **Reverse the carry condition:** enter when bull_prob > 0.65 AND funding_roll **>** some positive threshold — i.e. require both bull regime AND positive funding (longs paying = healthy bull market). This inverts the hypothesis from "negative funding is contrarian" to "positive funding confirms the trend."
2. **Per-coin signal sign:** HYPE/ETH respond to negative-funding-as-contrarian; BTC/SOL/AVAX may respond to positive-funding-as-trend-confirmation. A per-coin sign assignment (treat funding as feature, learn coefficient per coin) is the obvious extension.
3. **Time-priority filter:** require funding to have been negative for K bars *before* HMM goes bull (lead-then-confirm), not at the same instant. This separates lead-then-bounce setups from late-cycle alignment.

## What this changes

1. **HMM × Carry conjunction is ruled out as a tradable single-rule strategy.** Cross-cutting learnings file should add: signal conjunction without per-coin sign assignment is suspect when one signal is reactive and the other is forward-looking.
2. **The "two-signal independence" assumption was wrong here.** This is itself a Pareto datapoint: building a meta-allocator over `[SmaRegime180, HmmRegime4Rolling, FundingCarry]` should *not* assume their entries are uncorrelated.
3. **Per-coin parameterisation is now a higher-priority experiment** than further single-coin tuning. The 7-asset universe shows clearly that one-size-fits-all parameters destroy alpha that exists per-coin.

## Open follow-ups

- **Reverse-sign HmmCarry**: positive funding as bull confirmation (the natural alternative).
- **Per-coin funding-sign learning**: regress coin returns on lagged funding to assign sign and threshold per coin.
- **Lead-lag conjunction**: require funding-negative for K bars *before* HMM-bull turns on. Uses the time ordering rather than coincidence.
- **Concentrate on HYPE/ETH only** — both worked under conjunction. Not a generalisable strategy but a useful narrow application.
