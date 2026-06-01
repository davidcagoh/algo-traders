# Decision 004 — Track A hedged mechanism pre-registered gate

**Status:** BINDING from 2026-05-20.
**Track:** A — hedged variant of trend_vol mechanism.
**Replaces gate `001` for this mechanism only. Gate `001` still binds for the unhedged v1.**

## What is being tested

Does adding a market-trend hedge to the low-vol mechanism produce a long-only SGX/IDX strategy whose drawdown is bounded by something tighter than raw market beta, while preserving the Sharpe observed in the 2026-05-20 sanity sweep (0.79 SGX, 0.52 IDX)?

Hedge construction:
- Broad-market proxy = equal-weighted basket of the universe close.
- 200-day rolling SMA of the proxy.
- Hedge state = `in` when proxy > SMA; `out` when proxy ≤ SMA.
- When `out`: target weights = 0 across the universe (go flat, hold cash).
- When `in`: follow the unhedged low-vol mechanism unchanged.

Hedge takes precedence over the mechanism's internal regime gate.

## Acknowledged design provenance

The hedged mechanism's *base* parameters (`top_n=5`, weekly rebalance on
SGX; `top_n=8`, monthly rebalance on IDX) are informed by the
2026-05-20 sanity sweep on the tuning window. This is tuning-window
contamination of the parameter choice. The *hedge layer itself* (200d
SMA on equal-weighted universe proxy) is novel and not informed by any
prior result in this project. The gate below is set on the assumption
that the base params are informed; the held-out evaluation tests the
hedge layer's contribution, not the base mechanism's selection.

The CPCV protocol (`decisions/003-cpcv-protocol.md`, to be written if
this gate passes) will properly re-tune base params on each market with
the hedge layer in place.

## Universe and data

Same as `001` — yfinance daily OHLC for STI 30 + SGX mid-caps (`.SI`)
and LQ45 (`.JK`). Equal-weighted basket built from the same retained
tickers per market.

## Tuning vs held-out split

- **Tuning window:** 2014-01-01 → 2022-12-31. Hedge parameter
  (`hedge_window=200`) is fixed and not tuned. Base params are sanity-
  sweep-informed.
- **Held-out window:** 2023-01-01 → 2026-04-30. SEALED. Opened only
  after the gate is applied to the tuning window result.

## Gate criteria (binding on held-out window)

Strategy graduates iff **all** of:

| Gate | Threshold | Rationale |
|---|---|---|
| L1 — held-out CAGR | > 3% | meaningful return floor, not just "positive" |
| L2 — held-out Sharpe | > 0.5 | same as v1 |
| L2 — held-out MDD | **< 20%** | tighter than v1's 25% because hedge is supposed to *reduce* drawdown; if it doesn't, the hedge isn't pulling its weight |
| L2 — held-out Calmar | > 0.5 | weaker than v1's 1.0 — long-only EM equity cannot realistically reach Calmar 1.0 even with hedge |
| L3 — independent trade count | N ≥ 50 per market | rebalances are sparser with weekly/monthly + hedge |
| L4 — DSR (kurtosis-conditional) | DSR ≥ 0.95 IF (excess kurt < 5 AND N > 250); else humility check only | unchanged carve-out |
| L5 — held-out Ulcer Index | < 12 | path-aware tail discipline |

## Tightening rationale vs v1

- **MDD 20% (was 25%):** v1 picked 25% arbitrarily; this gate sets a tighter threshold *because the hedge is the entire point of the v2*. If the hedge doesn't cut MDD below 20% on held-out, the hedge isn't earning its complexity.
- **Calmar 0.5 (was 1.0):** v1's 1.0 was unrealistic for long-only equity. 0.5 means "CAGR is at least half the MDD" — feasible for a working hedged equity strategy.
- **CAGR 3% (was 0%):** a hedge-trimmed strategy needs to clear inflation + opportunity cost, not just "positive."

## Hedge counterfactual reporting (informational, not gating)

For each held-out result, also report:
- Unhedged variant on same params (same base params, no hedge) — measures hedge's net contribution.
- Buy-and-hold equal-weighted universe — measures market beta.

If hedged MDD ≥ unhedged MDD, the hedge is mechanically broken; investigate before opening any further experiment on the same base.

## Retirement / kill rule (if it graduates)

To be written as `decisions/005-kill-track-a-hedged.md` only if this gate passes. Don't speculate.

## Reasons this gate could be wrong

- 200d SMA is a single hedge design; many alternatives (slope, Donchian, vol-target) might do better. Picking SMA is judgment, not optimisation.
- Equal-weighted universe proxy may diverge from STI / IDX / market reality. A cap-weighted index ETF (e.g. `EWS`, `EIDO`) would be a more honest market proxy but adds yfinance dependency.
- Held-out window 2023-2026 contains 2025's regime which (per backtesting subproject) was mild bear in crypto — equity regime may differ.
- The gate's MDD < 20% threshold is still a judgment call. Documented here as binding to prevent post-hoc fitting.

## Open before running

- Confirm equal-weighted-proxy SMA is computed forward-only (no look-ahead).
- Confirm hedge "go flat" implementation: target weights = 0 across all tickers on `out` days (not NaN).
- Confirm hedge transitions count as rebalances and incur the 10bp cost.
