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

## 2026-08-06 — aurora-forecaster: new top-level project, BTC/SPY as target securities
**Status:** committed
**Source:** direct user decision, this session

Adopted `DecisionIntelligence/Aurora` (arXiv:2509.22295) as a new forecasting-archetype experiment, scaffolded as a top-level `aurora-forecaster/` project sibling to `freqtrade-experiment/`, not nested inside it — it is a pretrained multimodal generative forecaster (predicts forward returns directly), not a Freqtrade strategy trading a current mispricing back to an anchor, which is what every existing archetype in `wiki/concepts/strategy-archetypes.md` does. Target securities are BTC and SPY, chosen over the actual Hyperliquid book (`WLFI`/`VVV`/`XPL` etc.) because Aurora's own pretraining benchmark (TimeMMD) pairs time series with macro/economy-style expert-curated text, not asset-specific chatter — BTC/SPY are in-distribution for that domain and have deep price/text history, while the actual book's coins have neither (no prior-cycle price history, per the same day's proxy-backtest finding, and negligible text coverage). `evaluation-framework`'s existing metrics were confirmed *not* a constraint on this choice — already asset-class-agnostic across SGX (252-day) and crypto (365-day) annualisation. This is explicitly a feasibility test (does multimodal beat unimodal at all) before ever pointing the model at the actual illiquid book. A university CSLab Slurm GPU cluster is available (personal use confirmed permitted) but deliberately not used yet — the model is small (0.2B params) and local Apple Silicon (MPS) is sufficient; cluster use is deferred until an actual compute bottleneck appears.

## 2026-08-06 — aurora-forecaster: compare all four text-context sources rather than pick one upfront
**Status:** committed
**Source:** direct user decision, this session

Rather than committing to a single text-context source for Aurora's multimodal path, kept and smoke-tested all four candidates surfaced during research: GDELT (free, keyless, domain-matches Aurora's TimeMMD pretraining style, but undocumented and observed rate-limiting), Alpha Vantage `NEWS_SENTIMENT` (ticker-tagged with a sentiment score, but free tier capped at 25 requests/day — too tight to be a primary source for a walk-forward loop), Currents API (1,000 requests/day, no credit card, commercial-use allowed), and Guardian Open Platform (5,000 requests/day, single-publisher but professionally-curated business/economics coverage closest to TimeMMD's domain). All four confirmed working against live endpoints. Guardian is deliberately built-but-unwired — verified it works, not yet used in any pipeline — until the unimodal-vs-multimodal comparison this whole build is aimed at shows a need for it. A candidate fifth source (a personal Straits Times Opinion Forum scraper) was explicitly not added, per the same reasoning: no more sources before the existing four are actually compared.

## 2026-08-06 — evaluation-framework Phase 7 (SPA/Reality Check) closed; order-book capture deliberately deferred
**Status:** committed
**Source:** `evaluation-framework/PLAN.md` Phase 7 execution, this session

SPA/Reality Check (Hansen 2005, White 2000) had been listed as an unbuilt stretch item in the original 6-phase plan because both sources were unreadable — Hansen hit a TLS download failure against the DOI resolver, White is paywalled. Root cause was fetch/access, not a research gap. The user supplied both PDFs directly; relocated to `literature/strategy-evaluation/foundational/` and read in full. Wrote and then executed a Phase 7 plan in the same session: `evaluation/spa.py` implements Hansen's studentized SPA test (three null-recentering variants) plus White's unstudentized RC computed from the same bootstrap resamples, reusing `bootstrap.py`'s existing stationary-bootstrap machinery rather than reimplementing it. 162/162 tests pass, 96% coverage on the new module, ruff/black/mypy clean. Package is now feature-complete against all 7 phases. Separately decided to leave the one remaining optional item (real order-book capture for `stress.py`, currently an explicitly-labeled OHLCV proxy) unbuilt rather than build a rushed version: no strategy is currently live-paper-trading, so there's nothing to capture real book depth against yet, and no L2 data source exists anywhere in the repo today. If revisited, scope as a forward-only capture stub against the live venue, not a historical-backfill project. Also confirmed `evaluation-framework/PLAN.md`/`STATUS.md` stay as project-local docs rather than folding into the wiki's H3L structure — they're a phase-by-phase build spec with literature citations, a different kind of artifact than the wiki's ephemeral/cross-project state.

## 2026-08-06 — mean-variance-paper: forward accumulation starts regime-scoped to post-October-2025; multi-regime gate stays open
**Status:** committed
**Source:** Ethan (relayed by user), user confirmation, this session

Ethan floated restricting the paper monitor's live evidence-accumulation window to the regime after BTC's October 2025 peak, rather than blending pre-peak bull-recovery behavior into the evaluation. On its face this is in tension with "cross-cycle validation required before paper-trading" (that requirement is specifically about testing robustness *across* multiple structurally different regimes — the reason the 2026-08-06 liquid-majors proxy backtest ran a bull window and a chop window separately, and the reason a single-window headline was flagged as not evidence of generalization). Resolution: the tension is real but the proposal still has merit, because multi-cycle backtesting was never actually available for the real book in the first place — `WLFI`/`VVV`/`XPL` have no prior-cycle price history on any venue, which is why the proxy backtest had to substitute liquid majors instead of testing the actual book. For the real book, forward accumulation in whatever regime is currently observable is the only evidence that has ever existed. Committed framing: forward accumulation starts now, scoped to the coherent post-October-2025-peak regime (not blended with pre-peak dynamics) — this is accepted as the start of regime #1's evidence, not as satisfying cross-cycle validation. The original gate question (does the strategy need to survive multiple regimes before scaling capital) remains open and unresolved until a second regime is actually observed. The immediate blocker is operational, not methodological: the paper monitor at https://vercel-paper-dashboard.vercel.app/ is confirmed not working, so nothing can accumulate until it's fixed (see `open-threads.md`).

## 2026-08-06 — mean-variance-paper: build independent forward accumulation instead of using Ethan's Vercel monitor; pre-registered thresholds
**Status:** committed
**Source:** direct user decision, this session

Rather than requesting Ethan's Upstash/Vercel KV credentials to fix or connect to his broken monitor, decided to run forward accumulation independently. This is lower-effort than it first appears: `run_portfolio_short_funding.py::simulate()` (already proven — reused unchanged for the 2026-08-06 liquid-majors proxy backtest) is a pure, deterministic function of the full price/funding history array, with rebalancing computed via `(day_index - lookback) % rebalance_days == 0` — no external state machine is needed the way Ethan's serverless Vercel deployment required Cron+Redis just to persist state between invocations. Re-running `simulate()` daily over the real, growing Hyperliquid price/funding history and reading the newest row is mathematically identical to what a persistent incremental tick would produce. We also have an always-on machine, unlike Vercel serverless, so no external scheduler is needed either.

Two thresholds pre-registered before any data collection starts, so a stopping point isn't chosen after the fact once results are visible:
1. **Early-kill check, no minimum sample required**: decision-012's existing Kill If thresholds (`freqtrade-experiment/mean-variance-paper/analysis/results/2026-06-02-decision-012-kill-criteria-signed-mean-variance-portfolio.md`) — Sharpe/Calmar/MDD worse than equal-weight long, or average effective assets < 3, or average turnover per rebalance > 1.25.
2. **DSR-binding checkpoint at N=250 daily observations** (~8 months out from today) — per the existing confirmed rule in `learnings-archive.md` (2026-05-20, refined) that DSR is only statistically meaningful once N daily obs > ~250. Before that point, any Sharpe/DSR read from the forward accumulation is a running number, not evidence.

Explicitly separate from both: the cross-cycle gate (does the strategy survive a second, structurally different regime) is not a date threshold and stays open-ended — resolved only by an actual regime change occurring, which cannot be scheduled. Reaching N=250 days answers "is the within-regime signal statistically distinguishable from noise," not "does this generalize across regimes."
