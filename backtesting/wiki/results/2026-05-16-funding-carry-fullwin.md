# FundingCarry — full window (2026-05-16)

**Strategy:** `user_data/strategies/FundingCarry.py`
**Code:** C1

## Setup

- Pairs: `BTC, ETH, SOL, AVAX, DOGE` (all `/USDT:USDT`, Binance perp)
- Timeframe: 1h
- Range: **2020-09-23 → 2026-05-09** (5.5y, 2 bulls + 2 bears)
- Fee: `--fee 0.00035`
- `--eps --max-open-trades 5`, stoploss = −10%
- Funding source: `CARRY_FUNDING_EXCHANGE=binance` → `user_data/data/binance/funding/<COIN>-funding.parquet`
- **Funding history now covers the full window** (6165–6240 rows per coin, backfilled 2026-05-16 via `scripts/download_binance_funding.py --force`)
- Signal: 24h rolling mean of hourly funding rate. Enter long on cross below `ENTRY_THRESHOLD = -0.00001`, exit on cross above `EXIT_THRESHOLD = +0.00002`.

## Headline

**With the full 5.5y funding history, FundingCarry goes from "ambiguous, mostly inactive" to a real, modestly-positive standalone strategy: +32.44% total return, CAGR +5.12%, MDD 15.65%, Calmar 1.93, SQN 1.22 over 957 trades.** Win rate 51.0%, profit-factor 1.15, average trade duration 2 days. Worst drawdown was 2022-04 → 2022-06 (Luna/3AC bear) — DD recovered in 53 days.

## Layer 1-4 Metrics

| Metric | Value |
|---|---:|
| Total return | +32.44% |
| CAGR | +5.12% |
| MDD | 15.65% |
| Calmar | 1.93 |
| Sharpe (daily) | 0.45 |
| Sortino | 0.43 |
| SQN | 1.22 |
| Profit factor | 1.15 |
| Trades | 957 |
| Win rate | 51.0% |
| Avg duration | 2d 00:50 |

## Layer 5 — Tail / Path shape

| Metric | Value | Reading |
|---|---:|---|
| Skew | +8.83 | right-tailed (rare big wins) |
| Excess kurtosis | +221.61 | very fat-tailed (Sharpe overstates) |
| Tail ratio (\|P95\|/\|P5\|) | 0.74 | losers > winners in size |
| CVaR-5% (daily) | −1.28% | |
| Ulcer Index | 5.87 | |
| Martin ratio | 0.81 | |
| Pain index | 4.90 | |

## Per-pair breakdown

| Pair | Trades | Σ profit_ratio % | Win % |
|---|---:|---:|---:|
| BTC/USDT:USDT | 125 | +127.00 | 57.6 |
| ETH/USDT:USDT | 138 | +109.11 | 54.4 |
| SOL/USDT:USDT | 239 | +67.21 | 44.8 |
| DOGE/USDT:USDT | 214 | +15.86 | 51.4 |
| AVAX/USDT:USDT | 241 | +5.43 | 51.5 |

All 5 coins are profitable. BTC and ETH are the standouts — funding-rate carry is cleaner on majors where funding moves with macro positioning rather than coin-specific narrative cycles. AVAX is barely positive over 241 trades — a genuine zero-edge instance, not a loser.

Note: per-pair Σ profit_ratio % is the sum of per-trade profit ratios (each ≤ 10% bounded by stop-loss), not the portfolio contribution. Totals > 100% reflect 5+ years of fixed-stake compounding, not >100% portfolio gain.

## Comparison to truncated-window run

| Metric | Truncated (2.3y active in 5.5y) | Full window (5.5y) |
|---|---:|---:|
| Return | +2.13% | **+32.44%** |
| Calmar | 1.37 | **1.93** |
| SQN | 1.28 | 1.22 |
| MDD | 8.52% | 15.65% |
| Trades | (signal NaN outside 2022-11 → 2025-02) | 957 |

The truncated-window result understated the strategy's real return profile by ~15× because the signal was NaN-inactive for 3.2y of the 5.5y window. The MDD got *worse* with more data (15.65% > 8.52%) — the previous run missed the 2022 bear funding compression. The Calmar improved despite the larger MDD because the return scaled up faster.

## Verdict vs kill criteria & portfolio gate

- **K1 (standalone MDD ≤ 5.5%):** ✗ Fails. 15.65% MDD is 2.85× the threshold. Standalone NOT a paper-trade candidate.
- **Decision 009 portfolio-aware exception (MDB-rp ≥ 0.30 robust, MDD ≤ 11% hard cap):** ✗ Fails on the MDD hard cap (15.65% > 11%). Cannot enter book even as portfolio diversifier.
- **Calmar walk-forward minimum (2.0):** Borderline — Calmar 1.93 is 0.07 below.

**Classification change:** C1 moves from "ambiguous / killed-by-truncation-uncertainty" to **"genuinely positive standalone but kills itself on MDD"**. The strategy *works* — it has real edge across 5 coins over 5.5y — but the 10% stop-loss combined with fixed-stake sizing produces an MDD too large to admit into any reasonable book. Family is alive; this specific parameterisation is not.

## Read

**The full window resolves the prior ambiguity.** With only 2.3y active, we couldn't tell whether the +2.13% was noise or signal — now we know it's a low-Sharpe-but-real long-funding-carry edge that earns ~5%/yr CAGR with 15% drawdowns. The carry hypothesis (Inan 2025) is partially confirmed: negative funding *does* predict positive returns over a 5.5y horizon, but the signal is dominated by a few large winning trades (skew +8.83, excess kurtosis +221.6) — a thin tail of bull-regime carries. Most of the win comes from BTC/ETH (the highest-volume markets where funding mechanics are cleanest); SOL adds bonus return; AVAX/DOGE are roughly noise-around-zero.

**What needs to change for C1 to enter a book:**
1. **Tighter stop relative to carry yield** — current −10% stop is order(year of carry); replace with a vol-targeted stop or a 1× weekly-carry stop.
2. **Position sizing on funding magnitude** — scale up when funding deeply negative, scale down when funding near threshold. Current binary entry wastes signal information.
3. **Regime gate** — the 2022 drawdown is a directional-bear loss, not a funding-mechanic loss. Combining with a slow-MA filter (like T3's SmaRegime180) could keep the carry signal but reject the worst regimes.

## Open follow-ups

- **Vol-targeted sizing variant** — replace fixed 1000 USDT stake with target-volatility sizing (e.g. 10%/yr realised vol target). Expected to compress MDD from 15.65% toward 8-10% with similar return.
- **Conditional on T3 bull regime** — `FundingCarry & SmaRegime180.bull == True`. Would test whether the 2022 bear DD is signal-uncorrelated and removable.
- **Per-coin funding-sign learning** — BTC/ETH/SOL clearly different from AVAX/DOGE. A model that learns per-coin entry thresholds could rescue the weaker coins.
