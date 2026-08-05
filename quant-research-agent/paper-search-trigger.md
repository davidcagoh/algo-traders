# Literature Search Agent — Master Config

**Former trigger ID:** `trig_013s3hXkiYrSnYh2Qes1KPws` (retired Claude remote trigger)
**Schedule:** Sundays 4 AM America/Toronto
**Workflow:** `.github/workflows/paper-search.yml`
**Search configuration:** `literature/search-config.yml`
**Last updated:** 2026-08-05
**Status:** enabled; PR-gated

This is the operating prompt read by the GitHub Action. Root `literature/` owns
sources, indexes, source notes, and search history. `quant-research-agent/` owns
only the automation pattern and prompt.

## Scheduled-run instructions

### 1. Detect current state

Read completely:

- `literature/search-config.yml`
- `literature/_index.md`
- every enabled thread's configured index
- `literature/search-log.md`
- `wiki/open-threads.md`
- `wiki/learnings-archive.md` entries relevant to the configured threads

Reconcile files on disk against the indexes before searching. Treat this as a
delta run from the most recent search-log date. Never rediscover or duplicate an
already indexed paper or alternate version.

### 2. Search every enabled thread

Search each enabled thread independently using its seed terms, accepted candidate
terms, exclusions, source list, recency window, and budget. Do not spend the
whole run on the first productive thread. Record zero-result threads too.

Use primary sources and authoritative metadata. Prefer recent papers, but admit
an older foundational source when a new paper reveals that the corpus is missing
an evaluation method it depends upon.

### 3. Screen and verify

For each candidate:

- verify title, authors, date, identifier, maturity, and version;
- distinguish peer-reviewed work, working papers, and preprints;
- read beyond the abstract before making any claim about the paper's stance or
  relationship to another source;
- reject papers that merely report a headline return without a reusable method,
  realistic execution bridge, or direct open-thread relevance;
- deduplicate across all root literature indexes, not just the current thread.

Select no more than the configured per-thread and total budgets.

### 4. Retrieve and validate primary material

For every selected source, attempt a legal PDF download into its configured
`collection_dir` when present, otherwise its `source_dir`, using
`<stable-id>-<descriptive-slug>.pdf`.

A successful HTTP response is insufficient. Validate with `file`, `pdfinfo`, and
first-page `pdftotext`. If retrieval fails or the paper is paywalled, do not use
an unofficial bypass. Add a record to the thread index with the canonical URL
and exact access status.

### 5. Write records and review drafts

Update the configured thread index for every selected source, including sources
without PDFs. For threads with `write_notes: true`, create a same-directory
Markdown note beside the PDF, sharing its filename stem where possible, with:

- title, authors, venue, identifier, date, maturity;
- `Local PDF` or explicit `Access status`;
- method, sample period/universe, evaluation protocol, reported results;
- limitations and concrete relevance to an active thread;
- an evidence note distinguishing abstract-level metadata from sections actually
  read.

Scheduled runs must label new interpretive source notes `Review status: draft`.
Do not promote new claims into the durable wiki during an unattended run. The
pull request is the mandatory human characterization checkpoint. Wiki synthesis
may be added in a later reviewed session.

### 6. Refine keywords conservatively

Follow `keyword_policy` in `literature/search-config.yml`:

- never delete or rewrite seed terms;
- add at most the configured number of candidate terms to that thread's
  `adaptive_terms` list;
- require support from the configured number of relevant sources or a direct
  root-wiki open thread;
- record the proposed term, supporting sources, target thread, and reason in
  `literature/search-log.md`;
- let a human-reviewed pull request decide whether the term remains.

Do not optimize keywords merely to increase hit count. A term is useful only if
it improves relevant, non-duplicate retrieval.

### 7. Log the run

Append a dated search-log section containing each thread, exact queries,
candidates screened, selected sources, rejection reasons, PDF/access outcomes,
and keyword changes. If nothing is selected, still record the search and why.

Do not commit, push, or open a pull request. The workflow handles the dated
branch, commit, and PR after validating the changed paths.

## Change log

| Date | Change |
|---|---|
| 2026-08-05 | Unified all source ownership under root literature; added per-thread delta scans, PDF validation, records for inaccessible sources, draft review status, and bounded keyword refinement. |
| 2026-08-05 | Replaced retired remote trigger with scheduled/manual OpenAI Codex Action and PR review gate. |
| 2026-04-24 | Initial crypto/Hyperliquid adaptation. |
