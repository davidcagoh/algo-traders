# Implementation Plan: `evaluation` as a Reusable Evaluation Package

Package-first (see `STATUS.md`). Every phase below maps to a source in
`../literature/strategy-evaluation/_index.md`; cite it in code comments and
docstrings as each module is written.

**Status (2026-08-06): Phases 0-6 complete.** 150 tests, 96% coverage,
clean ruff/black/mypy. The DSR standalone fix (originally part of Phase 1 /
6.1) landed first — see `../wiki/decisions-archive.md` (2026-08-06 entry)
and `evaluation/dsr.py`. See `evaluation/README.md` for the module map,
worked example, and design notes. Not built: SPA/Reality Check (stretch
item, sources inaccessible) and real order-book capture (`stress.py`'s
`depth_from_ohlcv` remains an explicitly-labeled OHLCV proxy).

## Phase 0 — Package foundation (blocks everything)
- `pyproject.toml`: PEP 621 metadata, distribution name `algo-eval-stack`,
  import name stays `evaluation`. `requires-python>=3.11`. Core deps numpy/
  pandas/scipy. Extras: `freqtrade=[pyarrow]`, `factor=[statsmodels]`,
  `dev=[pytest, pytest-cov, ruff, black, mypy]`.
- `tests/conftest.py` + `tests/fixtures/`: seeded synthetic fixtures —
  gaussian wallet, fat-tailed (t-dist, excess kurt ≈6) wallet, trending
  wallet, noise trial matrix with known null, regime-switching returns.
- Characterisation tests for existing modules (`layers.py`, `dsr.py`,
  `correlation_mdb.py`, `backtest.py`) to pin current behavior before
  refactors land.
- CI: pytest + `--cov-fail-under=80`, ruff, black --check, mypy.
- Exit: `pip install -e ".[dev]"` works clean; pytest green; coverage ≥80%
  on existing modules.

## Phase 1 — Machine-readable trial ledger
Lit: Bailey & López de Prado 2014 (DSR needs real N and cross-trial
variance); Harvey/Liu/Zhu 2016 (multiple-testing thresholds scale with
total tests attempted); Jadouli 2026 (missing artifacts / post-hoc
promotion — an append-only ledger closes both); Chauhan 2026 (researcher-
menu correction → effective/clustered trial count).

- `evaluation/ledger.py`: frozen `TrialRecord` dataclass (id, timestamp,
  family, strategy, params, param_hash, dataset_id, split_id, cost_model_id,
  code_ref, status incl. `discarded`, sharpe, n_obs, returns_artifact,
  notes). `TrialLedger`: append-only JSONL, `scope()`, `n_trials()`,
  `sharpe_variance()`, `to_frame()`. Discarded trials still count toward
  `n_trials()`.
- `evaluation/ledger_schema.json` + validation on load.
- `effective_trials()`: correlation-cluster trials (avg-linkage on 1-|ρ|,
  default cut 0.9), report raw N and clustered N side by side. (Repo has a
  live example: HmmSmaSlope V1/V2/V3 pairwise Pearson 0.96–1.00 — one trial
  in three guises.)
- Rewire `evaluation/dsr.py::compute_dsr_table` to optionally pull
  `n_trials`/`sharpe_var` from a ledger via `compute_dsr_from_ledger()`
  (the required-kwarg fix already landed; this adds the ledger-backed path
  on top).
- Backfill a ledger for the HmmSmaSlope search from the ~40 dated result
  cards in `../freqtrade-experiment/hmm-slope-experiment/research/analysis/reports/`.
  Record unreconstructable trials explicitly — N is a floor, not a point
  estimate.
- Exit: DSR cannot be computed without an explicit, sourced trial count; a
  backfilled ledger exists for HmmSmaSlope with reconstruction gaps noted.

## Phase 2 — CSCV/PBO and block-bootstrap inference
Lit: Bailey/Borwein/López de Prado/Zhu 2017 (CSCV/PBO); Bysik & Ślepaczuk
2026 (block-bootstrap comparison + multiple-testing correction); Chauhan
2026 (dependent bootstrap/HAC); Oliveira/Guzman/Firoozye 2025 (select from
bootstrap quantiles, not the in-sample optimum); Jung 2026 (DSR + PBO/CSCV
+ slippage sensitivity as a combined stack).

