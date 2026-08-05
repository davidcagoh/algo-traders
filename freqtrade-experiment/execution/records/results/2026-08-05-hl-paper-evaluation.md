# 2026-08-05 — Hyperliquid paper-run evaluation

**Strategy:** `HmmSmaSlopeV2`
**Capital:** 1,000 USDC simulated
**Original gate window:** 2026-05-21 through 2026-06-20
**Extended observation window:** 2026-05-21 through 2026-08-05
**Verdict:** **Do not graduate to live capital; park the strategy.**

## Evidence

The trade ledger was read from the final read-only Supabase mirror of the VPS
Freqtrade database. Daily wallet values were reconstructed from cumulative
realized closed-trade P/L and evaluated with the repository's shared
`evaluation/` stack using 365-day crypto annualisation.

| Metric | Original 30 days | Full extended run |
|---|---:|---:|
| Closed trades | 2 | 21 |
| Open trades at endpoint | 0 | 1 |
| Realized P/L | -0.88 USDC | -35.40 USDC |
| Realized return on 1,000 USDC | -0.09% | -3.54% |
| Win rate | 0.0% | 4.8% |
| Profit factor | 0.000 | 0.0006 |
| Realized-balance MDD | 0.06% | 3.51% |
| Sharpe | -3.49 | -5.54 |
| Calmar | -12.13 | -4.49 |
| SQN | -2.03 | -7.03 |
| Ulcer Index | 0.06 | 1.36 |
| Maximum consecutive losses | 2 | 11 |
| DSR | 0.017 | 0.001 |

DSR is a non-binding humility check here: the daily samples are only 30 and
76 observations, respectively, below the stack's 250-observation threshold.
Layer 6 MDB is unavailable because no comparison strategy ran concurrently.

## Gate assessment

The pre-registered 30-day gate required at least five round trips. It produced
only two, so the original gate is **incomplete**, not a pass. The gate allowed
a 15-day extension only if that extension was pre-registered; the bot instead
continued beyond the deadline without a dated extension decision.

The extended run is therefore supporting evidence rather than a valid
continuation of the original gate. It nevertheless supplies a decisive
retirement signal: the existing strategy rule kills after six consecutive
losses, while the extended ledger contains eleven.

Uptime percentage, same-OHLC signal fidelity, slippage, funding impact, and a
complete log exception audit cannot be reconstructed from the retained trade
mirror. Their absence prevents a retrospective gate pass. The realized-balance
curve also excludes mark-to-market P/L on open positions, so its MDD is a lower
bound on economic drawdown.

## Pair attribution

All observed pair totals were negative:

| Pair | Realized P/L |
|---|---:|
| AVAX/USDC | -1.58 USDC |
| SOL/USDC | -4.08 USDC |
| BTC/USDC | -5.80 USDC |
| ARB/USDC | -7.75 USDC |
| ETH/USDC | -16.18 USDC |

One ETH position with approximately 68.97 USDC stake remained open at the
final mirrored checkpoint and is excluded from realized P/L.
