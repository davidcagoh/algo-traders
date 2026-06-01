# HmmRegime4Rolling Multi-Asset — 2026-05-10

**Strategy:** `user_data/strategies/HmmRegime4Rolling.py`
**Backtest ZIP:** see `user_data/backtest_results/` for the 2026-05-10 multi-pair run

## Setup

- Pairs: `BTC, ETH, SOL, HYPE, ARB, AVAX, DOGE` (all `/USDC:USDC`)
- Timeframe: 1h
- Range: 2025-11-25 → 2026-05-09 (~165 days, post burn-in)
- Fee: `--fee 0.00035`
- `--eps --max-open-trades 7`
- Same HMM params as single-asset rolling run (FIT_WINDOW=1000, REFIT_EVERY=168)
- Note: `HmmRegime4` (look-ahead) crashed on this universe — non-positive-definite covariance on one coin. Patched with try/except so it returns NaN bull_prob (no entries) on a fit failure. Rolling version already had try/except, so it ran cleanly.

## Headline

**The HMM regime structure does not generalise across the 7-coin universe.** Total return −5.62%, win rate 35.0%, MDD 14.7%. Only 2 of 7 coins are profitable.

## Per-pair results

| Pair | Trades | Tot Profit % | Win % | Notes |
|------|---:|---:|---:|------|
| **HYPE/USDC:USDC** | 98 | **+5.63%** | 32.7% | Single best trade +43.3% — likely one big trend caught luck |
| **BTC/USDC:USDC** | 56 | **+1.45%** | 41.1% | Consistent with single-asset run (+1.15%) |
| ETH/USDC:USDC | 53 | −0.86% | 39.6% | Win rate decent, magnitude poor |
| DOGE/USDC:USDC | 69 | −1.36% | 36.2% | |
| SOL/USDC:USDC | 65 | −2.20% | 41.5% | Highest win rate but losing — losers hit harder |
| AVAX/USDC:USDC | 82 | −2.34% | 31.7% | |
| **ARB/USDC:USDC** | 81 | **−6.36%** | 25.9% | Worst — sub-coin-flip win rate |
| **TOTAL** | 504 | **−6.06%** | **34.7%** | 14.7% MDD over 125d |

(Some figures differ trivially from the portfolio summary — pair table includes left-open trades.)

## Read

**The single-asset BTC result was not a transferable model.** When the same parameters are applied to the broader Hyperliquid majors universe, only HYPE and BTC are profitable, and HYPE's contribution is dominated by a single +43% trade. Strip out HYPE's one big trade and the portfolio is materially negative across the board.

**Win rate by pair ranges 25.9% → 41.5%, but win rate alone doesn't predict profitability.** SOL has the second-highest win rate (41.5%) and is still −2.20%; ARB has 25.9% and is −6.36%. The HMM-based entry signal correctly identifies *some* directional structure on every coin, but the asymmetry of winner-vs-loser magnitudes is wrong on most.

**Three plausible causes:**

1. **One-size-fits-all HMM params.** The 4-state structure with 1000-bar fit window may be tuned (implicitly) to BTC's volatility regime. ARB/AVAX/DOGE/HYPE have higher vol and faster regime turnover. A per-coin parameterisation might recover signal — or might be overfitting.
2. **Smaller-cap coins have noisier features.** The 24-bar log-return + log-volume features may carry less signal-to-noise on alts than on BTC. Volume z-scoring across the full series is also more distortion-prone on coins with explosive launch periods (HYPE).
3. **Bear-window selection bias.** This is a 6-month bear window (BTC −22%, portfolio market −16%). A long-only HMM-gated strategy on alts during a beta-driven sell-off has nowhere good to be. The single-asset BTC result enjoyed BTC's relative stability vs alts.

**Implication for the leaderboard:** HmmRegime4Rolling's BTC-only number (+1.15%) should not be read as "an HMM regime strategy works." It should be read as "an HMM regime strategy works on BTC in this window." That's a much weaker claim and weakens the case for HMM as a strategy family without per-coin tuning or a bull-window check.

**This is a useful negative result.** Per `wiki/learnings.md` cross-cutting fact: *single-asset-tuned strategies fail to generalise*. The cleanest path forward is a multi-asset NSGA-II sweep with per-coin params and Pareto evaluation, not more single-asset experiments.

## Open follow-ups

- **Per-coin re-fitting of HMM hyperparameters** (n_components, fit_window, threshold). Apply DSR gate over the resulting sweep.
- **Run on the bull window** (using CEX BTC + ETH proxies for 2024 bull) to check if regime detection works when there *is* a bull regime to detect.
- **HMM on 4h timeframe** for the 7-coin universe — single-asset BTC HMM was on 1h; SmaRegime180 is on 4h. The 4h version may have less noise on alts.
- **Combine HMM + funding gate** (next experiment). If funding-rate carry is a separate signal source, conjunction may filter out the false-positive entries that dominated ARB/AVAX losses.
