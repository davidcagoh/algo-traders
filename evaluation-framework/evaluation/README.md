# evaluation/

Reusable trading-strategy evaluation stack: layered metrics, honest
multiple-testing deflation (DSR + PBO/CSCV), leakage-safe splits, a sealed
holdout mechanism, cost/slippage modeling, and benchmark/factor/regime
decomposition through to backtest-to-live reconciliation. Package-first;
see `../STATUS.md` and `../PLAN.md` for priority and build history.

## Install

```bash
pip install -e ".[dev,freqtrade,factor]"   # from evaluation-framework/
pytest --cov=evaluation --cov-fail-under=80
```

Extras: `freqtrade` (pyarrow, for `.feather` ZIP reading), `factor`
(statsmodels; the package's own Newey-West fallback works without it),
`dev` (pytest, ruff, black, mypy).

## Module map

| Module | Purpose | Literature |
|---|---|---|
| `layers.py` | L1-L3, L5 metrics (CAGR, Sharpe, Calmar, SQN, skew/kurtosis, CVaR, Ulcer, Martin, Pain) + `compute()` aggregator | — (foundational, cross-project) |
| `dsr.py` | L4 Deflated Sharpe Ratio, corrected 2026-08-06 to require an explicit trial count and to drop the double-counting kurtosis carve-out | Bailey & López de Prado 2014 |
| `correlation_mdb.py` | L6 correlation + Marginal Diversification Benefit under eq/rp/mv weighting | — (cross-project) |
| `backtest.py` | Freqtrade backtest ZIP readers (wallet curve, trade returns) | — |
| `ledger.py` | Append-only trial ledger — the real search size DSR/PBO need, including discarded trials; `effective_trials()` clusters near-duplicate trials | Bailey & López de Prado 2014; Harvey/Liu/Zhu 2016; Jadouli 2026; Chauhan 2026 (SSRN 6861958) |
| `pbo.py` | Probability of Backtest Overfitting via CSCV — a deflator that doesn't share DSR's Cornish-Fisher approximation | Bailey/Borwein/López de Prado/Zhu 2017 |
| `spa.py` | Hansen's Test for Superior Predictive Ability (studentized, data-dependent null) plus White's Reality Check for comparison, both via stationary bootstrap | White 2000; Hansen 2005 |
| `bootstrap.py` | Block-bootstrap (moving/circular/stationary) CIs and paired tests for serially-dependent returns | Politis-Romano; Bysik & Ślepaczuk 2026; Chauhan 2026; Oliveira/Guzman/Firoozye 2025 |
| `intervals.py` | `metrics_with_ci()` — bootstrap CI as the default rendering, not opt-in | (wraps `bootstrap.py`) |
| `splits.py` | Purged K-fold, purged walk-forward, double-OOS split, combinatorial purged splits (CPCV) | Mroziewicz & Ślepaczuk 2026; Bieganowski & Ślepaczuk 2026; Jadouli 2026; Deep/Deep/Lamptey 2025 |
| `holdout.py` | Mechanically-enforced holdout sealing (`seal_holdout`/`guard`/`break_seal`) — makes peeking a logged, irreversible act instead of a memory-only rule | (enforcement layer for the splits.py corpus) |
| `costs.py` | Fee/slippage/funding cost model, cost grids, breakeven cost. Funding-aware — a cost model without it was wrong by 5.4x on this project's own live venue | Bysik & Ślepaczuk 2026; Chauhan 2026; Fu 2025 |
| `stress.py` | Order-book slippage stress (OHLCV-derived proxy, clearly labeled) and capacity curves | Sepper 2026; Bieganowski & Ślepaczuk 2026 |
| `benchmark.py` | Buy-and-hold / peer benchmark, excess return/Sharpe, information ratio, up/down capture | Liu 2026 |
| `factors.py` | Factor regression with HAC (Newey-West) standard errors | Chauhan 2026; Pippas/Ludvig/Turkay 2025 |
| `regimes.py` | Regime labeling (drawdown/SMA/vol-tercile) + per-regime metric decomposition | Liu 2026 |
| `live.py` | Backtest-to-live reconciliation with a three-valued verdict (PASS/FAIL/**INCOMPLETE**) | Liu 2026; Jadouli 2026 |

Every citation above resolves to an entry in
[`../literature/strategy-evaluation/_index.md`](../literature/strategy-evaluation/_index.md).

## Worked example: ledger → splits → costs → metrics+CI → PBO/SPA → benchmark/factor/regime → live reconcile

```python
import pandas as pd
from evaluation import (
    TrialLedger, TrialRecord,
    PurgedWalkForward,
    CostModel, apply_costs,
    metrics_with_ci, CRYPTO_ANNUAL,
    cscv_pbo,
    spa_test,
    buy_and_hold, excess_metrics,
    factor_regression,
    label_regimes, regime_metrics,
    LiveRun, reconcile,
)

# 1. Record every trial you run, including discarded ones.
ledger = TrialLedger("trials.jsonl")
ledger.append(TrialRecord(
    trial_id="run-001", created_at="2026-08-06T00:00:00Z",
    family="MyStrategy", strategy="MyStrategyV1",
    params={"sma_period": 180}, dataset_id="binance-bull-2023-2025",
    split_id="full", status="completed", sharpe=0.9, n_obs=792,
))

# 2. Split with purge + embargo, not a naive train/test cut.
wf = PurgedWalkForward(train_span=180, test_span=30, embargo=5, label_horizon=3)
for fold in wf.split(wallet):
    ...  # fold.train_idx, fold.test_idx never overlap or leak

# 3. Price trades with a funding-aware cost model before trusting P&L.
model = CostModel(model_id="hl-taker", taker_bps=3.5, funding_series=funding)
priced_trades = apply_costs(trades, model)

# 4. Report every headline metric with a bootstrap interval, not a bare point estimate.
metrics, cis = metrics_with_ci(wallet, annualisation=CRYPTO_ANNUAL)

# 5. Deflate with DSR (evaluation.dsr), PBO, and SPA — PBO doesn't inherit
#    DSR's fat-tail sensitivity, and SPA is a direct beat-the-benchmark test
#    rather than a deflator, so read all three rather than trusting one.
pbo_result = cscv_pbo(trial_returns_matrix, n_splits=8)
spa_result = spa_test(trial_returns_matrix, benchmark_returns)

# 6. Compare against a benchmark, not just zero return.
excess = excess_metrics(wallet, buy_and_hold(prices))

# 7. Check whether the "edge" is just market beta.
factor_result = factor_regression(strategy_returns, factors_df)

# 8. Decompose by regime so one bull run can't carry the whole track record.
labels = label_regimes(benchmark_prices, method="drawdown")
by_regime = regime_metrics(wallet, labels)

# 9. When live data exists, reconcile with a three-valued verdict.
live = LiveRun(
    window_start="2026-05-21", window_end="2026-06-20",
    n_trades=2, min_trades_required=5, realized_return_pct=-0.09,
)
report = reconcile(metrics, live)
assert report.verdict == "INCOMPLETE"  # 2 trades < the pre-registered 5
```

## Sealed holdouts

```python
from evaluation import seal_holdout, guard, break_seal

seal_holdout("my-forward-window", "2026-06-01", "2026-12-31", "seals.jsonl")
guard(new_data, "my-forward-window", "seals.jsonl")  # raises if new_data touches the window
```

`break_seal()` is the only way past a `guard()` raise, is irreversible, and
requires a logged reason and decision reference.

## Design notes

- **DSR requires an explicit `n_trials`** — no default derives it from
  `len(wallets)`. Pass the real search size (a `TrialLedger` scope is the
  intended source via `compute_dsr_from_ledger`), not just the survivors.
- **A narrow, correlated candidate family understates `sharpe_var`** and
  inflates DSR — the mirror-image of the `n_trials` bug. Pass an explicit
  `sharpe_var` (e.g. from a wider ledger scope) when scoring a family of
  near-duplicate parameter variants; see `dsr.py`'s docstring and
  `freqtrade-experiment/hmm-slope-experiment/research/analysis/pbo_vs_dsr.py`
  for a worked example of both bugs and their fix.
- **`is_dsr_binding()` no longer demotes DSR under high kurtosis** — the
  DSR formula already absorbs skew/kurtosis by construction; a separate
  kurtosis carve-out double-counted the correction and is what let a
  DSR=0.000 strategy reach paper trading. See
  `../wiki/decisions-archive.md` (2026-08-06).
- **`reconcile()`'s INCOMPLETE verdict is not FAIL.** A pre-registered gate
  that didn't collect enough trades is missing evidence, not evidence of
  failure — collapsing the two loses information a later decision might need.

## Not yet built

See `../PLAN.md` for what's done vs. pending. Notably absent: SPA/Reality
Check (`pbo.py`'s marked stretch item — both primary sources are
paywalled/inaccessible per the literature index, so any implementation
would be unverified against the original text), and real order-book data
(`stress.py`'s `depth_from_ohlcv` is an explicitly-labeled proxy; no L2
snapshot capture exists anywhere in this repository yet).
