# Session Log

Append-only daily log. Newest entry at the top.

---

## 2026-08-06 — Cross-cycle proxy test for signed mean-variance; traced the "cross-cycle validation required" requirement's origin

- Investigated why `mean-variance-paper`'s signed MV result can't be
  cross-cycle validated on its actual universe: Hyperliquid's public API
  caps history at ~5000 1h candles (~208 days) per pair — confirmed this is
  an exchange-side limit (`hmm-slope-experiment/research/analysis/reports/2026-04-24-decision-002-hyperliquid-deep-history.md`),
  not a freqtrade bug — freqtrade's `download-data` is hard-disabled for
  Hyperliquid (`ohlcv_has_history=False`) precisely because Hyperliquid
  doesn't publish bulk OHLCV anywhere. Separately, `WLFI`/`VVV`/`XPL`
  launched in 2025 and have no prior cycle on any venue — no re-fetch fixes
  that. No `.vercel` directory or other evidence the paper monitor is
  deployed.
- Traced the "cross-cycle validation is required before another paper run"
  line in `LEARNINGS.md` via git history: it was NOT part of collaborator
  Ethan's original commit (`5ef361f`, 2026-06-03) — it first appears when
  `LEARNINGS.md` was written from scratch during the 2026-08-05 repo
  consolidation (`d96b6fd`), inheriting `hmm-slope-experiment`'s
  pre-registered kill-criteria discipline by extension rather than being a
  decision Ethan made for this project. Worth him weighing in before it's
  treated as a hard gate here.
