# Project Status

Priority: reusable package (`evaluation/`) first, methods paper second
(decided 2026-08-06). The paper resumes only once the package has results
worth reporting; writing it first would front-run literature and code that
already moved past the May draft.

## Current state (2026-08-06)

- **Package: installable and tested.** `pip install -e ".[dev,freqtrade,factor]"`,
  150 tests, 96% coverage, clean ruff/black/mypy, CI at
  `.github/workflows/evaluation-framework-ci.yml`. All six planned phases
  (ledger, PBO/bootstrap, purged splits + sealed holdout, funding-aware
  costs, benchmark/factor/regime + live reconciliation, docs) are done —
  see `PLAN.md` and `evaluation/README.md`'s module map.
- DSR: kurtosis carve-out removed, trial-count derivation fixed, and (found
  while re-running the DSR-vs-PBO head-to-head) narrow-family `sharpe_var`
  under-estimation fixed — 2026-08-06, see `../wiki/decisions-archive.md`
  and `evaluation/dsr.py`.
- The 2026-06-01 through 2026-12-31 forward window is sealed —
  `freqtrade-experiment/hmm-slope-experiment/analysis/holdout_seals.jsonl`
  via `evaluation.holdout`. No downloader for that window exists yet; when
  one is written it must call `guard()` before inspecting the data.
- Manuscript/essay/worked-example: archived, not deleted —
  `archive/manuscript-2026-05/`. Stale relative to the 2026-08-05
  literature scan and the `HmmSmaSlopeV2` live failure; do not cite them
  as current.

## Evidence reconciled

- `HmmSmaSlopeV2` paper run: `evaluation.live.reconcile()` now returns a
  permanent regression-tested verdict — `INCOMPLETE` for the original
  30-day/2-trade gate (below the pre-registered 5-trade minimum) and
  `FAIL` for the extended run (21 trades, -3.54%, eleven-loss streak against
  a six-loss kill threshold). See `evaluation-framework/tests/test_live.py`.
- DSR vs PBO head-to-head run on the real HmmSmaSlope family (bull window):
  both deflators agree — NOISE / PBO=0.171 — once trial count and
  cross-trial variance are pulled from a real ledger rather than the
  wallets under test. See
  `freqtrade-experiment/hmm-slope-experiment/research/analysis/reports/2026-08-06-pbo-vs-dsr.md`.

## Next up

- Package is feature-complete against the original plan. Remaining
  optional items: SPA/Reality Check (sources inaccessible — see
  `evaluation/pbo.py`), real order-book capture for `stress.py`.
- Re-open the methods paper only after the package produces a further
  package-vs-literature-backed result worth writing up.
