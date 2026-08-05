# 2026-08-05 — Hyperliquid paper bot shutdown

The extended Hyperliquid paper-trading run was stopped cleanly on the Hetzner
VPS after the original 30-day gate had expired.

- Freqtrade and healthcheck containers: stopped and removed by Docker Compose.
- Trade database and logs: retained on the VPS.
- Final database checkpoint: 22 trades total, 21 closed, 1 open.
- Realized closed P/L: approximately `-35.40 USDC`.

This does not constitute a pass or fail decision for the original gate. The
day-30 gate report and full extended-run evaluation remain to be written.
