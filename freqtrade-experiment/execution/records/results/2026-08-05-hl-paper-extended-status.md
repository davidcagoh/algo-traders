# 2026-08-05 — Hyperliquid paper run extended-status checkpoint

**Strategy:** `HmmSmaSlopeV2`
**Deployment:** Hetzner VPS, Freqtrade dry-run, Hyperliquid mainnet prices
**Original pre-registered window:** 2026-05-21T04:44:24Z → 2026-06-20T04:44:24Z

## Verified deployment state

Checked from the VPS at approximately `2026-08-05T02:52Z`:

- Freqtrade container: running and emitting heartbeats.
- Healthcheck container: running.
- Trade database: 22 trades total, 21 closed, 1 open.
- Database trade range: 2026-05-21 → 2026-08-05.
- Realized closed P/L: approximately `-35.40 USDC`.

## Interpretation

The bot continued beyond the original 30-day dry-run deadline. This is an
extended paper-trading run, not a silent extension of the pre-registered gate.
The repository still needs a separate day-30 gate report covering uptime,
signal fidelity, slippage, drawdown, funding, trade count, and exceptions.

This checkpoint records deployment state only; it does not declare the strategy
accepted for live capital.
