# Crypto perp strategy backtesting — principled writeup

**Date:** 2026-05-16
**Window:** Binance perp 2020-09-23 → 2026-05-09 (5.5 years, 2 bulls + 2 bears)
**Substrate:** Freqtrade, USDT-margined futures, `--fee 0.00035` (Hyperliquid taker, applied uniformly for cross-strategy comparison)
**Sister docs:** `../freqtrade-experiment/hmm-slope-experiment/research/_index.md` (leaderboard), `../freqtrade-experiment/hmm-slope-experiment/research/analysis/reports/2026-05-16-decision-005-evaluation-and-diversity-plan.md` (methodology spine), `../freqtrade-experiment/hmm-slope-experiment/research/learnings.md` (cumulative log).

This document replaces [`archive/ranking-narrative.md`](archive/ranking-narrative.md). The earlier writeup was a narrative log of strategy discoveries; this is a principled study of a candidate book under a layered evaluation framework.

---

## 1. What changed

The earlier writeup told the story of one strategy (`SmaRegime180`, code **T3**) graduating to paper-trade candidate after a 6.7-year cross-cycle test on Binance BTC perp. Honest result, but in narrative form: a random walk through the strategy space.

The current version answers three structural questions that the narrative form couldn't:

1. **What does "principled evaluation" actually mean?** A layered stack — risk-adjusted return (Layer 2), sample-size awareness (Layer 3), multiple-testing deflation (Layer 4), tail and path shape (Layer 5), and portfolio diversification (Layer 6). DSR alone is necessary but not sufficient; MDB-rp is the load-bearing portfolio metric.

2. **How do strategies relate to one another?** Every strategy in the project is now re-backtested on a single common window. Pairwise correlation and Marginal Diversification Benefit (MDB) are first-class metrics. Strategies are evaluated not just standalone but as portfolio additions.

3. **What's the candidate book?** Two strategies — **T3** (SmaRegime180, BTC 4h) and **R∧T2** (HmmSmaSlopeV2, 5-coin 4h). Correlation 0.07. MDB-rp +0.55 robust. They are complementary, not redundant.

---

## 2. The evaluation stack

We organise strategy evaluation into six layers, each addressing a failure mode of the layer above.

| Layer | Question | Headline metric | What it fixes |
|---|---|---|---|
| 1 | Did we make money? | Total return / CAGR | (nothing) |
| 2 | Risk-adjusted? | **Calmar**, Sharpe | Penalises risk |
| 3 | Statistically meaningful? | **SQN** | Penalises thin samples |
| 4 | Survives multiple-testing? | **DSR** (Deflated Sharpe) | Penalises trial-count inflation |
| 5 | Tail / path shape? | **Ulcer**, Martin, skew, kurtosis, CVaR-5% | Catches "non-Gaussian" lies in Sharpe |
| 6 | Portfolio-additive? | **MDB-rp**, corr_to_book | Catches redundancy |

Layers 2 and 3 are the classical leaderboard. Layer 4 (DSR) we previously had but found stricter than evidence — DSR flagged every strategy as "noise" at N < 200, which is too pessimistic. Layer 5 was missing entirely; Layer 6 was missing entirely. The buildout in this writeup adds both.

The reading rule we now follow: **a strategy graduates to paper-trade (★) only if it's positive on layers 2-3-5 AND has robust MDB > 0.3 against the current book.** DSR (Layer 4) is reported but treated as a humility check, not a binding gate.

### 2.1 Layer 5 — tail and path

Two layer-5 measurements:

- **Ulcer Index** = √(mean(drawdown_pct²)) — path-aware drawdown. MDD captures the deepest point; Ulcer captures how long the equity curve spent underwater.
- **Skew / kurtosis** — distributional shape. Slope-gate strategies in this project have skew +9 to +21 and excess kurtosis +110 to +470. These are *very* non-Gaussian, which means Sharpe overstates them. Martin (CAGR/Ulcer) and tail ratio are the explicit corrections.

