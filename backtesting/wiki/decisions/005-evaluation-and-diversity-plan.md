# Decision 005 — Evaluation Tooling, Strategy Diversity, and Principled Writeup Plan

**Status:** active plan
**Date:** 2026-05-16
**Supersedes:** the implicit "build strategies, run backtests, narrate results" workflow that produced `writeup-2026-05-10.pdf`.

---

## 1. Executive Summary

- **Every result card and frontier point gains a tail-shape + path-shape row** (skew, kurtosis, tail-ratio, CVaR-5%, Ulcer Index, Martin ratio). Calmar stops being the only second-moment number we cite.
- **Inter-strategy correlation becomes a first-class metric.** A new `scripts/eval_layers.py` produces a daily-return matrix across all leaderboard ZIPs and reports pairwise correlation + marginal-diversification-benefit (MDB) per candidate. R∧T1/V2/V3 will almost certainly collapse to one effective strategy under this lens; that's the point.
- **Three new strategy families open**, ranked: (1) **pairs/cointegration** (BTC-ETH, BTC-SOL, ETH-SOL spread), (2) **cross-sectional momentum on 7-coin basket** (cheapest PCA-adjacent test that uses existing data), (3) **1h mean-reversion after funding-extreme** (hypothesis #10/#11 in `learnings.md`). Pairs first because it's the only family with a *structurally* different return shape (market-neutral) — i.e. the only one that materially shifts the correlation matrix.
- **The Pareto chart becomes a 3-panel figure**, not a single (bull-return, bear-MDD) scatter. Panel 1: standalone risk/return. Panel 2: tail/path shape (Ulcer vs CVaR). Panel 3: marginal portfolio contribution (MDB vs `corr_to_book`). Status tags from `strategy-taxonomy.md` become marker shape; family becomes color.
- **Capstone (Workstream D): the writeup is rewritten from the principled perspective.** Every claim cites (Calmar, SQN, Ulcer, CVaR-5%, DSR, MDB). At least one non-trend strategy on the frontier. The narrative changes from "we have one paper-trade candidate" to "we have a measured candidate book with quantified diversification."

---

## 2. Workstream A — Evaluation Tooling

### A1 — Tail + path metrics in result cards (1 week)

**Deliverable.** New module `scripts/eval_layers.py` exposing `compute_layer5_metrics(zip_path: Path) -> dict`:

| Metric | Definition | Source |
|---|---|---|
| `skew` | sample skew of daily wallet log-returns | already in `dsr_analysis.py:111` |
| `kurt_excess` | sample excess kurtosis | same |
| `tail_ratio` | abs(P95) / abs(P5) of daily returns; > 1 = right-tailed | new |
| `cvar_5` | mean(daily returns ≤ P5); negative number | new |
| `ulcer_index` | sqrt(mean(drawdown_pct²)) on wallet curve | new — path-aware |
| `martin_ratio` | CAGR / ulcer_index | new |
| `pain_index` | mean(abs(drawdown_pct)) | new — sanity check |

**Steps.**
1. Extract `load_daily_returns` + `load_trade_returns` from `scripts/dsr_analysis.py:73-100` into `scripts/eval_layers.py`. Shared loader.
2. Add the seven functions, each <15 lines, pure functions of a `pd.Series`.
3. CLI `python scripts/eval_layers.py <zip_path>` prints a markdown table to stdout.
4. Update `wiki/results/_template.md:15-27` with a "Layer 5 — Tail/Path shape" sub-table.
5. Backfill the 9 leaderboard runs in `dsr_analysis.py:46-56`. Insert tables into existing result cards — do not rewrite prose.

**Exit criteria.** All 9 result cards have a Layer-5 table. `_index.md` leaderboard at `wiki/_index.md:55-66` gains one new column: **Ulcer Index** (Martin is derivative). One paragraph in `learnings.md` records whether Ulcer disagrees with MDD anywhere — specifically, *does R2 still look killable under Ulcer or did MDD's point-in-time-ness exaggerate today's K1 breach?*

**Dependencies.** None. **Risk.** Low.

### A2 — Inter-strategy correlation matrix (1–2 weeks)

**Deliverable.** `scripts/eval_layers.py` gains `build_corr_matrix(zip_paths, common_window) -> pd.DataFrame` + `marginal_diversification_benefit(candidate, existing_book) -> float`.

**Steps.**
1. **Common window** = intersection of daily-wallet date ranges. Refuse to compute on overlap <90 days. Missing day = flat = 0 return.
2. Pairwise Pearson + Spearman on daily wallet log-returns. Output `wiki/assets/correlation_matrix.png` (heatmap, family-colored labels) and `wiki/results/_correlation_table.json` (machine-readable, mirroring `dsr_analysis.py:189-208`).
3. **MDB score.** For candidate strategy *c* and current book *B* (currently `SmaRegime180` alone), MDB = Sharpe(B ∪ {c}, equal-weight) − Sharpe(B). Positive MDB = candidate worth adding even if standalone Sharpe is lower.
4. Add an **MDB column** to `wiki/_index.md:55` leaderboard. This is the single most important new column — it justifies (or kills) R∧T2/V3 under correlation-aware evaluation.

**Exit criteria.**
- Heatmap rendered, embedded in `README.md` alongside Pareto chart.
- Each leaderboard row shows `corr_to_book` and `MDB`.
- `wiki/methodology/correlation-and-mdb.md` (~80 lines) documents loader assumptions, citing `multi-objective-search.md`'s OOS-stability objective as theoretical precedent.

**Dependencies.** A1's shared loader. **Risk.** Medium. The 0-fill-on-flat-day choice pulls correlations toward zero by construction. Document alternative (NaN + pairwise-complete) and pick one explicitly.

---

## 3. Workstream B — Strategy Diversity

### Ranking principle

Every green frontier strategy is *long, directional, BTC-correlated*. The single highest-leverage diversity move is anything **market-neutral or cross-sectional** — that's what changes the correlation matrix, not another conjunction variant.

| Family | Standalone Sharpe | Diversification | Data ready? | Build cost | Priority |
|---|---|---|---|---|---|
| **Pairs/Cointegration** (BTC-ETH, BTC-SOL, ETH-SOL) | Medium | **High** (market-neutral) | Yes — 7 coins on disk per `_index.md:115` | strategy + preflight script | **B1** |
| **Cross-sectional momentum** on 7-coin basket | Medium | Medium-high | Yes | strategy file | **B2** |
| **1h mean-reversion after funding extreme** | Unknown | Medium (different timescale) | Yes (funding parquets) | strategy + OU calibration | **B3** |
| **Short-bias trend** | Negative-expected | High (anti-correlation) | Yes | trivial | **B4** — only if B1–B3 underwhelm |
| **Vol-targeting overlay** | n/a | Improves Sharpe of *every* strategy | Yes | helper + post-hoc rescale | **deferred to A1.5 if cheap** |
| **CEX-DEX lead-lag** (hyp #6) | Unknown | Low at 1h | **No** — need sub-hour | high | **defer indefinitely** |
| **PCA factor on 7-asset returns** | Unknown | High if factors stable | Yes | medium | **deferred** — B1 is the cheaper test of the same hypothesis |

**Recommendation: build B1, B2, B3 in that order.** Do not build B4–B7 until after A2 ships. DSR pre-registration discipline (`cv-and-deflation.md:71-87`) applies: pre-register kill criteria *before* each backtest.

### B1 — Pairs / cointegration (1.5 weeks)

**Why first.** Only family that breaks β-correlation to BTC by construction. Maximum information per unit work for the writeup.

**Spec.**
- Pair candidates: BTC-ETH, BTC-SOL, ETH-SOL on 4h.
- Preflight `scripts/cointegration_preflight.py`: rolling Engle-Granger on 1000-bar window across 7-coin universe. Parquet of (pair, window_start, p_value, hedge_ratio, half_life). Filter p < 0.05 AND OU half-life 12h–10d.
- `user_data/strategies/PairsZScore.py`: enter at |z| > 2 of (log P_A − β log P_B); exit at z = 0 or stop at |z| > 4 or time-stop = 3 × half-life. β refit weekly on prior 60d only.
- Freqtrade quirk: single-instrument-per-trade by default. Implement as **synthetic spread** — compute spread series via `informative_pairs`, trade BTC leg alone with size set by z-score. Document modeling gap in result card.
- Pre-register `decisions/006-kill-criteria-pairs.md` before backtest: MDD > 8%, half-life drift >3× rolling median, cointegration p > 0.20 for 30 consecutive days.

**Exit criteria.**
- One PairsZScore result card with standalone Calmar/SQN **and** `corr_to_SmaRegime180` + MDB.
- Cointegration preflight parquet committed.
- If standalone Calmar < 2 but `corr < 0.2` and MDB > 0.1, strategy graduates under new correlation-aware rule (C1).

**Dependencies.** A2 must ship first. **Risk.** High on Freqtrade-mechanics; medium on edge (BTC-ETH cointegration is fragile post-2021). If preflight finds zero stable pairs, pivot to B2 same week.

### B2 — Cross-sectional momentum (1 week)

**Spec.** At each 4h bar, rank 7 coins by 7-day return; long top-2, short bottom-2 (or long-only top-2 if short-funding adverse). Rebalance every 24 bars. Equal-weight. This is a degenerate 1-factor PCA where the factor is "return rank" — fastest test of the cross-sectional thesis.

**Exit criteria.** Standalone + MDB on leaderboard. Drop if MDB < 0.05 vs (T3 ∪ B1). Pre-registered kill criteria in `decisions/007-kill-criteria-cross-sectional.md`.

**Dependencies.** A2. **Risk.** Low.

### B3 — Funding-extreme mean-reversion (1 week)

**Spec.** Implements `learnings.md` #10 + #11. OU-calibrate funding series per coin from `user_data/data/hyperliquid/funding/`. Entry when funding z-score > 2: **counter-funding** position (short if funding pays longs), time-exit at 3 bars (4h).

**Exit criteria.** Standalone + MDB. Pre-registered MDD > 4% in `decisions/008-kill-criteria-funding-mr.md`.

**Dependencies.** A2. Independent of B1/B2. **Risk.** Medium. 8h OU half-life means ~2 bars decay per trade — tight signal/noise.

---

## 4. Workstream C — Pareto Frontier Reframing

### Decision: 3-panel figure, not single-panel rethink

Keep current panel 1 (kill-criteria-anchored). Add two new panels. Rejected: single radar/parallel-coordinate chart over 6 metrics — denser but worse for at-a-glance frontier reading.

### C1 — Status-tag integration + frontier semantics rewrite (3 days)

1. Add `status: str` to `@dataclass Strategy` in `generate_pareto_chart.py:43-56`, matching `strategy-taxonomy.md:9` tags.
2. Marker shape: ★ = filled diamond, ▲ = filled circle, ~ = open circle (dashed edge), ✗ = X. Family color stays. Universe demoted to marker size hint or annotation.
3. **Frontier definition changes.** `pareto_frontier` at `generate_pareto_chart.py:126-143` becomes: geometric frontier AND (DSR > 0.5 OR MDB > 0.1 vs current book). Geometric-but-DSR-fails points still render with hollow markers — visually present, statistically flagged. Directly addresses the "DSR flags everything as NOISE" tension in `strategy-taxonomy.md`.

**Exit criteria.** Panel 1 visually distinguishes ★ (T3) from ▲ (R∧T) from ✗ (R2 today). Eyes find paper-trade candidate in 1s.

### C2 — Panel 3: correlation/MDB (4 days, depends on A2)

**Spec.** x = `corr_to_SmaRegime180`, y = `MDB`. Bubble size = standalone Calmar. Diagonal annotation: MDB > 0 + corr < 0.5 = "portfolio-additive quadrant" — frontier-worthy even with low standalone Calmar.

**Why this is the actual reframing.** Strategy *dominated on standalone* can be *non-dominated as portfolio addition*. Panel 3 makes this visible without rewriting panels 1–2.

**Exit criteria.** B1/B2/B3 land on panel 3 with meaningful MDB. Writeup says "we kept B1 despite Calmar 1.4 because MDB 0.18 vs T3" — principled, not narrative.

### C3 — Optional panel 4: Ulcer vs CVaR-5% (deferred)

Skip unless A1 surfaces a strategy where Ulcer and MDD strongly disagree. R2 today is a candidate (MDD 11.05% point-in-time vs Ulcer of one event, not chronic bleed).

---

## 5. Workstream D — Principled Writeup Rewrite (capstone)

The whole plan exists to enable this. Phase D is **non-optional**; it's how we prove the buildout was worth it.

### D1 — Outline + new sections (2 days)

Draft `writeup-2026-XX-outline.md` against the new evidence. Required sections that the current writeup lacks:

- **Methodology spine**: a 1-page summary of the evaluation stack (Layers 2–6) and the decision rule (DSR + MDB + held-out gates jointly). Cite `methodology/cv-and-deflation.md` and the new `methodology/correlation-and-mdb.md`.
- **Family map first**: open with `strategy-taxonomy.md`'s family structure, not with a leaderboard. Family > individual strategy.
- **Layer-5 table** for every quantitative claim. No more "Calmar 7.23" alone; instead "Calmar 7.23 | Ulcer 0.71 | CVaR-5% −1.8% | Martin 4.0 | DSR 0.83 | MDB n/a (is book)".
- **Correlation heatmap** of the leaderboard. Almost certainly shows R∧T1/V2/V3 collapse to one effective strategy — that's the point.
- **MDB-justified frontier**. Each frontier strategy listed with standalone metrics *and* MDB vs current book.
- **3-panel Pareto chart** with status tags.
- **At least one non-trend family on the frontier** (B1, B2, or B3).
- **Pre-registration ledger.** Each strategy links to `decisions/00N-kill-criteria-<strategy>.md`. Strategies without one flagged "pre-DSR era — research only."

Sections to cut or shorten:
- V1/V2/V3 sizing exploration → one paragraph: "Three sizing variants of R∧T; correlation matrix shows they are one effective strategy."
- Current "DSR flags everything as NOISE" humility section → reframed. DSR alone is too strict at low N; DSR + MDB + held-out jointly is the principled gate.

### D2 — Draft, review, ship (3 days)

Markdown → PDF via existing toolchain. Land as `writeup-2026-MM-DD.md` (date of completion) at repo root, replacing `writeup-2026-05-10.pdf` as the canonical writeup. Old PDF stays in repo for history.

**Exit criteria.** Writeup reads as a principled study, not a narrative log. A reader unfamiliar with the project can answer in under 2 minutes:
1. What evaluation criteria do you use?
2. What strategies do you have, and how do they relate?
3. Which strategy is your live candidate, and why?
4. What's on your frontier and why is each point there?
5. What did you rule out and on what evidence?

---

## 6. Cross-Workstream Sequencing

```
Week 1:    A1   — tail/path metrics + result-card backfill
Week 1.5:  A1.5 — re-backtest all existing strategies on Binance 5-coin window 2020-09 → 2026-05
Week 2-3:  A2   — correlation matrix + MDB (3 schemes: eq, rp, mv)  ──┐
Week 4:    C1+C2 — status tags + MDB panel                            ┘ ← A2 unlocks C2
Week 5:    B1.1 — cointegration preflight + decisions/006
Week 6-7:  B1.2 — PairsZScore (two-leg informative_pairs) + result card + frontier insertion
Week 8:    B2   — cross-sectional momentum
Week 9:    B3   — funding-extreme MR
Week 10:   D1   — writeup outline
Week 11:   D2   — writeup draft + ship
```

**A1.5 — Re-backtest on common window (locked in by pre-decision Q2).** Every existing strategy in `strategy-taxonomy.md` (T0-T3, R1, R2, R2-multi, C1, R∧C1, R∧T1/V2/V3 — 11 runs) gets re-run on the global intersection window Binance 2020-09-23 → 2026-05-09. Required because:
- The correlation matrix in A2 needs return series on a common window.
- Existing result cards mix Hyperliquid bear (~6mo) and Binance bull/cross-cycle (varies) — not directly comparable.
- Some strategies were tuned on Hyperliquid; running them on Binance is itself a robustness signal (the "did this generalize" question).

A1.5 deliverable: 11 new ZIPs under `user_data/backtest_results/`, one summary table appended to `_index.md` as "Binance 5-coin common-window leaderboard" alongside the existing Hyperliquid-bear leaderboard. Result cards updated with a `## Binance 5-coin re-run` section (do not overwrite original Hyperliquid sections).

**Pairs (B1.2) is now 2 weeks not 1** due to two-leg `informative_pairs` plumbing per pre-decision Q4.

**Total timeline: ~11 weeks** (was 9), reflecting locked-in pre-decisions.

**Why this order.** A1+A2 are *measurement infrastructure*; strategies built before them get re-evaluated anyway. B without MDB is just "more strategies"; with MDB it's "principled diversification." C without A2 has no panel-3 data. D ships only after the evidence base is in place.

**Acceptable interleave.** If A1 takes <3 days, start the **cointegration preflight script** (B1.1, pure data analysis) in parallel during week 2. Preflight doesn't need MDB.

---

## 7. Pre-Decisions (locked in 2026-05-16)

1. **Annualization basis** = **365 days** for all crypto Sharpe/Sortino/Calmar/DSR. Applied consistently in `eval_layers.py` and `dsr_analysis.py:152`.
2. **Correlation window** = **global intersection 2020-09-23 → 2026-05-09** (5.6y, 5 coins: BTC/ETH/SOL/AVAX/DOGE). ARB joins from 2023-03 — used only in pair-family runs where ARB is explicitly involved. Hyperliquid bear (~6mo) reported as a separate sub-window matrix, not part of the global matrix. Every strategy gets re-backtested on the Binance 5-coin window; correlation matrix computed from those re-runs.
3. **MDB book composition** = auto-updates as the ★ set changes. Today: book = {SmaRegime180}. After any new strategy graduates to ★, MDB is recomputed against the expanded book. Document this update protocol in `methodology/correlation-and-mdb.md`.
4. **MDB book weighting** = **compute all three** (MDB-eq, MDB-rp, MDB-mv). **MDB-rp** (risk-parity, 90d vol) is the leaderboard headline. Result cards show all three plus a "robust" flag = positive across all three. MDB-mv flagged as "upper bound, expect instability at small N."
5. **Pre-registration discipline** = **non-negotiable**. Every new strategy gets `decisions/00N-kill-criteria-<strategy>.md` *before* its first backtest, following the `decisions/004` template. No exceptions.
6. **Held-out window** = **forward reserve Binance 2026-06-01 → 2026-12-31**. Do not download this window until D2 ships. After D2, download once and run B1/B2/B3 + the current ★ set against it as a one-shot final check. Document the result in the writeup verbatim — no re-runs, no parameter tweaks after seeing the held-out result.
7. **Freqtrade pairs mechanics** = **two-leg via `informative_pairs`** (full fidelity). Accept the +1 week of plumbing as the cost of getting a clean spread P&L. The single-leg synthetic approach was rejected because it would underestimate pairs P&L by ~half and confound the MDB comparison against other strategies.

---

## 8. Files Referenced

Implementation touchpoints:
- `scripts/dsr_analysis.py:73-100, 152, 189-208` — share loader, share annualization, share JSON output pattern
- `scripts/generate_pareto_chart.py:43-56, 62-123, 126-143` — add status field, frontier rule, MDB panel
- `wiki/_index.md:55-66` — leaderboard column additions (Ulcer, MDB)
- `wiki/results/_template.md:15-27` — add Layer-5 sub-table
- `wiki/decisions/004-kill-criteria-sma-regime-180.md` — template for kill-criteria pre-registration
- `../wiki/methodology/multi-objective-search.md:31-43` — Pareto-objectives rationale
- `../wiki/methodology/cv-and-deflation.md:44-69` — DSR/PBO/held-out gate

New files this plan creates:
- `scripts/eval_layers.py`
- `scripts/cointegration_preflight.py`
- `user_data/strategies/PairsZScore.py`
- `user_data/strategies/CrossSectionalMomentum.py`
- `user_data/strategies/FundingExtremeMR.py`
- `wiki/methodology/correlation-and-mdb.md`
- `wiki/decisions/006-kill-criteria-pairs.md`
- `wiki/decisions/007-kill-criteria-cross-sectional.md`
- `wiki/decisions/008-kill-criteria-funding-mr.md`
- `writeup-2026-MM-DD.md` (D2 deliverable; replaces `writeup-2026-05-10.pdf` as canonical)
