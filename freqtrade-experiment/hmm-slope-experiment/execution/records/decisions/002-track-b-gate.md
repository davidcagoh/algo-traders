# Decision 002 — Track B pre-registered gate (BINDING)

**Status:** BINDING as of 2026-05-20. Open items resolved (see §Resolved below). Pass/fail criteria below are now locked; do not edit after dry-run starts.
**Date drafted:** 2026-05-20
**Date bound:** 2026-05-20
**Track:** B (Hyperliquid 30d dry-run of `HmmSmaSlopeV2`)

## What is being tested

Does `HmmSmaSlopeV2` (imported unchanged from `../../../research/`) behave during a 30-day live-market dry-run consistently with its backtest? This is an execution-realism test, not an alpha test. The backtest already shows the strategy passes the project's kill criteria but fails DSR; the dry-run does not change that.

## Strategy

- `HmmSmaSlopeV2` from `../../../research/strategies/`, imported unchanged.
- Universe: same as backtest multi-coin run (BTC, ETH, SOL, DOGE, AVAX, ARB).
- Timeframe: same as backtest.
- Position sizing: continuous slope-strength sizing per backtest implementation.
- Stake: per Freqtrade `dry_run_wallet` setting, $1000 simulated total, $200 per pair max.

## Run window (pre-registered)

- **Dry-run start:** TBD — set when Freqtrade harness is verified locally.
- **Dry-run duration:** 30 consecutive calendar days.
- **No code changes during the run.** Parameter or strategy edits invalidate the run; restart the 30d clock.

## Gate criteria (binding on dry-run window)

Strategy graduates to small-live capital iff **all** of:

| Gate | Threshold | Rationale |
|---|---|---|
| Uptime | bot heartbeat > 99% of 30d window | execution reliability prerequisite |
| Signal fidelity | dry-run trade entries match backtest entries on same OHLC ≥ 95% | Freqtrade harness consistency |
| Slippage realism | assumed slippage ≤ 2× modelled in backtest | check that backtest slippage model isn't optimistic |
| MDD | dry-run MDD < 8% (1.5× backtest bear-window MDD of 4.44%) | tail discipline |
| Trade count | ≥ 5 round-trip trades | minimum for any signal-level conclusion |
| Funding-rate impact | net funding paid as % of equity within ±50bps/30d of backtest assumption | regime check |
| No silent failures | zero unhandled exceptions in logs | operational |

If trade count < 5 in 30d, gate is **incomplete, not failed** — extend by 15d, but pre-register the extension before opening the result.

## What "graduate to live small" means

- $100–500 funded to a dedicated Hyperliquid API wallet (subaccount, no withdrawal rights).
- Same strategy, same code, same config.
- Same 30d clock, same gate criteria but recomputed on live fills.
- Live small run is its own decision; this document only governs the dry-run.

## Retirement / kill rule (already exists)

Per `../../../research/analysis/reports/2026-05-10-decision-004-kill-criteria-sma-regime-180.md` extended to V2. Continuous-shrinkage sizing already implemented. Hard-kill thresholds (MDD > 5.5%, six straight stops, rolling 365d return ≤ 0 for 30d) apply at all stages.

## Hosting requirements (for the gate to be evaluable)

- VPS with Docker, restart-on-crash policy.
- Telegram bot for alerts and remote `/stop`.
- healthchecks.io heartbeat (cron-style pings every 15 min).
- Logs persisted to disk + rotated. Optional: ship to Better Stack or Grafana Cloud free tier.

See `../../ops/` for the concrete setup.

## Reasons this gate could be wrong

- 30d is short. Even a passing dry-run is consistent with no real signal — it shows execution works, not that the strategy is profitable in expectation.
- Bull/bear regime during the 30d window will dominate the result. Note the regime at start; do not over-interpret.
- Freqtrade's Hyperliquid adapter is younger than its CEX adapters; bugs in the adapter could cause signal-fidelity failures unrelated to the strategy.
- Funding-rate behaviour is path-dependent; 30d may not see a representative funding regime.

## Resolved (open items closed before binding)

- **Freqtrade adapter pin:** originally specified as an in-repo editable checkout that is no longer retained (version `2026.4-dev`, commit `9d0fb9b0257dad05f19c153d624f74e0ac931647`). **Revised 2026-05-21 during VPS bring-up:** that build path landed on Python 3.14.3 inside the container, for which no `hmmlearn` wheel existed. The deployment switched to the upstream `freqtradeorg/freqtrade:stable` image (Python 3.12, prebuilt dependencies) plus a thin extension image adding `hmmlearn`. The binding requirement — "no version changes during the run" — was preserved by pinning the image digest when the clock started.
- **Dry-run wallet size:** $1000 simulated, $200 per-pair max stake (matches `../../../research/configs/config_hl_multi.json`). Rationale: keeps dry-run trade economics directly comparable to the backtest the gate is checking against. Larger wallets are out of scope for this gate; if needed later, restart the clock.
- **Mainnet vs testnet:** **mainnet prices, `dry_run=true`**. Freqtrade's dry-run observes real order books and simulates fills locally — that is the execution-realism signal we want. Hyperliquid testnet has thin liquidity and unrepresentative order books, which would break the slippage-realism gate.