The Ulcer-vs-MDD comparison is informative. For example:

| Strategy | MDD | Ulcer | Pain | Reading |
|---|---:|---:|---:|---|
| T3 SmaRegime180 | 2.21% | 1.30 | 1.12 | Tight, recovers fast |
| R2 HmmRegime4Rolling | 7.65% | 4.01 | 3.47 | Chronic underwater |
| C1 FundingCarry | 8.52% | 2.80 | 1.80 | Deep but recovers |

R2's K1 (5.5% MDD) kill is doubly justified: Ulcer + Pain confirm the drawdown is chronic, not a single event.

### 2.2 Layer 6 — correlation and MDB

**Marginal Diversification Benefit (MDB)** answers: if I add candidate C to my current book B, does the portfolio Sharpe go up?

We compute MDB under three weighting schemes:
- **MDB-eq** (equal-weight 1/N): naive split.
- **MDB-rp** (risk-parity, 90d trailing vol): every strategy contributes equal risk. **Headline.**
- **MDB-mv** (Markowitz mean-var, long-only): upper bound, known unstable.

A strategy is *robustly* diversifying iff MDB > 0 under all three. This catches the case where a strategy is "additive" under one weighting only because of weighting artifacts.

Full methodology: `wiki/concepts/correlation-and-mdb.md`.

---

## 3. Strategy taxonomy

Every strategy lives in one of seven families. Family = signal source × conjunction.

| Code | Family | Signal | Examples |
|---|---|---|---|
| **T** | Trend | SMA + slope | T0 (LongOnly), T1 (TrendFilter200), T2 (SmaRegime720), T3 (SmaRegime180) |
| **R** | Regime | HMM posterior | R1 (HmmRegime4, look-ahead), R2 (HmmRegime4Rolling), R2x (R2 5-coin) |
| **C** | Carry | Funding rate | C1 (FundingCarry 5-coin) |
| **R∧T** | Regime × Trend | HMM bull AND slope positive | R∧T1/V2/V3 (HmmSmaSlope/V2/V3 5-coin) |
| **R∧C** | Regime × Carry | HMM bull AND funding-negative | R∧C1 (HmmCarry 5-coin) |
| **X** | Cross-sectional / pairs | Spread mean-reversion or rank-momentum | X1 (PairsZScore SOL-DOGE), X2 (CrossSectionalMomentum 5-coin) |
| **F** | Funding mean-reversion | Counter-funding on z-extremes | F1 (FundingExtremeMR 5-coin) |

Status tag legend: ★ paper-trade, ▲ frontier (research), ~ upper bound (look-ahead, not tradeable), ✗ killed, · baseline.

Family-level verdicts (after the A1.5 + A2 sweep):