- `evaluation/pbo.py`: `cscv_pbo()` — combinatorially symmetric CV over S
  blocks, IS-best trial's OOS rank → logit λ, `PBOResult` with pbo,
  performance-degradation slope, probability-of-loss, stochastic dominance.
  Test against known-null (PBO≈0.5) and known-edge (PBO≈0) synthetic
  matrices.
- `evaluation/bootstrap.py`: moving/circular/stationary block bootstrap +
  Politis-White optimal block length; `bootstrap_ci()`, `paired_bootstrap_test()`.
  Vectorised — must stay fast at 10k replicates.
- `metrics_with_ci()` wrapper so bootstrap CIs are the default rendering,
  not an opt-in extra.
- Stretch: `evaluation/spa.py` (Hansen SPA / White Reality Check) — both
  primary sources are record-only in the lit index, implement from the
  standard published algorithm and flag as unverified against original text.
- Re-run PBO/DSR on the backfilled HmmSmaSlope ledger; write results to a
  dated report card. This is the DSR-vs-PBO head-to-head the archived essay
  promised and never delivered.
- Exit: `cscv_pbo` returns ≈0.5 on a known null; every headline metric can
  carry a bootstrap CI.

## Phase 3 — Purged double-OOS splits and holdout sealing
Lit: Mroziewicz & Ślepaczuk 2026 (window lengths are hyperparameters →
second untouched final test); Bieganowski & Ślepaczuk 2026 (purged
walk-forward on crypto microstructure); Jadouli 2026 (reused dates,
unpurged horizons, same-close execution); Deep/Deep/Lamptey 2025 (sequential
folds, information-set discipline).

- `evaluation/splits.py`: `PurgedKFold`, `PurgedWalkForward` (anchored +
  rolling), `DoubleOOSSplit` (dev → oos1 → final, final touched once),
  `combinatorial_purged_splits()` feeding Phase 2's PBO from real splits.
- `evaluation/holdout.py`: `seal_holdout()` (append-only manifest, sha256
  of window spec), `guard()` (raises `HoldoutViolation` on any in-window
  timestamp), `break_seal()` (irreversible, logged reason, flips status).
  Every guard call — pass or fail — appends to an access log.
- Seal the existing 2026-06-01 → 2026-12-31 forward window immediately once
  `holdout.py` exists; add `guard()` calls to the HmmSmaSlope data-loading
  path. Don't wait for the rest of the phase.
- Tests: no train/test index intersection after purge; leakage-injection
  test (score inflates without purge, at-chance with purge); guard raises
  on a single overlapping timestamp; `break_seal` is not reversible.
- Exit: a purged double-OOS protocol is expressible in code; the final
  holdout can't be read without a logged, irreversible seal break.

## Phase 4 — Fee/slippage grids, funding, order-book stress
Lit: Bysik & Ślepaczuk 2026 (cost-aware trade filtering); Sepper 2026,
Slippage-at-Risk (forward-looking order-book slippage for perps);
Bieganowski & Ślepaczuk 2026 (fee sensitivity, maker/taker, flash-crash
stress — notes latency/queue position unmodeled); Chauhan 2026
(turnover-scaled costs); Fu 2025 survey (full costs, capacity, latency).

- `evaluation/costs.py`: frozen `CostModel` (maker/taker bps, slippage bps,
  funding series, borrow bps, min notional). `apply_costs()`, `turnover()`,
  `cost_drag_summary()`, `cost_grid()`, `breakeven_cost()`.
  **Funding must be modeled** — on the project's own numbers funding drag
  was 5.4× taker fees (-12.08 vs -2.25 USDC), 85% falling on the 7 winning
  trades. Note: Freqtrade silently ignores the config `"fee"` key — cost
  must be reconstructed post hoc from the trade ledger, not trusted from
  backtest config.
- `evaluation/stress.py`: `slippage_at_risk()` (Sepper 2026 shape),
  `depth_from_ohlcv()` fallback proxy (label clearly as upper-bound-quality,
  not real book data — no L2 data is retained anywhere in this repo today),
  `flash_crash_scenario()`, `capacity_curve()`.
