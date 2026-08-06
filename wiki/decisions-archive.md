# Decisions Archive

Committed, closed, or superseded cross-project decisions. Append-only.

---

## 2026-08-05 — Separate knowledge, evidence, and publications
**Status:** committed
**Source:** repository cleanup

Reusable conclusions belong in the root wiki; primary sources belong in `literature/`; experiment data and dated records remain with the owning experiment; publications are grouped by intellectual project; reusable research-agent machinery belongs in `quant-research-agent/`.

## 2026-08-05 — Adopt the H3L wiki layout
**Status:** committed
**Source:** `/wiki` maintenance pass

The root wiki uses hot state files (`_index.md`, `open-threads.md`, and `session-log.md`), grep-oriented archives for findings and decisions, evergreen notes under `concepts/`, and retained historical evidence under `artifacts/`.

## 2026-08-05 — Centralize literature and separate discovery automation
**Status:** committed
**Source:** literature cleanup and recurring-search redesign

Root `literature/` owns PDFs, source notes, authoritative indexes, search configuration, and search history. Crypto-market PDFs and notes use one flat stable-ID-first collection. `quant-research-agent/` owns only the reusable pattern and operating prompt. The scheduled Action advances every enabled literature thread, proposes bounded adaptive keywords, and opens a review-gated pull request without promoting unattended interpretations into the wiki.

## 2026-08-06 — Remove the DSR kurtosis carve-out; require explicit trial counts
**Status:** committed
**Source:** `evaluation-framework/evaluation/dsr.py` planning pass, cross-checked against `HmmSmaSlopeV2`'s failed live run

The 2026-05-20 carve-out (`is_dsr_binding()`) demoted DSR to a non-binding "humility check" whenever excess kurtosis ≥ 5, on top of N_obs. This double-counted: the DSR denominator (`1 − γ₃·SR + (γ₄−1)/4·SR²`, Bailey & López de Prado 2014) already absorbs skew and kurtosis by construction, so a fat-tailed sample already scores a low DSR without a separate gate. The kurtosis clause is removed; only the N_obs floor (N > 250, for CLT validity) remains. Separately, `compute_dsr_table()` derived `N_trials` from `len(wallets)` — whatever subset the caller passed — rather than the true search size; it now requires an explicit `n_trials` keyword argument and raises if it's smaller than the candidates given. Neither defect had any external callers at time of fix (`freqtrade-experiment/.../dsr_analysis.py` carries its own copy of the formula, not an import), so this was a clean break. Superseded prior carve-out is recorded in `learnings-archive.md` (2026-05-20 entry) and left as-is for history; do not re-add a kurtosis exemption without a PBO/CSCV head-to-head first (see `open-threads.md`).

## 2026-08-06 — evaluation-framework priority: reusable package first, methods paper second
**Status:** committed
**Source:** direct user decision, this session

`evaluation-framework/` had been an ongoing methods-paper draft plus a lighter package. Decided: build the package (`evaluation/`) out fully first — it is package-first because a paper draft risks front-running literature and code that keeps moving (the 2026-08-05 literature scan, this session's DSR fixes), whereas a tested package is immediately useful regardless of publication plans. The May manuscript/essay/worked-example are archived (not deleted) to `evaluation-framework/archive/manuscript-2026-05/`, explicitly marked stale. The paper resumes only after the package produces a further package-vs-literature-backed result worth writing up. See `evaluation-framework/STATUS.md`.

## 2026-08-06 — evaluation-framework package build-out complete (Phases 0-6)
**Status:** committed
**Source:** `evaluation-framework/PLAN.md` execution, this session

All 6 planned phases shipped: installable package + CI; append-only trial ledger (`ledger.py`) fixing DSR's `n_trials` under-deflation; CSCV/PBO (`pbo.py`) as a second deflator that doesn't share DSR's fat-tail sensitivity; block-bootstrap CIs (`bootstrap.py`/`intervals.py`); purged splits plus a mechanically-enforced holdout seal (`splits.py`/`holdout.py`); funding-aware cost/slippage modeling (`costs.py`/`stress.py`); and benchmark/factor/regime decomposition with backtest-to-live reconciliation carrying a three-valued PASS/FAIL/INCOMPLETE verdict (`live.py`). 152 tests, 96% coverage. A second DSR bug was found and fixed in the process: a narrow, correlated candidate family understates cross-trial `sharpe_var` and inflates DSR (mirror image of the `n_trials` bug) — `compute_dsr_table` now accepts an explicit `sharpe_var` override. Every module cites its justifying source in `literature/strategy-evaluation/_index.md`. Nothing from this session is committed to git yet.

## 2026-08-06 — Sealed the HmmSmaSlope forward-test window mechanically
**Status:** committed
**Source:** `evaluation-framework/evaluation/holdout.py`, `freqtrade-experiment/hmm-slope-experiment/research/analysis/seal_forward_window.py`

The precommitted 2026-06-01 through 2026-12-31 Binance forward window (decision 005) was previously a memory-only rule ("should not be partially inspected"). It is now sealed at `freqtrade-experiment/hmm-slope-experiment/research/analysis/holdout_seals.jsonl` via `evaluation.holdout.seal_holdout`; any future loader must call `guard()` before inspecting data from that window, which raises `HoldoutViolation` on any overlap and requires an irreversible, logged `break_seal()` with a reason to proceed. No downloader for the window exists yet.
