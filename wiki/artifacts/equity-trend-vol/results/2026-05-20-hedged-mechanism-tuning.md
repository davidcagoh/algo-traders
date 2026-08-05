# 2026-05-20 — Hedged mechanism tuning-window evaluation

**Track:** A
**Mechanism:** trend_vol low-vol + market-trend hedge (200d SMA on equal-weighted universe proxy). Pre-registered in [`decisions/004-track-a-hedged-mechanism.md`](../decisions/004-track-a-hedged-mechanism.md).
**Window:** 2014-01-01 → 2022-12-31 (tuning).
**Held-out 2023-2026:** SEALED.

## Result table

| Market | Variant | CAGR | Sharpe | Calmar | MDD | Ulcer | Kurt | Rebals |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| SGX | buy&hold (market beta) | +10.46% | 0.93 | 0.33 | 31.7% | 5.85 | +19.3 | 1 |
| SGX | unhedged (top5_weekly) | +8.69% | 0.79 | 0.25 | 34.5% | 7.20 | +24.9 | 364 |
| **SGX** | **hedged (top5_weekly, hedge200)** | **+7.92%** | **1.20** | **0.71** | **11.1%** | **4.00** | **+7.9** | 256 |
| IDX | buy&hold (market beta) | +14.70% | 0.78 | 0.30 | 48.6% | 10.45 | +9.7 | 1 |
| IDX | unhedged (top8_monthly) | +8.16% | 0.52 | 0.18 | 46.4% | 9.76 | +18.6 | 102 |
| IDX | hedged (top8_monthly, hedge200) | +4.57% | 0.46 | 0.23 | 20.2% | 8.73 | +7.9 | 75 |

## Hedge contribution (counterfactual)

| Market | MDD reduction | Sharpe Δ | CAGR cost | Kurt reduction |
|---|---:|---:|---:|---:|
| SGX | 34.5% → 11.1% (-68%) | +0.41 (+52%) | -0.77pp | +24.9 → +7.9 |
| IDX | 46.4% → 20.2% (-56%) | -0.06 (-12%) | -3.59pp | +18.6 → +7.9 |

The hedge is doing massive work on SGX — cutting MDD by two-thirds, lifting Sharpe by half, and pruning fat tails — at the cost of less than 1pp of CAGR. On IDX it cuts MDD by more than half but pays a much steeper CAGR cost and slightly degrades Sharpe.

## Gate 004 application (tuning window only — INFORMATIONAL)

| Gate criterion | SGX hedged | IDX hedged |
|---|---|---|
| CAGR > 3% | 7.92% ✓ | 4.57% ✓ |
| Sharpe > 0.5 | 1.20 ✓ | 0.46 ✗ (-0.04) |
| MDD < 20% | 11.1% ✓ | 20.2% ✗ (+0.2pp) |
| Calmar > 0.5 | 0.71 ✓ | 0.23 ✗ |
| Ulcer < 12 | 4.00 ✓ | 8.73 ✓ |
| Tuning pass | **YES** | **NO** |

**SGX hedged passes all five gating layers on tuning.** IDX hedged fails three of five (Sharpe, MDD, Calmar) — narrowly on MDD (0.2pp over).

This is the **first candidate in the project** to pass a non-trivial pre-registered gate on tuning data for any equity venue.

Reminder: the gate is binding on **held-out**, not on tuning. The tuning-window result is informational. Per pre-reg discipline, the held-out evaluation is the next step regardless of tuning pass/fail.

## Honest qualifications

1. **Base params (`top_n`, rebalance period) were chosen via the 2026-05-20 sanity sweep on tuning data.** This is acknowledged in `decisions/004`. The hedge layer itself (200d SMA on equal-weighted proxy) is novel, but the strategy as a whole is tuning-informed at the parameter level. The held-out test measures the *hedge's contribution* with reasonable confidence, but the *mechanism's parameters* are not fully out-of-sample. CPCV with full hedge inclusion is the proper response (next experiment).
2. **Universe is current-as-of-2026 STI/LQ45 constituents.** Survivorship bias in the long direction; absent delistings would have dragged returns down. Most relevant during 2015–2016 (commodity-cycle delistings in SGX) and 2018 (IDX state-owned enterprise reshuffles).
3. **Equal-weighted broad-market proxy may diverge from a real index ETF.** EWS (iShares MSCI Singapore) or STI ETF would be the cap-weighted standard. v2 hedge would test cap-weighted proxy.
4. **The IDX failure is honest signal.** IDX has more concentrated banking-sector risk and the SMA on equal-weighted basket is slow to react to bank-led drawdowns. A sector-aware hedge would be the natural extension but is out of scope for v1.
5. **Kurtosis dropped to 7.9 on both markets.** That's close to the DSR-binding threshold of 5 but still over. DSR would remain humility-only on held-out unless kurt drops below 5 there.

## Next step per protocol

Open the held-out window for SGX hedged (top5_weekly, hedge_window=200). Apply gate 004 verbatim. Result is binding. One shot.

For IDX hedged: the tuning gate failed; per the pre-reg, IDX hedged does *not* graduate to held-out evaluation for binding purposes. It can still be run for informational counterfactual but must not be promoted to "paper-trade candidate" regardless of held-out outcome.

## Files

- Pre-reg gate: [`../decisions/004-track-a-hedged-mechanism.md`](../decisions/004-track-a-hedged-mechanism.md)
- Strategy code: parked equity source (removed during cleanup) (added `hedged_weights`)
- Prior baseline: [`2026-05-20-sgx-idx-baseline.md`](2026-05-20-sgx-idx-baseline.md)
- Prior sanity sweep: [`2026-05-20-sanity-sweep.md`](2026-05-20-sanity-sweep.md)
