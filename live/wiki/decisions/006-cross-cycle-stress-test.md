# Decision 006 — Cross-cycle stress test for hedged mechanism

**Status:** BINDING from 2026-05-20.
**Track:** A.
**Mechanism under test:** SGX-frozen hedged trend_vol (`top_n=5`, weekly rebalance, `hedge_window=200`) — same code, same params as the SGX held-out binding result.

## What is being tested

The SGX held-out (2023–2026) was bull-regime. The hedge passed gate 004 but didn't demonstrate drawdown-protection contribution because there was no significant drawdown. This stress test asks the falsification question:

**On a market with a real bear regime, does the same hedge layer contribute its designed value — drawdown reduction with bounded return cost?**

If yes: the SGX pass becomes informative (the hedge passed both a "tradability bar" and a "contribution-under-stress" test).
If no: the SGX pass was a regime-lucky outcome and the strategy is parked pending a better hedge design.

## Methodology

- Run the *exact same* hedged mechanism unchanged on a new market with a known bear regime in the window.
- Compare hedged vs unhedged counterfactual.
- Apply pre-registered pass criteria below.

This is **not** a re-tuning. Params are frozen. Universe and venue are new.

## Test venues (pre-registered)

| Venue | Window | Why this venue / window | Status |
|---|---|---|---|
| **HSI (primary)** | 2014-01-01 → 2024-12-31 | Contains 2015 China credit shock, 2018 US-CN trade war, 2020 COVID, **2021-2023 sustained HK bear (~50% peak-to-trough)**. Asian market, retail-accessible to SG. | Run first. |
| FTSE 100 (secondary) | 2014-01-01 → 2024-12-31 | Contains 2015-2016 commodity selloff, Brexit, 2020 COVID, 2022 rate shock. Different macro driver from HSI. | Run **only if HSI gives ambiguous result** (e.g. hedge contributes but pass criteria narrowly miss). |

The "primary / secondary" structure prevents fishing across multiple venues for any one that passes. If HSI passes outright or fails outright, FTSE doesn't get run.

## Universe

- **HSI:** ~45 Hang Seng Index constituents on yfinance (`.HK` suffix). Best-effort current list with the same "drop on fetch failure" pattern as SGX/IDX.
- **FTSE 100:** ~50 large-caps on yfinance (`.L` suffix). Written only if HSI necessitates the run.

Survivorship bias acknowledged for both; consistent with `decisions/001` and `004`.

## Pass criteria (binding)

The hedge **vindicates cross-cycle** iff **all** of:

| Criterion | Threshold | Rationale |
|---|---|---|
| Hedge cuts MDD vs unhedged | ≥ 30% relative reduction | matches SGX tuning observation (34.5% → 11.1% = 68% reduction); 30% is the floor for "noticeable" |
| Hedged absolute MDD | < 25% | tradability floor; looser than gate 004 because cross-cycle markets may be harsher |
| Hedged Sharpe | ≥ 0.5 | same absolute Sharpe floor as gate 004 |
| Hedge CAGR cost | ≤ 60% of unhedged CAGR | if hedge eats more than 60% of return, it's "always on" rather than regime-conditional |
| Hedged excess kurt | < unhedged excess kurt | tail-cleansing check — hedge should make the distribution less fat |

## Fail modes interpreted

- **Hedge contributes but doesn't pass** (e.g., MDD reduction = 25%): hedge concept is right, design needs work. Mark for v2.
- **Hedge doesn't contribute** (MDD reduction < 15%, or hedged MDD ≥ unhedged MDD): SGX result was regime-lucky. Park the hedge mechanism. Methodology lesson stands.
- **Hedge over-contributes** (CAGR cost > 80% of unhedged): hedge is always-on rather than regime-conditional. Park.
- **Pass:** SGX result is vindicated. Proceed to `decisions/005` (kill rule) and paper-trade.

## Reasons this stress test could mislead

- Single venue (HSI) is N=1. Two venues passing would be stronger, but the primary/secondary structure deliberately trades stronger-evidence for less-fishing-risk.
- HSI 2014–2024 includes 4 distinct bear regimes; one of them (2021–2023 HK political bear) is unusual relative to typical equity bears (China-specific regulatory shock). Generalisability beyond HSI is not guaranteed.
- HK has different liquidity / dealing-cost structure from SGX; 10bp cost assumption may be optimistic.
- Hedge SMA on equal-weighted HSI basket may behave differently from HSI itself (cap-weighted). Equal-weighted is consistent with the SGX test by design.

## What this stress test does NOT do

- It does not re-tune any params. The SGX-frozen params stay.
- It does not provide an additional held-out window for SGX. SGX held-out was already used and is exhausted.
- It does not re-open gate 004. Gate 004 was applied; this is gate 006.

## Open before running

- Confirm HSI ticker list resolves on yfinance for ≥ 30 names with ≥ 252 obs in window.
- Confirm the same code path is used (no copy-pasted variant).
