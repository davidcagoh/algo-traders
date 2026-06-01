# FundingCarry — 2026-05-10

**Strategy:** `user_data/strategies/FundingCarry.py`

## Setup

- Pairs: `BTC, ETH, SOL, HYPE, ARB, AVAX, DOGE` (all `/USDC:USDC`)
- Timeframe: 1h
- Range: 2025-11-04 → 2026-05-09 (~187 days)
- Fee: `--fee 0.00035`
- `--eps --max-open-trades 7`, stoploss = −10%
- Signal: 24h rolling mean of hourly funding rate. Enter long on cross below `ENTRY_THRESHOLD = -0.00001` (~5th-percentile of the rolling mean), exit on cross above `EXIT_THRESHOLD = 0.00002`.
- Hypothesis: sustained negative funding ⇒ short crowdedness ⇒ mean-reversion bounce + carry payment.

## Headline

**Strategy is catastrophically negative on the bear window: −30.16% return, win rate 10.6%, MDD 42.14%, Calmar −7.35.** Avg loser is exactly −10.06% — the stop-loss — meaning virtually every losing trade hit the stop. Conclusion: naive funding-rate carry is not a standalone strategy in a sustained downtrend. The hypothesis is wrong in this regime.

## Per-pair results

| Pair | Trades | Tot Profit % | Win % | Avg loser | Notes |
|---|---:|---:|---:|---:|---|
| HYPE/USDC:USDC | 2 | +5.04% | 50.0% | — | One +60% winner saves the pair |
| ETH/USDC:USDC | 1 | −1.00% | 0% | −10.06% | One trade, stopped out |
| DOGE/USDC:USDC | 5 | −2.26% | 20.0% | — | |
| BTC/USDC:USDC | 3 | −3.01% | 0% | −10.06% | |
| ARB/USDC:USDC | 8 | −8.05% | 0% | −10.06% | All 8 stopped out |
| SOL/USDC:USDC | 16 | −8.82% | 18.8% | — | |
| AVAX/USDC:USDC | 12 | −12.07% | 0% | −10.06% | All 12 stopped out |
| **TOTAL** | **47** | **−30.16%** | **10.6%** | | |

## Read

**The carry hypothesis fails in this regime because negative funding is a *trend-down indicator*, not a contrarian signal.** When alt-coin funding sits below the 5th-percentile floor for 24 hours, the venue's longs are getting squeezed and shorts are getting paid because shorts are right. Going long earns ~0.001%/hour funding (~9%/yr) but loses 10% to the underlying in days. The 9%/yr carry is annualised — it would take a year to recover one stop-out.

**The "all losers exactly hit −10.06%" pattern is diagnostic.** It tells us:
1. The strategy is unable to time exits — the rolling mean stays negative through entire crashes.
2. The underlying volatility (alts) is too high relative to the carry yield. A 10% stop on a 9%/yr carry is a 1-year-equivalent risk for a 1-hour edge.
3. The strategy holds positions for ~17 days on average — losers cut at stop, winners (when they exist) ride for 70+ days.

**Three structural fixes that would change the verdict:**
1. **Conditional carry** — only enter long when both (a) funding < threshold AND (b) price is above a slow MA / not in a confirmed downtrend. The HMM-bull-state filter from `HmmRegime4Rolling` is a natural conjunction.
2. **Tighter stop relative to carry yield** — current −10% stop is order(year of carry); a stop at, say, 1× weekly carry (−0.2%) creates frequent re-entries instead of large drawdowns.
3. **Symmetric short-leg version** — receiving carry on the long side when funding is negative AND on the short side when funding is positive lets the strategy earn carry in both regimes. Repo policy is long-only, but this is the obvious follow-up if the long-side ever works.

**This is a useful negative result** that confirms a literature claim (Inan 2025: "funding rate has predictive power for returns") only holds when conditioned on regime. The funding-rate carry signal needs a price-level or trend filter to be tradable.

## Open follow-ups

- **HMM × Carry conjunction:** enter long only when bull-prob > 0.65 AND funding < entry threshold. Tests whether the two signal families are complementary.
- **BTC-only carry** (re-run with single pair) — BTC's funding distribution is more dollar-driven and may behave more like a bond yield. The result here loses 3% on BTC alone, but the mechanism may differ from alts.
- **Bull-window backtest** when CEX BTC history is loaded — does the carry signal work in the inverse regime? If yes, this is a genuine regime-conditional strategy, not a discarded one.
- **Reverse the signal** — long when funding > some positive threshold (rolling mean indicating long-side momentum). The "predictability" paper hints this direction may dominate in trending markets.