- Ran a liquid-majors proxy test (`analysis/cross_cycle_liquid_majors.py`,
  new script, reuses `run_portfolio_short_funding.simulate`/`target_weights`/
  `metrics` verbatim — same optimizer, only data source and universe
  differ): substitutes `BTC, ETH, SOL, AVAX, ARB, DOGE` (deep Binance
  history) for the actual 9-coin book, across two windows structurally
  different from the original study window (which was itself a sharp
  bear-into-recovery leg). Result:
  `shrunk_mean_variance_signed` placed **last of 5** in a clean bull window
  (Sharpe 2.88 vs equal-weight's 4.15) and only "lost the least" in a chop
  window (both had negative Sharpe). Neither window reproduces the original
  headline result — evidence against the construction having a robust edge
  outside its one favorable window. This is evidence about the *method*,
  not the *actual book* (none of `HYPE, PAXG, TRX, WLFI, VVV, TON, ZRO,
  XPL` are in the proxy universe). See
  `freqtrade-experiment/mean-variance-paper/analysis/results/cross_cycle_liquid_majors_proxy.md`
  for the full write-up and caveats.
- Did not change `shrunk_mean_variance_signed`'s ledger `gate_outcome`
  (still `"passed"` at the `backtest` evidence stage — that's accurate for
  what it is: it did pass decision-012's pre-registered thresholds on its
  own window). The cross-cycle gate is separate and untouched by this
  session; the proxy result argues for continued caution, not for
  retroactively flipping the existing backtest-stage verdict.

---

## 2026-08-06 — Backfilled mean-variance-paper into the registry; migrated remaining hmm-slope-experiment drivers off duplicated formulas

- Backfilled `freqtrade-experiment/mean-variance-paper/` into a new
  `TrialLedger` (`analysis/backfill_ledger.py`, 43 trials + gap marker),
  reading `gate_outcome` mechanically off the pre-registered thresholds in
  decisions 011/012 (long-only and signed mean-variance kill criteria)
  benchmarked against each table's own equal-weight row. The
  `pc_pair_stat_arb` family has no kill-criteria decision doc, so its rows
  are left `gate_outcome="pending"` rather than asserting an unwritten
  verdict. The cross-project registry now spans two projects
  (`hmm-slope-experiment`, `mean-variance-paper`); still a floor, not the
  full search size, per each ledger's own gap marker.
- Migrated the remaining `hmm-slope-experiment` analysis drivers onto
  `evaluation-framework`: `eval_layers.py` is now a thin CLI wrapper around
  `evaluation.layers.compute()`/`format_markdown_table` (which already
  covers L1-L5, a superset of the file's old locally duplicated
  skew/kurtosis/tail-ratio/CVaR/Ulcer/Martin/Pain formulas) plus
  `evaluation.correlation_mdb` (also already covering the file's old local
  MDB/weighting-scheme duplication); `combined_book_mdd.py` now imports the
  weighting/portfolio-returns helpers and uses `evaluation.layers.max_drawdown`
  instead of a local drawdown-series helper. `run_correlation_mdb.py` had
  already been migrated in an earlier session. `generate_pareto_chart.py`
  needed no changes — it's a hand-transcribed data table plus a local
  Pareto-dominance helper with no formula the package covers.
- To support the above without leaking private names across script
  boundaries, promoted `evaluation.correlation_mdb`'s weighting-scheme
  helpers (`_equal_weights`, `_risk_parity_weights`,
  `_mean_variance_weights`) to public API and added a public
  `portfolio_returns()`, exported from `evaluation/__init__.py`.
- Verification surfaced a real latent bug in `run_correlation_mdb.py`: it
  called the package's `marginal_diversification_benefit`/`mdb_robust_flag`
  without passing `annualisation`, silently defaulting to
  `DEFAULT_ANNUAL=252` (SGX) instead of crypto's 365-day year — even though
  the script's own output JSON already *claimed* `"annualisation": 365`.
  Fixed by passing `evaluation.layers.CRYPTO_ANNUAL` explicitly. Confirmed
  by regenerating `_correlation_table.json` before and after the fix: no
  `robust` MDB verdict changed (the flag is scale-invariant to a positive
  annualisation factor at threshold 0), only the reported magnitudes were
  wrong before the fix — so no prior conclusion in the wiki was affected,
  but any future work reading raw MDB magnitudes from that file would have
  been reading a wrong scale.

---

## 2026-08-06 — Extended TrialRecord with cross-project registry fields; backfilled hmm-slope-experiment

- Extended `evaluation-framework/evaluation/ledger.py`'s `TrialRecord` with
  four optional fields toward the cross-project trial registry:  `project`,
  `venue`, `evidence_stage` (`backtest`/`paper`/`live`), `gate_outcome`
  (`passed`/`killed`/`pending`/`n/a`). All default to `None`, so existing
  ledger files (schema_version 1) still load without a migration step;
  `SCHEMA_VERSION` bumped to 2 for new records. Added `TrialLedger.scope()`
  filters for the new fields and a `registry_groups()` method that buckets
  trials by `(evidence_stage, venue)` — deliberately not a single ranked
  leaderboard, per the explicit warning in `open-threads.md`: killed
  IS-backtests and live-tested strategies aren't comparable, and Sharpe
  scales differ by venue.
- Backfilled the new fields onto the existing 10-record + gap-marker
  `hmm-slope-experiment` ledger (`research/analysis/backfill_ledger.py`),
  reading gate outcomes off the bear-window MDD-vs-5.5%-threshold
  comparisons already on record in `learnings-archive.md`: V1 and V3 killed
  (bear MDD 8.65% and 5.72%, both breach), V2 passed (4.44%), the short and
  long-short variants killed (ruled out on net P&L, not the MDD axis).
- Not done: the `mean-variance-paper` project (part of the ~34-report-card
  backfill target) has no `TrialLedger` or backfill script yet — its result
  cards live at
  `freqtrade-experiment/mean-variance-paper/analysis/results/*.md` and
  haven't been reconstructed into ledger records. This is the next step for
  a real cross-project registry; right now the registry has one project in
  it.

---

## 2026-08-06 — Built evaluation-framework as an installable package; fixed a second DSR bug; migrated dsr_analysis.py

- Decided `evaluation-framework/` priority: reusable package first, methods
  paper second. Archived the May manuscript/essay/worked-example to
  `archive/manuscript-2026-05/` (kept, not deleted — stale relative to the
  2026-08-05 literature scan and the `HmmSmaSlopeV2` live failure).
- Built out all 6 phases of `evaluation-framework/PLAN.md`: `pyproject.toml`
  + CI (`.github/workflows/evaluation-framework-ci.yml`); an append-only
  trial ledger (`ledger.py`, backfilled for the HmmSmaSlope family with an
  explicit reconstruction-gap marker); CSCV/PBO (`pbo.py`) and block-bootstrap
  CIs (`bootstrap.py`/`intervals.py`); purged splits and a mechanically
  enforced holdout seal (`splits.py`/`holdout.py` — the real
  2026-06-01→12-31 forward window is now sealed at
  `freqtrade-experiment/hmm-slope-experiment/analysis/holdout_seals.jsonl`);
  funding-aware cost/slippage modeling (`costs.py`/`stress.py`); and
  benchmark/factor/regime decomposition plus backtest-to-live reconciliation
  with a three-valued PASS/FAIL/**INCOMPLETE** verdict (`live.py`) — the
  `HmmSmaSlopeV2` original 30-day gate now correctly resolves to
  `INCOMPLETE` (2 trades < 5 required), the extended run to `FAIL`, as a
  permanent regression test. 152 tests, 96% coverage, clean ruff/black/mypy.
- Found and fixed a second DSR bug while re-running the DSR-vs-PBO
  head-to-head on real HmmSmaSlope data (`analysis/pbo_vs_dsr.py`): a
  narrow, correlated candidate family (e.g. V1/V2/V3 parameter variants)
  understates cross-trial `sharpe_var` and inflates DSR — the mirror image
  of the earlier `n_trials` under-deflation bug. `compute_dsr_table` now
  accepts an explicit `sharpe_var` override, and `compute_dsr_from_ledger`
  defaults to pulling it from the ledger's own recorded Sharpes rather than
  always from the wallets under test. With both fixes, DSR and PBO now
  agree on the HmmSmaSlope family (NOISE / PBO=0.171).
- Migrated `research/analysis/dsr_analysis.py` off its duplicated DSR
  formula onto `evaluation.dsr`; fixed a stale output path bug in the same
  pass (`wiki/results/` didn't exist; the file actually lives at
  `analysis/reports/_dsr_table.json`). Verified output matches pre-migration
  numbers exactly.
- Discussed (not yet built) extending `TrialRecord` with `project`,
  `venue`, `evidence_stage`, and `gate_outcome` fields toward a principled
  cross-project trial registry — filterable by evidence maturity and venue
  rather than one flat ranked leaderboard, which would misleadingly compare
  killed IS-backtests against live-tested strategies and mix incompatible
  Sharpe scales across venues.

**Next:** Nothing from this session is committed. Extend `TrialRecord`'s
schema (small, ~20min) before committing to the larger backfill effort
across ~34 report cards in `hmm-slope-experiment/` plus `mean-variance-paper/`.

---

## 2026-08-06 — Ruled out HmmSmaSlopeV2 short-side; fixed recurring Docker base-image drift

- Drafted `HmmSmaSlopeV2Short` (short-side mirror of V2's HMM/slope signal) and
  `HmmSmaSlopeV2LongShort` (V2's long entries + the short entries combined), both in
  `freqtrade-experiment/hmm-slope-experiment/research/strategies/`.
- Backtested both on the same bull (Binance, market +190.83%) and bear (Hyperliquid,
  market -38.61%) windows V2 used. Short-only lost even in the bear window (-13.12%,
  MDD 16.07%, 3x the 5.5% kill threshold) — no edge, not a regime-timing problem.
  Combined long+short was worse than either half alone in both windows (bull +26.79%
  vs V2's +33.44% with MDD more than doubled; bear -14.70% vs V2's -1.58%). Full
  writeup: `research/analysis/reports/2026-08-06-hmm-sma-slope-v2-short-and-longshort.md`.
- Rebuilding the backtest image surfaced a recurrence of the 2026-05-21 Track B
  bring-up issue: `execution/ops/Dockerfile.ext`'s `FROM freqtradeorg/freqtrade:stable`
  had drifted to Python 3.14, which has no hmmlearn wheel — compiles but produces a
  silently-broken `.so`. Fixed by digest-pinning to the `2025.9` tag (Python 3.13, has
  a wheel), upgrading `ccxt` (fixes a separate Hyperliquid market-load crash), and
  adding a build-time `python -c "from hmmlearn.hmm import GaussianHMM"` assertion so
  future drift fails `docker build` instead of failing silently at deploy time.

**Next:** Choose the evaluation framework's primary deliverable and review the
first automated multi-thread literature PR before accepting adaptive keywords.

---

## 2026-08-05 — Unified literature and rebuilt recurring discovery

- Consolidated all cross-project PDFs and source notes under root `literature/`; created authoritative crypto-market and strategy-evaluation indexes, including explicit records for unavailable PDFs.
- Screened current evaluation methods, empirical audits, foundational inference, and surveys; downloaded and validated legally available PDFs with file-type, metadata, and text checks.
- Flattened `literature/crypto-markets/` into stable-ID-first PDF/Markdown pairs and repaired every repository link to the new paths.
- Reduced `quant-research-agent/` to automation and pattern documentation; configured six independent search threads with budgets, exclusions, immutable seeds, and PR-reviewed adaptive terms.
- Updated the scheduled Codex Action to advance every thread, log zero-result scans, validate changes, stage only `literature/`, and defer durable wiki claims until human review.
- Validated all local PDFs, Markdown links, YAML, and whitespace after the migration.

**Next:** Choose the evaluation framework's primary deliverable and review the
first automated multi-thread literature PR before accepting adaptive keywords.

---

## 2026-08-05 — Consolidated the trading workspace and closed the Freqtrade experiment

- Merged backtesting, strategy configuration, live execution, monitoring, and dated records into `freqtrade-experiment/hmm-slope-experiment/`; removed duplicated upstream Freqtrade and runtime artifacts.
- Stopped the Hetzner deployment and evaluated the Hyperliquid paper run: 21 closed trades, -3.54%, 4.8% win rate, and an eleven-loss streak; parked without live-capital graduation.
- Merged reusable evaluation code and its evolving paper/essay outputs into the root `evaluation-framework/` project; moved primary PDFs and paper notes to root `literature/`, with `quant-research-agent/` retained as automation only.
- Applied the `/wiki` H3L structure: hot state at the root, evergreen notes in `concepts/`, grep-oriented archives, and historical equity evidence in `artifacts/`.
- Rebasing before push surfaced collaborator-owned mean-variance and PC-neutral work; isolated its strategy, config, analysis, results, agent instructions, and paper monitors in `freqtrade-experiment/mean-variance-paper/`.
- Replaced the retired machine-local paper-search trigger with a scheduled/manual OpenAI Codex Action that opens reviewable pull requests; configured its encrypted `OPENAI_API_KEY` repository secret without committing the local key.
- Repaired all repository references; validated Markdown links, Python syntax/imports, shell syntax, Compose configuration, and the 14-page LaTeX build.

**Next:** Choose the evaluation framework's primary deliverable and reconcile it
with the failed live test; keep the signed mean-variance track in research until
cross-cycle validation.
