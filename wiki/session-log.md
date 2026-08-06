# Session Log

Append-only daily log. Newest entry at the top.

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
