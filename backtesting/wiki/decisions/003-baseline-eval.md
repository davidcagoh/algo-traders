# 003 — Baseline eval for Session Start Routine

**Date:** 2026-04-24
**Status:** Accepted

## Decision

The Session Start Routine's baseline eval runs **`LongOnlyStrategy` on 1h BTC/USDC:USDC, ~200 days (5000 candles)** via `./scripts/run_eval.sh`.

Primary metric: **Calmar (CAGR / |MDD|)**. Sharpe is also displayed on every report card as a sanity check.

## Rationale

- Already verified end-to-end on 2026-04-24: 5001 rows of 1h BTC/USDC:USDC data land in `user_data/data/hyperliquid/`, `freqtrade backtesting` consumes them, 49 trades over ~200 days, placeholder `LongOnlyStrategy` lost 0.89%.
- Zero setup required — the data and strategy file already exist in the repo.
- Runs in seconds on a single 1h pair, so the Session Start Routine stays cheap.
- Single-pair, single-timeframe is intentional: the baseline's job is regression detection, not alpha discovery. A drift in Calmar here means infrastructure broke, not that markets changed.

## How to change this

To swap the baseline (e.g. multi-pair basket once the data is downloaded, or a different timeframe):

1. Update the command in `scripts/run_eval.sh`.
2. Update the expected baseline values cited in `wiki/_index.md` Strategy Leaderboard.
3. Update the "Run baseline eval" step in `CLAUDE.md` → Session Start Routine.
4. Append a row to the table below recording the change.

## Change log

| Date | Baseline | Reason | Who |
|------|----------|--------|-----|
| 2026-04-24 | `LongOnlyStrategy` on 1h BTC/USDC:USDC, ~200d | Initial — verified end-to-end, zero setup | Claude (David approved) |
