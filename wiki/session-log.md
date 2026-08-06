# Session Log

Append-only daily log. Newest entry at the top.

---

## 2026-08-06 — evaluation-framework cleanup + Phase 7 (SPA/Reality Check) implemented

- Cleaned up `evaluation-framework/` and root build junk: deleted untracked
  `.venv`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.coverage`,
  `algo_eval_stack.egg-info` (~481M, none git-tracked); added
  `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/` to root `.gitignore`
  (they were missing despite `.venv/`/`.coverage`/`*.egg-info/` already
  being covered). Confirmed `PLAN.md`/`STATUS.md`/`README.md`/
  `pyproject.toml` were NOT stale despite the user's suspicion — all 6
  original phases were genuinely complete per `STATUS.md`.
- Investigated why SPA/Reality Check (Hansen 2005, White 2000) were listed
  as "record only" in `literature/strategy-evaluation/_index.md`: Hansen
  hit a TLS download failure against the DOI resolver, White is behind an
  Econometrica-adjacent paywall — not a research gap, a fetch/access
  failure. User supplied both PDFs directly; relocated into
  `literature/strategy-evaluation/foundational/` with descriptive
  filenames matching the directory's existing convention, and read both
  in full (30 + 17 pages).
- Wrote an implementation plan as **Phase 7** in
  `evaluation-framework/PLAN.md`, matching the existing phase format
  (literature citation, concrete deliverables, test list, exit criteria),
  then implemented it fully in the same session: `evaluation/spa.py`
  (Hansen's studentized SPA test with three null-recentering variants
  `l`/`c`/`u`, plus White's unstudentized RC as `SPAResult.rc_p_value`
  computed from the same bootstrap resamples), 7 new tests in
  `tests/test_spa.py`, de-privatized
  `bootstrap.py::stationary_bootstrap_indices` so `spa.py` reuses it
  instead of reimplementing resampling, wired into `__init__.py` and
  `evaluation/README.md`'s module map + worked example.
- **Correction to my own Phase 7 plan, caught during implementation**: I
  had written a test asserting `p_value_liberal` (Hansen's `μ̂ˡ` null
  variant) numerically equals White's RC p-value, reasoning "μ̂ˡ is by
  construction the RC's null." That's wrong — `μ̂ᵘ=0` (not `μ̂ˡ`) is the
  RC-equivalent null *philosophy* (both assume every model's population
  mean is exactly 0), and even then literal RC is unstudentized while all
  three SPA variants are studentized, so they're related in spirit but
  not numerically equal. Replaced with a p-value ordering test
  (`liberal <= consistent <= upper`, which Hansen's `μ̂ˡ ≤ μ̂ᶜ ≤ μ̂ᵘ`
  ordering does guarantee) and a direct power-comparison test
  (`p_value_consistent <= rc_p_value` on a known-edge fixture,
  reproducing the paper's actual headline claim).
- Verified: full suite 162/162 passing (150 prior + 12, including the 7
  new SPA tests and bootstrap.py rename fallout), `spa.py` at 96% line
  coverage, ruff/black/mypy clean across the whole package. Updated
  `PLAN.md` (0-6 → 0-7 complete), `STATUS.md`, and the literature index's
  read-status flags to close out the phase. Deleted the venv/caches again
  after verification, consistent with the earlier cleanup.
- Discussed the real order-book capture item (`stress.py`'s
  `depth_from_ohlcv` OHLCV proxy) — decided to skip it for now rather than
  build a rushed version: no strategy is currently live-paper-trading, so
  there is nothing to capture real book depth against yet. A genuinely
  quick forward-only capture stub (poll Hyperliquid's order-book endpoint
  going forward, no historical backfill) was scoped as the option if this
  becomes relevant later.
- Confirmed with the user that `evaluation-framework/PLAN.md` and
  `STATUS.md` should stay as project-local docs rather than being folded
  into the wiki's H3L structure — they're a phase-by-phase build spec with
  literature citations, not ephemeral cross-project state; the wiki's
  `_index.md` already routes to them correctly via the `Now:` pointer.

**Next:** Optional order-book capture item is deliberately parked, not
forgotten — revisit once a strategy is actually live-paper-trading.

## 2026-08-06 — Session wrap: aurora-forecaster stood up end-to-end (data + model + text sources)

- Full session summary (see detailed entries below for each step): scaffolded
  new top-level project `aurora-forecaster/` for a forecasting archetype
  genuinely different from the mean-reversion-style archetypes everywhere
  else in this repo; TDD'd device selection, price clients (BTC via
  ccxt/Binance, SPY via yfinance), and four text-context clients (GDELT,
  Alpha Vantage, Currents API, Guardian Open Platform); got a real
  multimodal forward pass running end-to-end on local Apple Silicon (MPS);
  found and fixed a genuine bug in the published `aurora-model==0.2.0`
  package. All four text sources and both price sources are now confirmed
  working against live endpoints — see `aurora-forecaster/README.md` for
  the full technical record (version pins, the library bug and its fix,
  per-source rate limits).
- Ethan separately confirmed his Vercel paper monitor is deployed
  (undocumented locally because never pushed) but not working —
  corroborates this session's earlier proxy-backtest doubt about signed
  MV's edge.
- Noted (git status) unrelated uncommitted changes in
  `evaluation-framework/` (PLAN.md, STATUS.md, new `spa.py`/`test_spa.py`)
  and `literature/strategy-evaluation/` (two new PDFs, updated `_index.md`)
  that predate this session and weren't touched here — left alone, not
  part of this commit. Worth checking their origin next session (possibly
  the literature-search workflow's first run landing changes, or leftover
  unstaged work from an earlier session).

**Next:** Align the four text sources into one per-timestep text-context
input for Aurora's multimodal path, then run the actual unimodal vs.
GDELT vs. Alpha Vantage vs. Currents comparison — the feasibility question
this whole build has been aiming at. Guardian stays built-but-unwired until
that comparison shows a need for it. Separately, investigate the unrelated
uncommitted `evaluation-framework`/`literature` changes noted above.

---

## 2026-08-06 — Currents and Guardian smoke-tested; all four text sources confirmed working

- User added `CURRENTS_API_KEY` and `GUARDIAN_API_KEY` to root `.env`.
  Confirmed present via `grep -oE '^[A-Z_]+='` (names only, values never
  read), then ran both smoke scripts the same way as Alpha Vantage's (key
  loaded via `python-dotenv`, never printed). Both work: Currents returned
  20 real articles each for `bitcoin` and `S&P 500` keyword queries;
  Guardian returned 10 real, on-topic business-section articles each for
  the same two queries.
- All four text sources (GDELT, Alpha Vantage, Currents, Guardian) and both
  price sources (BTC, SPY) are now confirmed working against real,
  live endpoints. Guardian remains explicitly unwired per standing
  decision — verified working, not yet used in any pipeline.
- Fast test suite: 18/18 passing, no network required.

---

## 2026-08-06 — Added Currents API and Guardian text clients; four-source comparison now scoped

- User surfaced a comparison table + a second corroborating source (a blog
  post, treated with mild skepticism given its unrelated origin domain, but
  its claims matched both the table and this session's own GDELT/Alpha
  Vantage findings). Consensus read: Alpha Vantage's 25 req/day cap is a
  hard ceiling no caching strategy fixes, not a throttle to design around;
  Currents API (1,000/day, no card, commercial-ok) and Guardian Open
  Platform (5,000/day, non-commercial, single-publisher but
  professionally-curated business/economics coverage closer to TimeMMD's
  domain) are the credible alternatives.
- Decision: try all four rather than swap. TDD'd
  `aurora_forecaster/data/text_currents.py` and
  `aurora_forecaster/data/text_guardian.py` (build-URL + fetch, dependency
  injected, no network in tests — 18/18 passing total now). Neither
  smoke-tested yet — both need free API keys (Currents: currentsapi.services,
  Guardian: open-platform.theguardian.com) not yet in `.env`. Guardian is
  explicitly "verify it works, don't use it yet" per standing decision not
  to commit to a source before the comparison runs.
- `.env` var names checked via `grep -oE '^[A-Z_]+='` (names only, values
  never read) — confirmed only `OPENAI_API_KEY` and `ALPHA_VANTAGE_API_KEY`
  present; `CURRENTS_API_KEY` and `GUARDIAN_API_KEY` still needed.

---

## 2026-08-06 — First real multimodal Aurora forward pass; found and fixed a batch-collapsing bug in aurora-model==0.2.0

- Got a real end-to-end multimodal forward pass working: real BTC OHLCV
  (528-step lookback, ccxt/Binance) + real/fallback text through
  `AuroraForPrediction.generate(...)`, output shape `(1, 10, 96)` matching
  the unimodal baseline. Confirmed via
  `aurora-forecaster/scripts/multimodal_smoke_test.py`.
- Found a real bug in the published `aurora-model==0.2.0` package along the
  way: its `generate(text_inputs=...)` convenience path
  (`aurora/ts_generation_mixin.py`) calls `.squeeze(0)` on the tokenizer
  output, which collapses the batch dimension whenever batch size is 1 —
  our case, since forecasting is per-asset. Crashes downstream BERT encoding
  with `not enough values to unpack (expected 2, got 1)`. Not an environment
  or usage mistake — reproduced with real data, root-caused by reading the
  installed package source, confirmed by an isolated bypass test.
- Fix: pre-tokenize ourselves and pass `text_input_ids`/`text_attention_mask`/
  `text_token_type_ids` directly (the `generate()` signature accepts these
  and only hits the buggy path when `text_inputs` is set). Landed as
  `aurora_forecaster/multimodal.py::tokenize_text_context`, TDD'd (3 tests,
  no network — uses the model's bundled local BERT tokenizer files), wired
  into the smoke script with a comment explaining why.
- Both live text sources hit rate limits during testing: GDELT returned 429
  twice (undocumented limit, no backoff yet); Alpha Vantage confirmed at its
  stated 25 req/day, 1/sec free-tier cap (see earlier entry below). Neither
  is fatal — the smoke script now degrades to fallback text on GDELT failure
  — but a real walk-forward loop will need caching/backoff design for both.
- User flagged a third possible text source for later: a personal Straits
  Times Opinion Forum scraper at
  `/Users/davidgoh/LocalFiles/Post-Duke/st_forum_scraper/` (Selenium,
  non-headless by design — needs manual popup dismissal — targets
  `opinion/forum`'s specific markup). Not adapted or wired in this session;
  logged as a candidate, not built, per the standing decision not to add
  more sources before GDELT vs. Alpha Vantage vs. unimodal baseline actually
  runs. Would need de-babysitting (headless-capable) and re-verified
  selectors for Business/Finance/Wealth sections before it could feed an
  unattended backtest.

---

## 2026-08-06 — Chose BTC/SPY as aurora-forecaster targets; built and smoke-tested price/text data clients

- Decided target securities: BTC and SPY, not the actual Hyperliquid book.
  Rationale traced to Aurora's own pretraining domain — its primary
  multimodal benchmark, TimeMMD, pairs time series with macro/economy-style
  expert reports across 9 domains (Agriculture, Climate, Economy, Energy,
  Environment, Health, Security, SocialGood, Traffic), not asset-specific
  headline chatter. `WLFI`/`VVV`/`XPL` etc. would fail this test twice —
  they already lack price history (2026-08-06 proxy-backtest finding) and
  would have near-zero text coverage in Aurora's pretraining distribution.
  `evaluation-framework`'s metrics were confirmed *not* a constraint here —
  already asset-class-agnostic (spans SGX 252-day and crypto 365-day
  annualisation).
- TDD-built (tests first, dependency-injected fakes, no network in the fast
  suite — 10/10 passing) three data clients in `aurora-forecaster/`:
  `data/price.py` (BTC via ccxt/Binance, SPY via yfinance — reusing existing
  repo conventions per `wiki/concepts/data-sourcing.md`, no new tooling
  needed there), `data/text_gdelt.py` (GDELT DOC 2.0, free/keyless),
  `data/text_alphavantage.py` (Alpha Vantage `NEWS_SENTIMENT`, free tier,
  needs an API key).
- User chose to keep and compare both text sources rather than commit to one
  upfront (GDELT's domain-alignment vs. Alpha Vantage's ticker-tagging is
  itself part of the feasibility question). Real-endpoint smoke tests
  confirmed working for BTC, SPY, and GDELT; Alpha Vantage untested pending
  an API key (documented in `aurora-forecaster/README.md`).
- Added a "News / text (multimodal forecasting)" section to
  `wiki/concepts/data-sourcing.md` — first time this repo has sourced text
  data rather than only price/funding/order-book.

---

## 2026-08-06 — Scaffolded aurora-forecaster/, a new forecasting-archetype project

- New top-level project `aurora-forecaster/`, separate from
  `freqtrade-experiment/` because [DecisionIntelligence/Aurora](https://huggingface.co/DecisionIntelligence/Aurora)
  ([arXiv:2509.22295](https://arxiv.org/abs/2509.22295)) is a pretrained
  multimodal generative forecasting foundation model (time series + text +
  image inputs, flow-matching decoder), not a Freqtrade strategy — it
  predicts forward returns directly rather than trading a current
  mispricing back to an anchor, which is a genuinely new archetype relative
  to everything in `wiki/concepts/strategy-archetypes.md`.
- TDD-built device selection (`aurora_forecaster/device.py`, tests written
  first) and confirmed real pretrained weights load and run end-to-end on
  local Apple Silicon (M3, MPS backend) via `scripts/smoke_test.py` — output
  shape `(1, 10, 96)` for a synthetic unimodal input. Model is small (0.2B
  params, ~800MB F32); local CPU/MPS is sufficient for now.
- Two real compatibility issues surfaced and fixed: (1) the model card's
  `torch==2.4.0` pin has no Python 3.13 wheel — relaxed to `torch>=2.6`;
  (2) that pulled in `transformers>=5`, whose internal weight-tying API
  change (`all_tied_weights_keys`) breaks `aurora-model==0.2.0`'s
  `from_pretrained` — pinned `transformers<5,>=4.44` instead, confirmed
  working. Both documented in `aurora-forecaster/README.md`.
- User confirmed a UofT CSLab Slurm GPU cluster is available (personal use
  permitted as a full-time grad student, underused over summer) but decided
  to hold off — local is sufficient for the model's size, cluster use is
  deferred until an actual compute bottleneck appears (e.g. sweeping
  text-context variants at scale).
- Open design gap, not yet started: no text-context data source exists in
  this repo for the multimodal path, and `evaluation-framework`'s metrics
  assume realized returns, not a probabilistic forecast — both need design
  work before this can produce a comparable backtest result.

---

## 2026-08-06 — Ethan confirmed Vercel paper monitor deployed but non-functional

- Ethan confirmed he deployed his own paper monitor at
  https://vercel-paper-dashboard.vercel.app/ directly (never pushed the
  `.vercel` config to the repo, which is why no local evidence of it existed
  — see prior entry below). He also confirmed it is **not working**, which
  corroborates this session's cross-cycle proxy-backtest finding casting
  doubt on `shrunk_mean_variance_signed`'s edge. Still unresolved: whether
  he wants cross-cycle validation to formally gate this project (see
  `open-threads.md`).

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
