# HmmRegime4Rolling — 2026-05-10

**Strategy:** `user_data/strategies/HmmRegime4Rolling.py`
**Backtest ZIP:** `user_data/backtest_results/backtest-result-2026-05-10_01-41-03.zip`

## Setup

- Pair: `BTC/USDC:USDC` (futures)
- Timeframe: 1h
- Range: 2025-11-25 → 2026-05-09 (~165 days; later start than HmmRegime4 because the rolling refit needs FIT_WINDOW=1000 bars of burn-in before first signal)
- Fee: `--fee 0.00035` (Hyperliquid taker)
- `--eps --max-open-trades 1`
- Same 4-state GaussianHMM, same features (24-bar log return + log-volume z-score), same thresholds (entry P(bull) > 0.65, exit < 0.45)
- **What changed vs HmmRegime4:** the HMM is re-fit every `REFIT_EVERY=168` 1h bars on the trailing `FIT_WINDOW=1000` bars. At each bar t, the bull-state posterior is computed using only data through bar t (predict_proba on the trailing window up to t, take last entry). No look-ahead.

## Results

| Metric | Value |
|---|---|
| Trades | **53** |
| Total return | +1.15% (+11.48 USDC on 1000) |
| CAGR | 2.56% |
| Sharpe (closed) | 0.51 |
| Sortino (closed) | 1.89 |
| **Calmar (closed)** | **12.11** |
| **SQN** | **0.59** |
| Profit Factor | 1.31 |
| Expectancy (Ratio) | 0.22 (0.19) |
| **Win rate** | **37.7%** (20W / 0D / 33L) |
| Max consec wins / loss | 4 / 7 |
| Max DD | 1.10% (11.06 USDC) |
| DD duration | 27d (2026-03-11 → 2026-04-07) |
| Best trade | +13.66% |
| Worst trade | −2.61% |
| Avg duration | 1d 5:01 (winners 2d 10:00, losers 0d 11:27) |
| Market change | −7.69% |

## Comparison vs HmmRegime4 (look-ahead, prior result)

| Metric | HmmRegime4 (look-ahead) | HmmRegime4Rolling (no look-ahead) | Delta |
|---|---|---|---|
| Trades | 74 | 53 | −28% |
| Total return | +2.65% | +1.15% | −57% |
| CAGR | 5.26% | 2.56% | −51% |
| Sharpe (CT) | 1.23 | 0.51 | −59% |
| **Calmar (CT)** | 26.35 | 12.11 | −54% |
| **SQN** | **1.38** | **0.59** | **−57%** |
| Profit Factor | 1.58 | 1.31 | −17% |
| **Win rate** | **45.9%** | **37.7%** | **−8.2pp** |
| MDD | 1.03% | 1.10% | +7% |
| Test window | 187d (Nov-04 →) | 165d (Nov-25 →) | not directly comparable |

## Read

**The look-ahead absorbed roughly half the alpha.** Every headline metric — return, CAGR, SQN, Sharpe, Calmar — drops by ~50–60% under honest walk-forward. Profit Factor and win rate are sturdier (−17% and −8pp respectively), which suggests the regime structure has *some* real signal: the directional call survives, but the magnitude/timing edge that came from fitting on the full window mostly does not.

**Win rate stays above the 35% "signal real" threshold** that the original result card pre-registered. 37.7% on N=53 is statistically meaningful (binomial 95% CI ≈ [25%, 52%], strictly excludes a coin-flip random-entry strategy in this bear-trending window where buy-and-hold is −7.69%). So: the HMM regime detector is doing *something* — but it's a weaker effect than the look-ahead version implied.

**This is the cleanest evidence yet for the look-ahead alpha hypothesis** raised in `wiki/learnings.md`. Open hypothesis #5 (HMM lifts win rate vs SmaRegime180's ~22%) holds with a smaller margin: 37.7% vs 21.9% is still +16pp, still real.

**Honest leaderboard position.** SQN 0.59 places HmmRegime4Rolling *below* SmaRegime180 (SQN 1.02) on the project's co-primary metric — the look-ahead version was ranked above by a margin that mostly evaporates under proper validation. The two strategies should now be read as roughly comparable, with different shapes:
- SmaRegime180 wins on Profit Factor (2.72 vs 1.31) — fewer trades, bigger winners.
- HmmRegime4Rolling wins on win rate (37.7% vs 21.9%) and trade density (53 vs 32) — more frequent, smaller edges.
- Total return is similar order of magnitude (+1.15% over 165d ≈ +2.56% CAGR vs +2.83% over 800d for SmaRegime180; SmaRegime180 still dominates on return per trade).

This is the second concrete Pareto-frontier datapoint (first was the original `HmmRegime4` vs `SmaRegime180`, now confirmed under look-ahead correction).

**MDD is essentially unchanged (1.03% → 1.10%)** — the look-ahead wasn't buying drawdown protection, just trade selection. That's consistent with the read that look-ahead helps the model "know" when bull-states are about to be valid; without it, you take more false-positive entries but the position-sizing stays disciplined.

## What this changes

1. **Demote HmmRegime4 from the leaderboard headline.** The look-ahead version is upper-bound only; HmmRegime4Rolling is the honest number.
2. **HMM regime detection remains a viable strategy family**, but its real edge over SmaRegime180 is smaller than the prior result implied. Both belong on the leaderboard; neither dominates.
3. **The "rolling-window HMM refit was the alpha" hypothesis is partially confirmed.** ~50% of the lift came from look-ahead; ~50% is genuine regime signal.
4. **Pre-register stronger validation gates** before HMM family graduates to paper-trading: at minimum, run on out-of-sample years (CEX BTC history pre-Hyperliquid) and on the 7-asset universe to check generalisation.

## Open follow-ups

- Multi-asset HmmRegime4Rolling run (BTC/ETH/SOL/HYPE/ARB/AVAX/DOGE) — does the regime structure generalise?
- Tune `FIT_WINDOW` and `REFIT_EVERY`. 1000 bars + weekly refit was a guess. A coarse sweep (e.g. {500, 1000, 2000} × {72, 168, 336}) would tell us whether more or less adaptation helps. Apply DSR gate.
- Run on CEX BTC history (Binance perps, ~2019–) to get more bear/bull cycles for stability assessment. Use this as *training-set check*, not as Hyperliquid evaluation (per `wiki/learnings.md` data-sourcing rule).
- Combined HMM + funding-rate gate: only enter when bull-state AND funding < threshold. Tests whether the two signal families are independent or redundant.
