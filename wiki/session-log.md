# Session Log

Append-only daily log. Newest entry at the top.

> **Archived:** entries before 2026-08-07 (aurora-forecaster rolling-forecast loop) moved to `session-log-archive-2026-08.md`.

---

## 2026-08-09 — aurora-forecaster: funding/DXY/SPY text+vision streams built, n=4→n=12 rerun, dashboard built; funding-vision result did NOT replicate

- Built three new numeric covariate streams (funding rate via Hyperliquid, DXY, SPY) after confirming Aurora is univariate-only for its primary time-series input (no way to feed multiple numeric series natively) — routed them through the existing text-covariate path instead: `data/text_funding.py` (Hyperliquid `/info` funding history, exponential backoff on 429), `fetch_dxy_ohlcv` added to `data/price.py`, extractors in `text_adapter.py`, dispatch in `text_fetch.py`, three new `StreamConfig`s (`FUNDING_ONLY`/`DXY_ONLY`/`SPY_ONLY`) in `ablation.py`.
- Then built a second, orthogonal axis: encoding those same three covariates as **rendered line-chart images** (`vision.py::render_line_chart`, Pillow) instead of text, passed via Aurora's `vision_inputs` path — `vision_fetch.py`, `VisionSource`/`vision_sources` on `StreamConfig`, `covariate_encoding` field added to both ledger schemas (v2→v3). Found and fixed two real bugs in `aurora-model==0.2.0` along the way: (1) a double-preprocessing crash — `vision_inputs` must be a raw un-preprocessed PIL Image, since Aurora's own `ViTImageProcessor` runs internally; (2) a genuine MPS device-placement bug (the internal ViT output never gets moved off CPU) — vision-covariate runs are forced to `device="cpu"` as a documented workaround, not silently patched.
- First run at n=4 origins surfaced a striking result: `funding-vision` beat `unimodal` at p=0.000 and its own text version `funding` at p=0.040. Flagged as needing replication before trusting it — 9 configs → 36 pairwise DM tests, no multiple-comparison correction, n=4 is thin.
- Rebuilt for a larger n rather than trusting the n=4 result: pinned `FETCH_SINCE_MS` to a fixed calendar anchor (2026-04-01) after discovering the previous `since`-less fetch caused cross-config origin misalignment (ledgers built on different days had zero common origins, breaking `align_common_origins`); bumped `FETCH_LIMIT` 1000→1700 and `TEXT_FETCH_DELAY_SECONDS` 5.0→10.0 (more GDELT calls per config at 12 origins vs 4) → **12 non-overlapping origins**, 3x the original sample. Deleted all stale n=4 ledgers and reran all 10 `STANDARD_CONFIGS`.
- **Real finding: `funding-vision` did NOT replicate at n=12.** At n=4 it was the standout config; at n=12 its mean CRPS loss (1366.3) is now worse than plain `funding` text (1291.9, the actual best performer) and not significantly different from `unimodal` (1387.4, p=0.635 vs funding-vision). No config beats `unimodal` significantly at n=12 (best p-value vs. unimodal is `funding` at p=0.110). This is a textbook small-n/multiple-comparisons false positive, not a real vision-encoding advantage — logged as a methodological lesson in `learnings-archive.md`.
- `GDELT_ONLY` and `GDELT_CURRENTS` still blocked by GDELT rate-limiting even at the hardened 10s spacing — `GDELT_ONLY` got through 8/12 origins before a 429 this run (better than the earlier 2-3/4 failures, but still incomplete). Both remain unrun at n=12; the ablation report/dashboard reflect 8/10 configs.
- Built persistent tracking so this doesn't need re-deriving each time: `aurora_forecaster/ablation.py::compute_ablation_results` (extracted from `run_ablation_report`, returns structured summaries/comparisons rather than only a markdown string), `leaderboard.py` (append-only `LeaderboardEntry` history, mirrors the ledger pattern), `scripts/render_dashboard.py` (local static `artifacts/dashboard.html` — bar chart + DM significance table + per-config trend section, inline SVG/CSS, deliberately NOT the Artifact tool per standing preference to keep this off claude.ai).
- Standing process note reconfirmed this session: batching (no per-TDD-stage commits) per explicit user instruction; this is the first commit covering all of the above.

**Next:** Revisit the original calibration-miscalibration finding (nominal 50/80/95% vs. ~20/28/38% empirical, first found 2026-08-07 at n=4 unimodal) using the now-available n=12 data — more fundamental than covariate/encoding choice and unrevisited since the first run; scoped for a future session. `GDELT_ONLY`/`GDELT_CURRENTS` remain blocked by rate limiting, low priority.

---

## 2026-08-08 — Built the aurora-forecaster stream-ablation harness (config, DM significance test, HAC fix)