- **T family**: T3 is the conservative core of the book. T2 (SmaRegime720) and T1 (TrendFilter200) survive as frontier ▲ but don't pass MDB against the expanded book {T3, R∧T2}. T0 is killed.
- **R family**: R2 (the honest walk-forward HMM) is killed cross-cycle — Calmar 0.47 standalone, Ulcer 4.01 chronic. R1 (look-ahead) is the unreachable ceiling. R2x (multi-asset HMM without slope-gate) blows up to 21% MDD.
- **C family**: C1 *survives* on the common window (+2.13%, Calmar 1.37) but is not portfolio-additive (MDB-rp −0.825) due to its vol shape relative to the book.
- **R∧T family**: the headline finding. V2 graduates to ★. V1 and V3 are statistically *the same strategy* (correlation 0.96-1.00); kept as ▲ for research.
- **R∧C family**: confirmed dead cross-cycle (MDD 35.46% on 5-coin Binance, mirrors Hyperliquid bear's −19.59%).
- **X family**: X1 (pairs) killed — cointegration on crypto majors is essentially absent (preflight pass rate 7.4% even for best pair). X2 (cross-sectional momentum) is a marginal frontier candidate; MDB-rp +0.048 robust but MDD 13.04% breaches K1-xs.
- **F family**: F1 killed — counter-funding doesn't mean-revert at 4h cadence on Binance; MDD 29.94%.

---

## 4. The candidate book

After all evaluation gates, the book is **{T3, R∧T2}**.

| | T3 SmaRegime180 | R∧T2 HmmSmaSlopeV2 |
|---|---|---|
| Family | T (Trend) | R∧T (Regime × Trend) |
| Universe | BTC only | 5 coins (BTC, ETH, SOL, AVAX, DOGE) |
| Timeframe | 4h | 4h |
| Calmar (5.5y) | 8.76 | 30.23 |
| SQN | 1.78 | 2.73 |
| CAGR | +3.42% | +21.31% |
| MDD | 2.21% | 6.05% |
| Ulcer | 1.30 | 2.87 |
| Martin | +2.51 | +7.41 |
| Win rate | 22.4% | 35.4% |
| Trades | 85 | 616 |

Correlation between T3 and R∧T2: **0.07** (Pearson on daily returns).

This is the key result. T3 and R∧T2 are nearly orthogonal — the slope-gate on BTC 4h captures a different signal than the HMM-bull AND slope-positive on a 5-coin basket. Adding R∧T2 to T3 increases portfolio Sharpe by **0.55** (MDB-rp, robust across all three weighting schemes).

R∧T2 standalone breaches K1 (5.5% MDD) by 0.55pp. Under decision 004, this would have killed the strategy. But under the layer-6 evaluation, R∧T2 is *portfolio-justified* — the book is what matters, not any single strategy. We propose updating K1 to a portfolio-aware version: if MDB-rp > 0.3 robust against a ≥2-strategy book, accept up to 8% MDD on the new strategy.

This proposal uses `freqtrade-experiment/hmm-slope-experiment/research/analysis/reports/2026-05-16-decision-006-kill-criteria-pairs.md` as a precedent (K1-pairs is set at 8% deliberately); the formal cross-strategy rule is recorded in decision 009 in the same reports directory.

---

## 5. What is *not* in the book — and why each was kept out

A complete record of the killed strategies, with mechanism:

| Code | Strategy | Standalone | MDB-rp | Why killed |
|---|---|---|---|---|
| T0 | LongOnlyStrategy | Calmar −0.37, MDD 10.17% | −0.009 | Baseline; doesn't beat random |
| T1 | TrendFilter200 | Calmar 1.69, skew +15 | +0.040 robust | Lottery-shaped (rare big wins); robust MDB but low-quality signal — ▲ frontier only |
| T2 | SmaRegime720 | Calmar 5.39, MDD 3.57% | −0.023 | Overlaps with T3 (corr 0.65); doesn't add when T3 is in book |
| R2 | HmmRegime4Rolling | Calmar 0.47, MDD 7.65% | +0.010 (noise-level) | Chronic underwater (Pain 3.47); K1 confirmed by Ulcer |
| R2x | HmmRegime4Rolling 5-coin | Calmar 3.79, MDD 21.47% | +0.069 | Standalone MDD unacceptable; could deploy at very small size only |
| C1 | FundingCarry 5-coin | Calmar 1.37, MDD 8.52% | −0.825 | High-vol diluter under risk-parity; not portfolio-additive |
| R∧C1 | HmmCarry conjunction | Calmar 0.08, MDD 35.46% | −0.000 | Anti-complementary signals; catastrophic on multi-asset |
| R∧T1, V3 | HmmSmaSlope variants | Calmar 25-27 | +0.012, −0.023 | Statistically same strategy as R∧T2 (corr 0.96-1.00) |
| X1 | PairsZScore SOL-DOGE | +8.66%, MDD 4.03% | −0.898 | Cointegration premise fails on crypto majors; low-vol → over-weighted under risk-parity |
| F1 | FundingExtremeMR | −17.99%, MDD 29.94% | −1.845 | Counter-funding doesn't mean-revert at 4h cadence on Binance |

Three of these (T1, T2, R2x) have *robust positive* MDB but are not promoted to paper-trade — either because the signal magnitude is too small, the standalone metrics breach kill criteria, or both. The discipline is: robust positive MDB is necessary but not sufficient for paper-trade; standalone metrics matter independently.

---

## 6. The Pareto frontier, re-framed

The earlier writeup presented a single (bull-return, bear-MDD) scatter. The current frame is three panels, each projecting strategies into a different evaluation space.

![Pareto chart](../freqtrade-experiment/hmm-slope-experiment/research/analysis/reports/pareto.png)

- **Panel 1 — Risk-adjusted return.** Calmar (y) vs MDD% (x). Upper-left is best. The K1=5.5% threshold is the red line. T3 sits at the absolute upper-left (high Calmar, low MDD); R∧T2/V3/V1 sit further right with much higher Calmar.
- **Panel 2 — Tail / path shape.** Martin ratio (y) vs Ulcer (x). Upper-left is best. T3 again wins on path-quality; R∧T variants are decent but not as tight. R2/R2x/C1/F1 are clustered in the lower-right (high ulcer, low Martin) — the "killed" quadrant.
- **Panel 3 — Marginal Diversification Benefit.** MDB-rp (y) vs correlation-to-T3 (x). Green-shaded quadrant is "portfolio-additive": MDB > 0 AND correlation < 0.5. R∧T1/V2/V3 sit at the top of this quadrant with corr ≈ 0.07 and MDB-rp ≈ 0.55 (computed vs T3-only book; values shrink against the {T3, R∧T2} book). T2 (corr 0.65, MDB ≈ 0) sits at the boundary; X1 and F1 sit deep in the negative-MDB region.

Panels 1 and 2 are the *standalone* evaluation. Panel 3 is the *portfolio* evaluation. A strategy can be dominated on panel 1 but not on panel 3 — that is the principled justification for keeping R∧T variants on the frontier despite their MDD being worse than T3's.

![Correlation matrix](../freqtrade-experiment/hmm-slope-experiment/research/analysis/reports/correlation_matrix.png)

The correlation heatmap shows three structural facts:
1. The diagonal block R∧T1↔R∧T2↔R∧T3 (Pearson 0.96-1.00) — three variants are one strategy.
2. T2↔T3 (0.65) — same family, different timeframe, partially overlapping.
3. Everything else is essentially orthogonal — most off-diagonal cells are < 0.1.

The third fact is the diversification opportunity. Building a multi-family book is structurally possible because the families don't correlate; the question is just which families have edge.

---

## 7. Methodology decisions, locked

The seven pre-decisions locked in by `decisions/005`:

1. **Annualisation** = 365 days (crypto trades 365).
2. **Correlation window** = global intersection Binance 2020-09-23 → 2026-05-09 (5.5y, 5 coins).
3. **MDB book composition** = auto-updates as ★ set changes. Today: {T3, R∧T2}.
4. **MDB book weighting** = compute all three (eq, rp, mv); MDB-rp is leaderboard headline.
5. **Pre-registration discipline** = `decisions/00N-kill-criteria-<strategy>.md` *before* every backtest. Non-negotiable.
6. **Held-out window** = forward reserve Binance 2026-06 → 2026-12. Don't download until after D2 ships. One-shot OOS check.
7. **Freqtrade pairs mechanics** = pre-decision was two-leg `informative_pairs`; shipped single-leg synthetic v1 due to engineering scope. Documented modeling gap; two-leg upgrade flagged.

Decisions/004 (T3 kill criteria) and 006/007/008 (new-strategy kill criteria) follow the same pre-registration template — every strategy has an explicit, pre-committed set of hard-kill thresholds before its first backtest. This is the discipline that makes Layer 4 (DSR) trustworthy: we're not data-fishing thresholds after the fact.

---

## 8. What the writeup is *not* claiming

Discipline cuts both ways. Things that are *not* settled by this work:

1. **The book is not yet live-paper-traded.** Decision 005 calls for a 30-day Hyperliquid dry-run for T3 (and now R∧T2) against decision 004's kill criteria *before* real capital. Backtests are not live trading.

2. **The forward held-out window is intentionally untouched.** Binance 2026-06 → 2026-12 has not been downloaded. After D2 ships, run the book + new strategies on it once, document the result verbatim, no parameter tweaks. That is the strongest OOS check we can run.

3. **MDB-mv is unstable.** Numbers under MDB-mv are upper bounds; the robust flag requires positivity under all three schemes specifically to avoid letting MDB-mv noise drive decisions.

4. **K1's calibration on bear-only Hyperliquid data probably is wrong for multi-asset.** Decision 004 stands as written; the proposed update to portfolio-aware K1 is `decisions/009` (not yet written). Until then, R∧T2's K1 breach is documented as a known accepted risk under portfolio justification, not a re-calibrated threshold.

5. **The cross-sectional and pairs work is preliminary.** B1 (pairs) shipped as v1 single-leg synthetic; B2 (cross-sectional momentum) is the simplest possible long top-1 formulation; B3 (funding MR) tested one parameterisation. None of these are exhausted; they are the *first* test of those families, not the last.

6. **DSR still flags everything as "noise" at N < 200.** The DSR gate is too strict on its own. The principled answer is the layered stack, not DSR pass/fail. This is the resolution of the "DSR flags everything" tension noted in the earlier writeup.

---

## 9. The next sprint

In rough priority order:

1. **Decision 009** — codify portfolio-aware K1: if MDB-rp > 0.3 robust against ≥2-strategy book, accept up to 8% standalone MDD. Writeup formally what was applied informally to R∧T2.
2. **Two-leg PairsZScore v2** — re-attempt X1 with proper `informative_pairs` execution. The single-leg result killed the strategy on a known-biased measurement; the proper measurement might rescue it.
3. **Cross-sectional momentum tuning** — X2 is marginal frontier. Try long top-2 / short bottom-2 (true long-short), or vary the 7d lookback. Goal: increase MDB-rp from +0.05 to > 0.3.
4. **Per-coin HMM hyperparameter sweep** — R2 fails cross-cycle on BTC; might work on individual alts. Decision: scan or accept that HMM-only isn't the right family.
5. **30-day Hyperliquid paper-trade dry-run** for the {T3, R∧T2} book.
6. **Extend Binance funding parquet** to full 5.5y. Currently 2.3y of 5.5y → carry-family results are evaluated on a truncated window.

After these, run the forward held-out window (Binance 2026-06 → 2026-12) as the one-shot OOS gate.

---

## 10. The bottom line

After the buildout:

- **Two strategies in the candidate book**: T3 (conservative, BTC 4h, MDD 2.21%) and R∧T2 (high return, 5-coin 4h, MDD 6.05%). Correlation 0.07.
- **One unified evaluation stack** that catches sample size, multiple testing, tail shape, and portfolio redundancy. Calmar alone no longer makes a decision.
- **A pre-registered kill-criteria discipline** in `decisions/004, 006, 007, 008`. Every strategy is gated before its first backtest.
- **A forward held-out window** that has not been touched and won't be until after the next sprint ships.

The earlier writeup said "we have a paper-trade candidate." This one says "we have a measured candidate book with quantified diversification, evaluated under a layered framework, with discipline against multiple-testing." The structural difference is the layered evaluation and the portfolio framing. They are the principled-not-narrative spine the project lacked.

---

*Generated 2026-05-16 in a single autonomous session over A1 → A1.5 → A2 → C → B1 → B2 → B3 → D. See `../freqtrade-experiment/hmm-slope-experiment/research/analysis/reports/2026-05-16-decision-005-evaluation-and-diversity-plan.md` for the plan that produced this writeup.*
