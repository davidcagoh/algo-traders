# FundingExtremeMR — full window (2026-05-16)

**Strategy:** `user_data/strategies/FundingExtremeMR.py`
**Code:** F1

## Setup

- Pairs: `BTC, ETH, SOL, AVAX, DOGE` (all `/USDT:USDT`, Binance perp)
- Timeframe: 4h
- Range: **2020-09-23 → 2026-05-09** (5.5y)
- Fee: `--fee 0.00035`
- `--eps --max-open-trades 5`
- Funding source: `CARRY_FUNDING_EXCHANGE=binance` (now covers full window)
- Thesis: counter-funding mean-reversion (long when funding extremely negative — overshoot snap-back). Pre-registered kill criteria in `decisions/008-kill-criteria-funding-mr.md`.

## Headline

**F1 stays killed.** Full window: −11.60% return, MDD 33.51%, Calmar −0.32, SQN −0.64 over 2582 trades. Win rate 47.6%, profit factor 0.97, average profit per trade −0.05% — below the 0.07% one-way taker fee floor.

## Layer 1-4 Metrics

| Metric | Value |
|---|---:|
| Total return | −11.60% |
| CAGR | −2.17% |
| MDD | 33.51% |
| Calmar | −0.32 |
| Sharpe (daily) | −0.13 |
| Sortino | −0.11 |
| SQN | −0.64 |
| Profit factor | 0.97 |
| Trades | 2582 |
| Win rate | 47.6% |
| Avg duration | 10h 05m |

## Layer 5 — Tail / Path shape

| Metric | Value | Reading |
|---|---:|---|
| Skew | +1.58 | mildly right-tailed |
| Excess kurtosis | +26.19 | fat-tailed |
| Tail ratio (\|P95\|/\|P5\|) | 0.72 | losers > winners |
| CVaR-5% (daily) | −1.56% | |
| Ulcer Index | 15.98 | |
| Martin ratio | −0.14 | |
| Pain index | 11.89 | |

## Per-pair breakdown

| Pair | Trades | Σ profit_ratio % | Win % |
|---|---:|---:|---:|
| ETH/USDT:USDT | 480 | +57.50 | 48.5 |
| BTC/USDT:USDT | 584 | +49.34 | 48.5 |
| SOL/USDT:USDT | 450 | −47.73 | 44.2 |
| AVAX/USDT:USDT | 544 | −53.03 | 47.8 |
| DOGE/USDT:USDT | 524 | −123.78 | 48.3 |

**Split portfolio.** BTC/ETH are positive (the same majors that worked for C1); SOL/AVAX/DOGE are decisively negative. DOGE alone destroys the strategy. This is the exact opposite shape from the carry signal: extreme-negative funding on alts predicts continuation, not reversion.

## Comparison to truncated-window run

| Metric | Truncated (2.3y active in 5.5y) | Full window (5.5y) |
|---|---:|---:|
| Return | (n/a, signal flat outside 2022-11→2025-02) | −11.60% |
| MDD | 29.94% | 33.51% |
| Calmar | (n/a — no Calmar reported on prior leaderboard) | −0.32 |
| Trades | (low — most window NaN) | 2582 |

Extending funding history did NOT rehabilitate F1 — if anything it confirms the kill. MDD worsened from 29.94% to 33.51%; return remains negative; the strategy spent 923 days underwater (drawdown from 2023-08 → 2026-02 was 33.51% peak-to-trough over **2.5 years**).

## Verdict vs kill criteria & portfolio gate

- **K1-fmr (decision 008: MDD ≤ 5%, Calmar ≥ 0.5, profit_factor ≥ 1.1):** ✗✗✗ All three thresholds fail simultaneously. MDD 33.51% is **6.7× the limit**; Calmar is negative; PF 0.97 < 1.0.
- **Decision 009 portfolio-aware exception:** ✗ Far below the 11% MDD hard cap; would only be eligible if MDB-rp ≥ 0.30 (it's −1.85).
- **K1 standalone (5.5%):** ✗ 6× over.

**Classification change:** **F1 stays ✗ killed.** The 2.3y-truncation hypothesis (that the previous result was an artefact of sparse data) is rejected — with 5.5y of clean funding data, the strategy is decisively bad. The counter-funding mean-reversion thesis (Le 2026's 8h OU half-life on Hyperliquid) does NOT generalise to Binance 4h execution on a 5-coin alt universe. The mechanism is real on a small fraction of pairs (BTC/ETH show modest positive contribution) but is overwhelmed by continuation on DOGE/AVAX/SOL.

## Read

**Extending the window doesn't change the verdict — it sharpens it.** The strategy now has 2582 trades over 5.5y, which is enough data for an honest read: average trade profit −0.05%, below the cost floor. The funding-extreme-MR thesis is *backwards* on alts. When DOGE funding goes deeply negative (longs paying shorts), it's because DOGE is being shorted aggressively for good reason — narrative collapse, capitulation tape — and reverting toward zero takes long enough that the position bleeds to the 10% stop. On BTC/ETH the same signal works modestly because their funding distributions are mean-reverting around macro positioning; on alts it's narrative-driven and trending.

**Future variants worth testing (deferred):**
1. **BTC/ETH-only F1** — would the strategy clear K1 if AVAX/SOL/DOGE are dropped? Per-pair numbers suggest yes for the *direction*, but the trade count probably collapses below DSR-viable.
2. **1h timeframe with hourly funding** — 4h bars on 8h funding may be aliasing.
3. **Asymmetric exit** — current rules likely hold through funding-sign flip; tighten exit to act on the first positive print.

## Notes on the data backfill

Funding parquets now cover 2020-09-23 → 2026-05-09 for all 5 coins (6165–6240 rows each, 8h cadence). No coin had a Binance listing-date gap inside the window (AVAX 2020-09-09, DOGE 2020-07-10, both earlier than 2020-09-23). Backfill verified: `time.min() == 2020-09-23 00:00:00 UTC`, `time.max() == 2026-05-09 16:00:00 UTC`.
