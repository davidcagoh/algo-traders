# Decision 001 — Track A pre-registered gate (DRAFT)

**Status:** DRAFT — not yet binding. Finalise before any strategy code is written.
**Date drafted:** 2026-05-20
**Track:** A (SGX + IDX trend_vol mechanism port)

## What is being tested

Does the `trend_vol_v4` *mechanism* (regime-conditional vol/trend selection on an equity basket) produce statistically distinguishable alpha on SGX + IDX equities — a venue not used for tuning?

The mechanism is ported; the parameters are re-tuned on SGX+IDX data. This is a generalisation test of the methodology, not of feishu's tuned strategy.

## Universe and data

- **SGX:** STI 30 constituents + ~50 most-liquid mid-caps by ADV.
- **IDX:** LQ45 constituents.
- **Data source:** yfinance daily OHLC. Cached parquet under parked equity source (removed during cleanup).
- **Currency:** local (SGD for SGX, IDR for IDX). Per-market returns; no FX overlay in v1.
- **Calendar:** per-market trading days. No cross-market alignment in v1.

## Tuning vs held-out split (pre-registered)

- **Tuning window:** 2014-01-01 → 2022-12-31.
- **Held-out window:** 2023-01-01 → 2026-04-30. **Not opened until tuning complete.**
- No look-ahead allowed in feature construction. Vol/trend windows must use trailing-only data.

## Gate criteria (binding on held-out window)

Strategy graduates iff **all** of:

| Gate | Threshold | Source |
|---|---|---|
| L1 — held-out CAGR | > 0% | trivial floor |
| L2 — held-out Calmar | > 1.0 | risk-adjusted floor |
| L2 — held-out Sharpe | > 0.5 | secondary |
| L3 — independent trade count | N ≥ 100 per market | SQN validity |
| L4 — DSR (kurtosis-conditional) | DSR ≥ 0.95 IF (excess kurt < 5 AND N > 250); else humility check only | per `../learnings.md` DSR carve-out |
| L5 — held-out MDD | < 25% per market | tail discipline |
| L5 — held-out Ulcer Index | < 15 | chronic-drawdown check |
| L6 — MDB vs `trend_vol_v4` daily wallet | MDB > 0 under all three weightings (eq, rp, mv) | only meaningful if both strategies have positive standalone Sharpe |

L6 is informational in v1 (would require running `trend_vol_v4` on overlapping calendar). Defer if not feasible.

## Tuning protocol

- CPCV with 6 folds, embargo = 10 trading days.
- Tune hyperparameters on tuning window CPCV mean.
- Record number of configurations tested. Apply DSR with N_configs penalty.
- No re-tuning after held-out is opened.

## Retirement / kill rule (if it graduates)

Per `../methodology/kill-criteria.md`. To be drafted as `decisions/003-kill-track-a.md` only if the strategy passes this gate. Don't speculate.

## Reasons this gate could be wrong

- N per market may be too thin even on 12+ years (SGX has fewer cross-sectional opportunities than CSI300).
- yfinance data quality on SGX/IDX is uneven; corporate actions, delistings, and survivorship bias need an explicit audit before the gate is run.
- Currency: in v1 we treat per-market returns as the unit. A USD-investor view would need FX overlay and changes Sharpe materially.
- DSR carve-out: SGX+IDX daily returns may have higher kurtosis than feishu A-shares (fewer constituents, less-liquid mid-caps). DSR may again become humility-only.
- **FX-as-signal is deliberately deferred to v2.** Adding FX channels (regime filter via local-curr weakness, export/domestic cross-sectional sort) is a documented-alpha extension but conflates two hypotheses with v1's mechanism-generalisation test. v2 gate (`003-track-a-v2-fx.md`) will be written only after v1's held-out result is known, so v2 is properly conditioned on baseline.

## Open before finalising

- Confirm yfinance has clean adjusted-close history for SGX/IDX over the tuning window.
- Decide on survivorship-bias treatment (use point-in-time index constituents if obtainable, else document the bias).
- Decide on FX treatment for the "did this find alpha" interpretation.
