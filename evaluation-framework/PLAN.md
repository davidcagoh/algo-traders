# Implementation Plan: `evaluation` as a Reusable Evaluation Package

Package-first (see `STATUS.md`). Every phase below maps to a source in
`../literature/strategy-evaluation/_index.md`; cite it in code comments and
docstrings as each module is written.

**Status (2026-08-06): Phases 0-7 complete.** 162 tests, clean
ruff/black/mypy. The DSR standalone fix (originally part of Phase 1 / 6.1)
landed first — see `../wiki/decisions-archive.md` (2026-08-06 entry) and
`evaluation/dsr.py`. See `evaluation/README.md` for the module map, worked
example, and design notes. Phase 7 (SPA/Reality Check) closed the one
remaining stretch item once its blocking sources (White 2000, Hansen 2005
— TLS failure / paywall) were acquired directly and read in full. Not
built: real order-book capture (`stress.py`'s `depth_from_ohlcv` remains an
explicitly-labeled OHLCV proxy) — this was never blocked on source access,
just out of scope for the original 6 phases.

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

## Phase 7 — SPA / Reality Check (closes the Phase 2 stretch item) — done 2026-08-06
Lit: White 2000, *A Reality Check for Data Snooping*
(`../literature/strategy-evaluation/foundational/white-reality-check-data-snooping.pdf`,
read in full 2026-08-06); Hansen 2005, *A Test for Superior Predictive
Ability* (`../literature/strategy-evaluation/foundational/hansen-test-superior-predictive-ability.pdf`,
read in full 2026-08-06). Both were previously "record only" (TLS download
failure / paywalled) — see `../literature/strategy-evaluation/_index.md`.
Acquired directly by the user and relocated into the literature tree; now
readable, so the stretch item is unblocked. Hansen's SPA is a strict
power improvement on White's RC (studentized statistic + data-dependent
null vs. the LFC-based null) — see Hansen §2.4 and Table 2-4 Monte Carlo
results (~15%→53% power in the paper's worked example). Build SPA as the
primary test; RC falls out for free since it reuses the same bootstrap
resampling, just unstudentized with `μ=0`.

- `evaluation/spa.py`:
  - `SPAResult` frozen dataclass: `p_value_liberal`, `p_value_consistent`,
    `p_value_upper` (Hansen's `μ̂ˡ/μ̂ᶜ/μ̂ᵘ` three-null-variant p-values),
    `t_stat_best`, `best_trial`, `n_trials`, `n_boot`, `rc_p_value`
    (White's unstudentized RC p-value, for comparison).
  - `spa_test(trial_returns: pd.DataFrame, benchmark: pd.Series, n_boot=10_000, block_len=None, seed=None) -> SPAResult`.
    Same `(T periods x N trials)` input shape as `pbo.py::cscv_pbo`, so it
    slots into the same call sites. Per-trial relative performance
    `d_{k,t} = L(benchmark_t) - L(trial_k,t)` (Hansen Table 1 notation);
    default loss `L = -returns` (i.e. compare mean returns) to match the
    project's existing Sharpe-style metrics, but accept a `loss` callable
    for MSE/other criteria per Hansen Examples 2.1-2.3.
  - Studentized statistic `T^SPA_k = max(n^0.5 * d̄_k / ω̂_k, 0)` (Hansen
    p.368). `ω̂_k` from the same block-bootstrap population-variance
    estimator already implemented for `bootstrap.py`'s block-length
    logic — reuse `_stationary_bootstrap_indices`, do not reimplement
    resampling.
  - Three recentering estimators per Hansen §2.4 p.368-371:
    `μ̂ˡ_k = min(d̄_k, 0)` (liberal = RC), `μ̂ᶜ_k = d̄_k * 1[n^0.5 d̄_k/ω̂_k <= -sqrt(2*log(log(n)))]`
    (consistent, Hansen's recommended default), `μ̂ᵘ_k = 0` (upper = old
    LFC/RC null). Bootstrap p-value construction mirrors
    `bootstrap.py::paired_bootstrap_test`'s resampling pattern, applied to
    the max-statistic instead of a pairwise difference.
  - `format_spa_table(result: SPAResult, label: str = "") -> str`, same
    convention as `pbo.py::format_pbo_table`.
- `bootstrap.py::stationary_bootstrap_indices` — de-privatized (was
  `_stationary_bootstrap_indices`) so `spa.py` reuses the resampling
  scheme instead of reimplementing it. Existing call sites updated.
- `tests/test_spa.py`, mirroring `tests/test_pbo.py`'s structure — 7
  tests: known-null (p_value_consistent > 0.05 against a zero benchmark),
  known-edge (p_value_consistent < 0.1, correct best_trial), SPA-more-
  powerful-than-RC on the known-edge fixture (`p_value_consistent <=
  rc_p_value`, reproducing the paper's headline claim), p-value ordering
  (`liberal <= consistent <= upper`, per Hansen's `μ̂ˡ ≤ μ̂ᶜ ≤ μ̂ᵘ`),
  mismatched-index guard, too-few-observations guard, and table
  formatting. **Correction to the original plan**: a
  `test_spa_p_liberal_matches_reality_check` test was planned on the
  premise that `μ̂ˡ` "is by construction the RC's null" — that's wrong.
  `μ̂ᵘ=0` is the RC-equivalent *null philosophy* (both assume every model's
  population mean is exactly 0), but literal RC is unstudentized while all
  three SPA variants (`l`/`c`/`u`) are studentized, so `p_value_upper` and
  `rc_p_value` are related in spirit but not numerically equal. Replaced
  with the p-value ordering test instead, which is the property the paper
  actually guarantees.
- `evaluation/__init__.py`: `SPAResult`, `spa_test`, `format_spa_table`
  added to imports and `__all__`. No separate `reality_check_p_value`
  function — RC's p-value ships as `SPAResult.rc_p_value`, computed from
  the same bootstrap resamples as SPA (no separate bootstrap pass needed).
- `evaluation/README.md`: `spa.py` row added to the module map; worked
  example now runs `cscv_pbo` and `spa_test` side by side (step 5) with a
  note that SPA is a direct beat-the-benchmark test, not a deflator like
  DSR/PBO.
- `_index.md`'s two White/Hansen rows updated: "read in full and
  implemented 2026-08-06" instead of "not yet read past record".
- `STATUS.md`'s "Next up" updated — SPA/Reality Check removed from the
  blocked list; only real order-book capture for `stress.py` remains open.
- Exit — all met: `spa_test` returns p_value_consistent=0.081 (> 0.05, no
  false rejection) on 20 pure-noise trials vs. a zero benchmark;
  p_value_consistent < 0.1 with the correct trial identified on an
  injected-edge fixture; `p_value_consistent <= rc_p_value` and the
  liberal/consistent/upper ordering both hold on that fixture; full suite
  (162 tests, including 7 new in `test_spa.py`) passes; ruff/black/mypy
  clean.

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