- Exit: any strategy can be re-scored across a cost grid including funding,
  with a breakeven cost and capacity curve.

## Phase 5 — Benchmark/factor/regime decomposition + backtest-to-live report
Lit: Liu 2026 (pro-forma-to-live decay vs peer/external benchmark,
regime-conditioned haircut, 1,726 commercial strategies); Chauhan 2026
(factor diagnostics, HAC-delta inference); Pippas/Ludvig/Turkay 2025
survey (factor controls, survivorship bias, deployment realism); Jadouli
2026 (same evidence schema, retain negative outcomes).

- `evaluation/benchmark.py`: `buy_and_hold()`, `peer_benchmark()`,
  `excess_metrics()` (excess CAGR/Sharpe, information ratio, up/down
  capture).
- `evaluation/factors.py`: `factor_regression()` with HAC/Newey-West SEs;
  `crypto_factors()` helper (market/BTC, cross-sectional momentum, funding
  carry). `statsmodels` behind the `factor` extra, small numpy Newey-West
  fallback in core.
- `evaluation/regimes.py`: `label_regimes()` (drawdown/SMA/vol-tercile),
  `regime_metrics()`, `regime_stability()`.
- `evaluation/live.py`: `LiveRun` dataclass (deliberately a superset of
  what the 2026-08-05 run could produce, so gaps are visible), `reconcile()`
  → `ReconciliationReport` with a **three-valued verdict**: PASS / FAIL /
  INCOMPLETE (INCOMPLETE when a pre-registered minimum, e.g. trade count,
  wasn't reached — encodes the actual finding on the original 30-day
  HmmSmaSlopeV2 gate: incomplete, not a pass).
- `evaluation/live_schema.json`: minimum live-run artifact set (trade
  ledger, per-bar signal log, fill vs signal prices, funding payments,
  uptime samples, exception log) — prevents recurrence of "cannot be
  reconstructed from the retained trade mirror."
- Regression fixture: the real HmmSmaSlopeV2 backtest-vs-live pair as a
  permanent test asserting `reconcile()` returns INCOMPLETE for the
  original 2-trade/30-day gate and FAIL for the extended run.
- Exit: a strategy report includes benchmark excess, HAC factor alpha,
  per-regime metrics, and (where live data exists) a three-valued
  reconciliation verdict.

## Phase 6 — Documentation and API surface
- Re-examine any remaining DSR framing now that PBO exists (2.5's
  head-to-head result decides whether the N-only carve-out is final).
- `evaluation/README.md`: install instructions, full module map, an
  end-to-end worked example (ledger → splits → costs → metrics+CI → PBO →
  benchmark/factor/regime → live reconcile), and a table mapping every
  module to its literature source.
- `evaluation/__init__.py`: extend `__all__`; add a test asserting `__all__`
  matches actual exports.
- Cross-reference `../wiki/concepts/cv-and-deflation.md` and
  `../wiki/concepts/kill-criteria.md` to the new enforcement mechanisms
  (`evaluation.splits`, `evaluation.holdout`).
- If/when the archived manuscript resumes: start from `STATUS.md` and the
  current literature index, not from `archive/manuscript-2026-05/` — those
  files are stale by construction (see their README).

## Independently deliverable slices
| Slice | Ships |
|---|---|
| Phase 0 | installable, tested package |
| + Phase 1 | honest trial counts (DSR stops under-deflating) |
| + Phase 2 | PBO + bootstrap CIs |
| + Phase 3 | purge + sealed holdout |
| + Phase 4 | funding-aware cost grids |
| + Phase 5 | full report card incl. live reconciliation |
| + Phase 6 | reconciled docs, stable API surface |

## Key paths
- Package: `evaluation/`
- Ledger backfill source: `../freqtrade-experiment/hmm-slope-experiment/research/analysis/reports/`
- Downstream callers to migrate when ledger lands: `../freqtrade-experiment/hmm-slope-experiment/research/analysis/{dsr_analysis,eval_layers,run_correlation_mdb,combined_book_mdd,generate_pareto_chart}.py`
- Live evidence: `../freqtrade-experiment/hmm-slope-experiment/execution/records/results/2026-08-05-hl-paper-evaluation.md`
- Literature manifest: `../literature/strategy-evaluation/_index.md`
