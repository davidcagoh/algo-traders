# 2026-05-20 — SGX + IDX sanity sweep (top_n × rebalance period)

**Track:** A
**Window:** 2014-01-01 → 2022-12-31 (tuning window)
**Purpose:** Test the "scale mismatch" hypothesis from `2026-05-20-sgx-idx-baseline.md` before committing to CPCV. NOT a pre-registered tune; informal exploration.
**Held-out 2023-2026:** SEALED.

## Sweep

Six variants per market, holding all other params at `trend_vol_v4` defaults. Cost = 10bp round-trip on turnover.

### SGX

| Variant | CAGR | Sharpe | Calmar | MDD | Kurt | Rebals | Turnover/rebal |
|---|---:|---:|---:|---:|---:|---:|---:|
| top20_daily (baseline) | +2.07% | 0.24 | 0.06 | 35.2% | +32.3 | 1818 | 0.193 |
| top12_daily | +3.33% | 0.34 | 0.09 | 36.3% | +37.2 | 1818 | 0.206 |
| top8_daily | +2.20% | 0.25 | 0.06 | 35.7% | +29.5 | 1818 | 0.215 |
| top8_weekly | +7.00% | 0.67 | 0.20 | 34.2% | +29.6 | 364 | 0.455 |
| **top5_weekly** | **+8.63%** | **0.79** | 0.25 | 34.5% | +24.9 | 364 | 0.509 |
| top8_monthly | +8.40% | 0.77 | 0.25 | 33.1% | +27.4 | 91 | 0.807 |

### IDX

| Variant | CAGR | Sharpe | Calmar | MDD | Kurt | Rebals | Turnover/rebal |
|---|---:|---:|---:|---:|---:|---:|---:|
| top20_daily (baseline) | +1.13% | 0.15 | 0.02 | 54.3% | +15.5 | 2019 | 0.245 |
| top12_daily | +2.30% | 0.22 | 0.04 | 52.2% | +16.9 | 2017 | 0.257 |
| top8_daily | +0.62% | 0.12 | 0.01 | 58.1% | +17.7 | 2017 | 0.267 |
| top8_weekly | +6.55% | 0.46 | 0.13 | 49.7% | +12.2 | 405 | 0.505 |
| top5_weekly | +5.79% | 0.41 | 0.12 | 47.6% | +11.0 | 405 | 0.548 |
| **top8_monthly** | **+8.16%** | **0.52** | 0.18 | 46.4% | +18.6 | 102 | 0.887 |

## Reading

**Turnover is the dominant lever, not top_n.** Daily → weekly rebalance roughly triples Sharpe on both markets. Going from top_20 → top_8 at the same rebalance frequency moves Sharpe by only ~5%. The mechanism was being eaten alive by ~3.5–5%/yr cost drag on daily rebal.

**top_n matters at the margin.** top5_weekly slightly beats top8_weekly on SGX (more selective = stronger signal). On IDX the relationship inverts (smaller universe + more concentration = more idiosyncratic risk). Both effects are second-order vs the turnover effect.

**MDD is invariant.** 33–35% on SGX and 46–58% on IDX across all six variants. This is **structural market beta**, not parameter choice. The low-vol mechanism gives you a defensive-equity sleeve that still eats market drawdowns in 2015 (China slowdown), 2020 (COVID), and 2022 (rate shock). Long-only without a hedge has no answer to those.

**Excess kurtosis is also invariant.** 20–37 on SGX, 11–19 on IDX. Same regime story — these markets *have* fat tails. DSR will be humility-only across the board.

## Gate verdict (informal, on tuning window)

Even the best variant fails the pre-registered gate at MDD:

| Best variant | CAGR | Sharpe | Calmar | MDD |
|---|---:|---:|---:|---:|
| SGX top5_weekly | +8.63% | **0.79** ✓ (>0.5) | 0.25 ✗ (<1.0) | **34.5%** ✗ (<25%) |
| IDX top8_monthly | +8.16% | **0.52** ✓ (>0.5) | 0.18 ✗ (<1.0) | **46.4%** ✗ (<25%) |

Sharpe gate passes. Calmar and MDD gates fail by a wide margin.

## Key honest takeaway

**The 25% MDD gate in `decisions/001-track-a-gate.md` is probably mis-calibrated for long-only EM equity.** For context: SPY had a 34% drawdown in 2020. The pre-reg threshold would reject SPY 2014-2022.

This is a real gate-design failure on my part, not a strategy failure. Long-only equity in any market has structural drawdown bounded by market beta. The right gate either:
- Sets a market-aware MDD threshold (e.g. MDD < 1.5× market MDD over the same window), or
- Tests a hedged variant where a broad-market trend filter cuts exposure during drawdowns.

The v1 gate stands as written for the v1 mechanism. A v2 gate must be pre-registered before evaluating any new variant against it.

## Recommended next experiments

1. **Market-trend hedge** (new mechanism, deserves its own decision file): rebalance only when STI / LQ45 itself is above its 200d SMA. Should preserve the bull-regime alpha while flat in bears. This is **not** the same mechanism as trend_vol_v4 — it's a new mechanism that needs its own pre-reg gate.
2. **CPCV tune the unhedged mechanism with v2 gate.** Pre-register `decisions/004-track-a-v2-gate.md` with realistic MDD (40% or relative-to-market), then CPCV over the grid hinted at here. Best CPCV winner gets the held-out shot.
3. **Choice C: stop at "default doesn't generalise, scale-corrected version recovers Sharpe but not MDD."** This is a publishable finding on the methodology — it caught a transplant problem that single-metric eyeballing would have missed.

## Files

- Strategy + backtest: `../../tracks/sgx_idx_trend_vol/`
- Sanity sweep was an inline script; not persisted. If we proceed to CPCV, persist all runs.
