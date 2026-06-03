# Decision 010 — Paper plan, deferred until project matures

**Status:** deferred (intent captured; writing blocked)
**Date:** 2026-05-16

## What this is

A capture-the-intent memo, not a draft. The eventual artefact for this project is a methodology paper. We choose to defer writing it until the empirical scaffolding strengthens.

## Why defer

The paper's strongest claim is "this evaluation framework identifies a candidate book that holds up on data the authors never touched." That claim requires:

1. **Forward held-out window** (Binance 2026-06 → 2026-12, locked by decision 005 pre-decision Q3). Currently untouched and must remain so until this sprint completes.
2. **30-day paper-trade dry-run** for the candidate book {T3, R∧T2} on Hyperliquid (per decision 004 / 005 next-sprint).
3. **Decision 009** — portfolio-aware K1. The R∧T2 "K1 breach is portfolio-justified" framing is currently informal; it needs to be codified before review. ✅ 2026-05-16 — decision 009 codifies the portfolio-aware K1 rule.
4. **Two-leg PairsZScore v2** — pre-decision Q4 was overridden to single-leg in the 2026-05-16 sprint. Either the v2 implementation rescues X1 (changes results) or confirms the killed verdict (strengthens it). Either way the result changes the paper. ✅ 2026-05-16 — `PairsZScoreV2` (SOL+DOGE, two-leg, equal-dollar) shipped and backtested on the 5.5y common window: +3.04% / Calmar 0.97 / MDD 2.91% / 13 trade-legs. **Verdict strengthened (not rescued)** — SOL leg is directional alpha during 2021/2024 SOL runs; DOGE leg loses 7/8 trades to per-leg −10% stops before joint z-score reverts. Adds a framework finding: Freqtrade can't express atomic pair trades because stops are per-instrument, not per-spread. See `wiki/results/2026-05-16-pairs-zscore-v2.md`.
5. **Extend Binance funding parquets to full 5.5y** — currently 2.3y of 5.5y, which truncates C1 and F1 evaluation. Re-running these on full history may move them between categories. ✅ 2026-05-16 — done. Parquets backfilled to 2020-09-23 → 2026-05-09 for all 5 coins. C1 re-run: +32.44% / Calmar 1.93 / MDD 15.65% (real standalone edge but MDD still kills it). F1 re-run: −11.60% / Calmar −0.32 / MDD 33.51% (stays killed; not a truncation artefact). See `wiki/results/2026-05-16-funding-carry-fullwin.md` and `wiki/results/2026-05-16-funding-extreme-mr-fullwin.md`.

Writing now means writing twice. Each of the five items above rewrites at least one section of the paper. Better to write once, after the project is mature.

## Target

- **Format**: ACM `acmart` `sigconf` style, two-column.
- **Length**: 6-8 pages excluding references.
- **Venue (when ready)**:
  - First-line: **ICAIF** (ACM AI in Finance) — workshop or main track.
  - Second-line: NeurIPS Workshop on AI in Finance.
  - Fallback: **arXiv preprint** (no venue lock-in; cite-able immediately).
- **Bibliography**: assembled from `wiki/papers/` (≥10 papers already curated).

## Structure (when written)

1. Abstract (150w)
2. Introduction — practitioner gap (Sharpe/Calmar alone is the norm); contribution (layered evaluation + multi-scheme MDB + cross-cycle validation + pre-registration as multi-testing defense)
3. Related work — DSR (López de Prado 2014), regime detection HMM, funding-rate carry literature, slippage-at-risk, backtest-vs-live divergence
4. Data and substrate — Binance perp, 5.5y common window, 5-coin universe, fees, Freqtrade
5. Methodology — layered evaluation stack with formal definitions, MDB-eq/rp/mv with equations, pre-registration framework
6. Strategy taxonomy — six families (T / R / C / R∧T / R∧C / X / F)
7. Experimental setup — common window, walk-forward refits, pre-flight gates
8. Results — common-window leaderboard, correlation matrix, MDB ablation, candidate book, **forward held-out (after sprint)**
9. Discussion — portfolio-aware K1, negative results' value, pre-registration as multi-testing defense
10. Limitations
11. Future work
12. References

## Figures (already available)

- `wiki/assets/correlation_matrix.png` — strategy correlation heatmap (will need serif re-render for publication)
- `wiki/assets/pareto.png` — 3-panel Pareto chart (Calmar/MDD, Martin/Ulcer, MDB/corr)
- **To create**: MDB scheme ablation chart (showing where MDB-eq, MDB-rp, MDB-mv disagree)
- **To create**: Layer-5 catches Calmar lie — a worked example showing FundingCarry or R2 by Calmar vs by Ulcer/Pain

## Tables (already available)

- Common-window leaderboard (`_index.md`)
- MDB results across schemes (`_correlation_table.json`)
- Pre-registered kill criteria summary (across decisions 004 / 006 / 007 / 008)

## Pre-conditions for writing

In order:

1. [x] Decision 009 (portfolio-aware K1) is written and applied. (2026-05-16: written; combined-book MDD_rp = 2.12% confirmed via `scripts/combined_book_mdd.py`.)
2. [x] Two-leg PairsZScore v2 ships and X1 is re-evaluated. (2026-05-16: shipped, X1 kill strengthened, framework limit recorded.)
3. [x] Binance funding parquets extended to 5.5y; C1 and F1 re-run on full window. ✅ 2026-05-16 — see `wiki/results/2026-05-16-funding-{carry,extreme-mr}-fullwin.md`.
4. [ ] 30-day Hyperliquid paper-trade dry-run for {T3, R∧T2} completes; result documented.
5. [ ] Forward held-out window (Binance 2026-06 → 2026-12) downloaded and run once; result documented verbatim (no parameter tweaks).

After step 5, write the paper in 1-2 focused sessions and post to arXiv. Hold conference submission for a second editorial pass.

## What is NOT pre-conditioned

- The article series (`backtesting/wiki/course/` parallel to `feishu/wiki/course/`). This serves a different audience (blog / casual) and can be written independently when motivation strikes. Not on the critical path.

## Cross-references

- `wiki/decisions/004-kill-criteria-sma-regime-180.md` — original K1 definition
- `wiki/decisions/005-evaluation-and-diversity-plan.md` — pre-decisions and overall plan
- `wiki/decisions/006-kill-criteria-pairs.md` — pairs kill criteria (and the K1 = 8% precedent)
- `wiki/decisions/007-kill-criteria-cross-sectional.md`
- `wiki/decisions/008-kill-criteria-funding-mr.md`
- `wiki/methodology/correlation-and-mdb.md`
- `writeup-2026-05-16.md` (the dense internal writeup that will serve as the prose substrate for the paper)
