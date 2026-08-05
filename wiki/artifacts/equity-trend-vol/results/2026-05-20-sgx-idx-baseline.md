# 2026-05-20 — SGX + IDX trend_vol_v4 baseline (default params)

**Track:** A (mechanism port)
**Window:** 2014-01-01 → 2022-12-31 (tuning window, pre-registered per `decisions/001-track-a-gate.md`)
**Params:** `TrendVolParams()` defaults, identical to feishu's `trend_vol_v4`
**Held-out 2023-2026:** SEALED.

## Result

### SGX (48 tickers retained from 50-name universe)

| Layer | Metric | Value | Gate (held-out) | Tuning observed |
|---|---|---:|---|---|
| — | Selection coverage | 80.4% | — | OK |
| — | Regime gate fires | 18.1% | — | OK (5–25% expected) |
| — | Rebalances | 1818 / 2262 days | — | extremely high churn |
| — | Avg turnover/rebalance | 19.3% | — | high |
| L1 | CAGR | **+2.08%** | > 0% | pass (barely) |
| L2 | Sharpe | **0.240** | > 0.5 | **FAIL** |
| L2 | Calmar | **0.06** | > 1.0 | **FAIL** |
| L2 | MDD | **35.23%** | < 25% | **FAIL** |
| L3 | SQN | 0.72 | — | low |
| L4 | DSR | 1.000 (NOT BINDING) | ≥ 0.95 if binding | humility check only |
| L5 | Skew | -1.23 | — | left-tailed |
| L5 | Excess kurt | **+32.32** | < 5 for DSR binding | fat-tailed |
| L5 | Ulcer | 11.00 | — | high |
| L5 | CVaR-5% | -1.67% | — | — |

### IDX (44 tickers retained from 45-name universe)

| Layer | Metric | Value | Gate (held-out) | Tuning observed |
|---|---|---:|---|---|
| — | Selection coverage | 90.3% | — | OK |
| — | Regime gate fires | 8.1% | — | OK |
| — | Rebalances | 2019 / 2243 days | — | extremely high churn |
| — | Avg turnover/rebalance | 24.5% | — | very high |
| L1 | CAGR | **+1.11%** | > 0% | pass (marginal) |
| L2 | Sharpe | **0.152** | > 0.5 | **FAIL** |
| L2 | Calmar | **0.02** | > 1.0 | **FAIL** |
| L2 | MDD | **54.19%** | < 25% | **FAIL** |
| L3 | SQN | 0.46 | — | very low |
| L4 | DSR | 1.000 (NOT BINDING) | ≥ 0.95 if binding | humility check only |
| L5 | Skew | +0.30 | — | near-symmetric |
| L5 | Excess kurt | **+15.51** | < 5 for DSR binding | fat-tailed |
| L5 | Ulcer | 17.24 | — | very high |
| L5 | CVaR-5% | -2.80% | — | bad |

## Honest reading

**Default params fail the pre-registered gate on both markets** at multiple layers (Sharpe, Calmar, MDD). The DSR shows "SIGNAL" by raw value but its binding-criterion is violated (excess kurt 15–32, well above the 5 threshold), so it is humility-only per the cross-project carve-out — this is exactly the regime the carve-out was designed for.

Per pre-registration discipline, this result is not adjustable. Default-param trend_vol_v4 **does not generalise** to SGX or IDX with default parameters and a 10bp retail cost assumption.

## Likely mechanism (hypotheses for v2 / CPCV tuning)

1. **`top_n` is structurally wrong for small universes.** feishu picked top-20 out of 2270 stocks (≈0.9% selectivity). Here we pick top-20 out of 48-50 (≈40%). That's near-market exposure with a vol-weighted tilt — the low-vol cross-section signal is diluted to noise. Plausibly `top_n` should be 5–10 (10–20% selectivity).
2. **Turnover is eating the strategy.** 1800+ rebalances at 20%+ turnover × 10bp = ~3.5–5%/yr drag, comparable to gross return. Rebalance-frequency reduction (rebalance weekly not daily, or rebalance only on signal change > ε) is a candidate axis.
3. **Trend threshold may be miscalibrated.** -2.5% over 35d was tuned for A-share volatility. SGX/IDX vol distributions differ; the threshold may admit too many falling-knife names.
4. **Regime gate may be miscalibrated.** Firing 8–18% is within the methodology expectation, but the `sigma_threshold=2.0` and `regime_window=30` are A-share-tuned and may need recalibration for SGX/IDX vol structure.

## What this DOESN'T mean

- It does not mean the methodology is wrong. The methodology pre-registered a gate and the gate is doing its job.
- It does not mean trend_vol_v4 itself is wrong on A-shares — different market, different microstructure, different result.
- It does not invalidate the held-out window for v1. The v1 result (with these defaults) stands; CPCV-tuned v2 is a separate experiment with its own gate.

## Next step

CPCV tuning (`tune.py`, task 8) on:
- `top_n` ∈ {5, 8, 12, 20}
- `rebalance_period` ∈ {1 day, 5 days, 20 days}  (requires new param)
- `trend_threshold` ∈ {-0.05, -0.025, -0.01, 0.0}
- `sigma_threshold` ∈ {1.5, 2.0, 3.0}

Pre-register the CPCV protocol (`decisions/003-cpcv-protocol.md`) before running. Six folds, 10-day embargo, evaluate on tuning-window CPCV mean. Held-out 2023-2026 stays sealed until tuning is locked.

## Files

- Raw wallet curves: not yet persisted (smoke-test script only). Persist in `tune.py` runs.
- Strategy code: parked equity source (removed during cleanup)
- Backtest harness: parked equity source (removed during cleanup)
- Eval stack: `../../eval/`