- Fixed `aurora_forecaster/compare.py`'s Diebold-Mariano test to use a
  Bartlett/Newey-West kernel long-run variance estimator (new `max_lag`
  param, explicit or automatic Newey-West 1994 plug-in bandwidth) instead of
  the plain sample-variance form — `h`-step-ahead rolling-forecast origins
  overlap in time and induce serial correlation the plain form understates,
  which would have produced false-positive "significant" ablation results.
  Added a deterministic block-pattern regression test proving the fix
  changes the outcome (`max_lag=0` significant, `max_lag=n-1` not), not just
  that it doesn't break the 4 existing tests (all still pass unchanged).
- Built the config-driven ablation harness end-to-end, TDD throughout (every
  module's tests written and confirmed red before implementation):
  `text_adapter.py` (normalizes GDELT/Alpha Vantage/Currents raw JSON to
  plain text), `text_fetch.py` (network dispatch, `http_get`-injectable),
  `ablation_core.py` (generic `LossSeries`/pairwise-DM-comparison/report —
  zero aurora-specific types, the literal promotion candidate for
  `time-series/forecast_eval/` per today's eval-package-boundary decision,
  see `decisions-archive.md`), and `ablation.py` (aurora-specific
  `StreamConfig` glue: `UNIMODAL`/`GDELT_ONLY`/`CURRENTS_ONLY`/
  `GDELT_CURRENTS` in `STANDARD_CONFIGS`, per-config ledger naming, Alpha
  Vantage excluded from the standing rotation by construction — its 25
  req/day free tier can't sustain a walk-forward loop).
- Extended `ForecastRecord`/`ScoredForecastRecord` with a `text_config`
  field (schema v1→v2, default-valued so old ledger lines parse unchanged —
  verified against the real `artifacts/` files by hand). Added
  `run_multimodal_forecast` to `rolling.py` (the proven
  `multimodal_smoke_test.py` batch-collapse-bug bypass, now reusable).
  Parameterized both `rolling_forecast_btc.py` and `score_forecast_ledger.py`
  on a `STREAM_CONFIG` module constant (default `UNIMODAL` reproduces prior
  behavior byte-for-byte, including the exact existing ledger filenames) —
  no CLI framework added, kept to the project's existing
  "edit-constant-rerun" convention. New `scripts/run_ablation.py` builds and
  writes `artifacts/btc_ablation_report.md`; ran it for real against the
  existing 4-origin unimodal ledger (only config with data so far).
- 102 tests passing (up from 52), ruff clean. Logged the
  evaluation-framework-vs-forecast_eval boundary decision this harness
  follows in `decisions-archive.md`, and cross-referenced it in both
  packages' READMEs.

**Next:** Run `rolling_forecast_btc.py`/`score_forecast_ledger.py` for the
`gdelt`/`currents`/`gdelt+currents` configs (needs `CURRENTS_API_KEY` in
root `.env`) to get real scored ledgers, then `run_ablation.py` for the
actual comparison this whole feasibility test has been building toward.

---
## 2026-08-07 — mean-variance-paper: forward-accumulation Action debugged to a verified green run

- Following the same-day Action build (entry below), the first `workflow_dispatch` test run immediately 422'd: GitHub Actions rejects the `secrets` context directly inside `if:` expressions ("Unrecognized named-value: 'secrets'"). Fixed by promoting the secret to a job-level `env.HEALTHCHECKS_URL` and gating on that instead — this also confirmed the secret itself was wired correctly, since the `/fail` ping fired and returned `OK` from healthchecks.io on this same broken run.
- Second failure: `pip install -r requirements.txt` from repo root broke the file's `-e ../../evaluation-framework` editable path (relative to the requirements file's own directory, not the invocation CWD). Fixed with `working-directory:` on the install step.
- Third failure: `ModuleNotFoundError: No module named 'pyarrow'` — `requirements.txt`'s editable install doesn't pull `evaluation-framework`'s `[freqtrade]` extra that provides it; worked locally only because the existing dev venv happened to already have it installed from an earlier session. Added `pyarrow>=14` to the install step explicitly.
- Fourth failure, the real one: sustained `429 Too Many Requests` from Hyperliquid on funding-history calls. Root cause wasn't just the repeated manual test triggers — raw price/funding data is `.gitignore`d (`*.feather`/`*.parquet`), so a **fresh Actions checkout has no local cache to resume from**, and `download_hyperliquid.py`'s funding fetch starts from Hyperliquid's 2022 epoch for all 9 coins instead of resuming from yesterday's cursor like it does locally — thousands of paginated requests instead of a handful, every single day. Fixed two ways: (1) added `actions/cache@v4` keyed on the `data/hyperliquid` directory so only the first cold-cache run pays the full-history cost, every run after resumes incrementally; (2) hardened `download_hyperliquid.py` itself — added `post_with_retry()` (was previously zero retry logic, just a flat 0.2s inter-page sleep), raised `MAX_RETRIES` to 8 with a 30s backoff cap, and added 1s spacing between per-coin funding requests. The retry/backoff fix benefits the script generally, not just this Action.
- Fifth run (after all four fixes) went fully green: data refresh, retry/cache, `forward_accumulate.py`, and both healthchecks pings all succeeded. Correctly logged `already accumulated 2026-08-07, skipping (N=148)` — today's slot was already filled by the manual local run earlier in the session, so no duplicate commit, exactly the idempotency the state design was supposed to guarantee. Confirmed via `git log origin/main` and the healthchecks.io success ping.
- **Real takeaway generalizing beyond this one workflow:** a script whose local behavior depends on pre-existing local state (here: incremental resume from cached data files) will behave completely differently in a stateless CI environment unless that state is explicitly cached or re-derived. "It works when I run it locally" is not evidence it'll work in the Action — the local venv had months of accumulated cache the fresh runner didn't.

---
## 2026-08-07 — mean-variance-paper: daily forward accumulation automated via GitHub Action + healthchecks.io

- Following the same-day `forward_state.py` fix (see the "fixed forward accumulation" entry below), automated the daily pull instead of relying on remembering to run it manually for ~102 more days: new `.github/workflows/forward-accumulation.yml` (cron `30 1 * * *` UTC + `workflow_dispatch`) checks out the repo, refreshes Hyperliquid OHLCV/funding via `download_hyperliquid.py`, runs `forward_accumulate.py`, and commits the updated `forward_state.json`/`forward_daily_log.jsonl`/`forward_accumulation_ledger.jsonl` straight back to `main` (bot commit, no PR — deterministic numeric state, not judgment-requiring content, unlike the existing `paper-search.yml` PR pattern which is for LLM-generated literature notes).
- Wired healthchecks.io as a dead-man's-switch, mirroring the start/success/fail pattern already used in the user's other repo's `sync-prices.yml`: `HEALTHCHECKS_FORWARD_ACCUMULATION_URL` repo secret (set by the user directly via `gh secret set`, never pasted into the conversation), pinged `/start` before checkout, bare URL on success, `/fail` on failure — each ping guarded so a missing secret doesn't fail the job.
- User enabled Actions "Read and write permissions" (required for the bot's `git push` step; default `GITHUB_TOKEN` is read-only otherwise) and set the healthchecks secret. Not yet verified end-to-end — next step is a manual `workflow_dispatch` run to confirm the ping actually reaches healthchecks.io before trusting the cron schedule.

**Next:** trigger `workflow_dispatch` once and check the healthchecks.io dashboard shows a received ping; then let the daily cron run unattended.

---
## 2026-08-07 — aurora-forecaster: rolling-forecast walk-forward loop built; scoring findings visualized

- Earlier in this session (before another concurrent session built the scoring module below): built the rolling walk-forward forecast loop itself — `aurora_forecaster/rolling.py` (`forecast_origins`, `run_unimodal_forecast`), `forecast_ledger.py` (`ForecastRecord`, append-only JSONL mirroring `evaluation-framework`'s `TrialRecord` pattern), and `scripts/rolling_forecast_btc.py`. Ran it for real: 4 BTC origins (2026-07-19 to 2026-07-31, 96h horizon each) against Binance BTC/USDT, appended to `artifacts/btc_unimodal_forecast_ledger.jsonl`. This is what the scoring module (entry below) then scored.
- After the scoring module landed (`aurora_forecaster/scoring.py`, `scored_ledger.py`, `artifacts/btc_unimodal_forecast_scored.jsonl`, committed `04fe3f7`/`f0d7292` by the concurrent session — verified via `git log`/`git status` before touching anything, wiki files already clean/committed by that session so no reconciliation needed here): built a single-file HTML visualization, `aurora-forecaster/artifacts/btc_unimodal_forecast_chart.html`, joining both ledgers by `forecast_id`. Shows the actual BTC price line against all 4 forecast fans (mean ± std), a forecast-summary table extended with skill/CRPS/MASE per origin, and a calibration panel (nominal-vs-empirical coverage bars for 50/80/95%, mean standardized residual) that makes the overconfidence finding visible at a glance rather than only readable from the JSONL. Local file, not published as a hosted Artifact per user preference this session.
- Dataviz skill's palette validator run against the 5-series set (actual + 4 forecast origins) in both light/dark before use — all hard gates pass; light mode carries a contrast WARN on 3 of the 5 hues, mitigated with the required relief (visible legend labels + the summary table, never color-only identity).

**Next:** `artifacts/` (both JSONL ledgers and the new chart HTML) still isn't in `.gitignore` — undecided whether these should be committed as evidence or treated as regenerable output; flagged in `open-threads.md`.

