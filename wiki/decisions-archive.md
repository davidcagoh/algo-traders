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
