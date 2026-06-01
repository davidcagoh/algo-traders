# Track B — 30d Hyperliquid dry-run Day 8 snapshot

**Snapshot timestamp (UTC):** 2026-05-29  
**Gate:** [live/wiki/decisions/002-track-b-gate.md](../decisions/002-track-b-gate.md)  
**Window:** 2026-05-21T04:44:24Z → 2026-06-20T04:44:24Z (day 8 of 30)

## Bot health

- Both containers up 8 days, zero restarts (`docker ps`)
- Continuous 1-min heartbeats, no errors in logs
- healthchecks.io: green (last ping 3 min before snapshot)
- No open trades at time of snapshot

## Closed trades (2 total)

| # | Pair | Open | Close | Duration | Open rate | Close rate | P&L (USDC) | P&L % | Exit reason |
|---|------|------|-------|----------|-----------|------------|------------|-------|-------------|
| 1 | BTC/USDC | 2026-05-21 08:00 | 2026-05-21 12:00 | 4h | 77,863 | 77,211 | −0.281 | −0.90% | exit_signal |
| 2 | BTC/USDC | 2026-05-22 04:10 | 2026-05-22 20:00 | 15h 49m | 77,830 | 75,818 | −0.600 | −2.66% | exit_signal |

Both trades BTC only. No other pair triggered in 8 days.

## Cumulative stats (from `/api/v1/profit`)

| Metric | Value |
|--------|-------|
| Closed trades | 2 |
| Open trades | 0 |
| Total P&L | −$0.88 (−0.09% of $1000 wallet) |
| Win rate | 0% (0W / 2L) |
| MDD (abs) | $0.88 |
| MDD (%) | 0.089% |
| Avg trade duration | 9h 55m |
| Funding paid (total) | −$0.0043 |
| Trading volume | $106.59 |

## Gate criteria — day 8 status

| Gate criterion | Threshold | Day 8 status |
|----------------|-----------|--------------|
| Uptime | > 99% of 30d | ✓ 8/8 days continuous |
| No unhandled exceptions | 0 | ✓ clean logs |
| MDD | < 8% | ✓ 0.089% |
| Trade count | ≥ 5 round-trip | ⏳ 2/5 — 22 days remain |
| Signal fidelity vs BT | ≥ 95% same-OHLC | not evaluable yet (need ≥5 trades) |
| Slippage realism | ≤ 2× modelled | ✓ limit orders filled at requested price both trades |
| Funding net | within ±50bps/30d | ✓ $0.004 paid so far, negligible |

## Notes

- Strategy is generating signals only on BTC so far. With 6 pairs and 4h timeframe this is low — consistent with the BTC "chop" regime at start (slope +0.013%/period, below the +0.05% bull threshold). HMM+SMA slope filter is likely suppressing entries on other pairs.
- Low trade count (2 in 8 days) is not a gate failure yet — gate requires ≥5 over 30d, 22 days remain. If still < 5 at day 30, gate is incomplete per decision 002 (extend 15d, pre-register extension first).
- No capital at risk, no position sizing concern — both trades were small ($22–31 stake) consistent with continuous slope-strength sizing in low-conviction chop.
- No issues requiring intervention.

## Next snapshot

Day 15 (2026-06-05) or earlier if a gate-relevant event occurs (exception, MDD spike, position opened).
