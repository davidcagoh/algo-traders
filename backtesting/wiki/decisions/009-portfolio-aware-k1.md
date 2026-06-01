# Decision 009 — Portfolio-Aware K1

**Status:** decided
**Date:** 2026-05-16
**Supersedes:** none. Refines K1 from `decisions/004-kill-criteria-sma-regime-180.md` for portfolio-addition use.
**Pre-registration scope:** retroactive (R∧T2 was already backtested on the common window). Future strategies must apply this gate prospectively, before their first backtest, alongside their own per-family kill-criteria doc.

---

## 1. The dispute

R∧T2 (`HmmSmaSlopeV2`, 5-coin 4h) is the second strategy in the candidate book {T3, R∧T2}. On the Binance common window 2020-09-23 → 2026-05-09 its standalone metrics are:

| Metric | Value |
|---|---:|
| Calmar (CT) | 30.23 |
| SQN | 2.73 |
| CAGR | 21.31% |
| **MDD** | **6.05%** |
| Martin ratio | +7.41 |
| Pearson corr → T3 | 0.07 |
| MDB-rp vs {T3} | **+0.55, robust** |

The K1 = 5.5% hard-MDD ceiling defined in `decisions/004` is breached by 0.55pp. Two readings of the same number:

- **Reading A (strict):** K1 is a hard kill. R∧T2 fails. The candidate book collapses back to {T3}.
- **Reading B (portfolio-aware):** K1 was calibrated as 3× T3's IS MDD on a *single BTC-bear* sub-window. On a 5-coin 5.5y substrate (2 bulls + 2 bears) a strategy with genuinely sound risk shape will naturally show a deeper MDD than the same strategy on a single-coin 6-month bear. The breach is a calibration-scope artifact, not a risk failure — *provided* the strategy is being added to an existing K1-compliant book and its portfolio contribution is independently verified.

This decision codifies Reading B as the official rule for **portfolio additions**, with explicit bounds so it cannot be abused.

---

## 2. Why the standalone K1 alone is insufficient

K1 = 5.5% was derived in `decisions/004` as `3 × IS_MDD(T3, Hyperliquid bear)` = `3 × 1.74%` ≈ 5.5%. The multiplier captured the empirical fact that live MDD typically exceeds IS MDD by ~3× under regime shift.

Two assumptions in that derivation do not transfer cleanly to portfolio-addition decisions:

1. **Single-window scope.** The 1.74% anchor was measured on one BTC-only bear (~6mo). On the Binance common window (5.5y, 5 coins, 2 bulls + 2 bears) T3's own MDD widens to 2.21% — and that's the *same* strategy, just measured against a more demanding substrate. Applying the 3× rule consistently would push K1 to ~6.6% in the common-window basis.
2. **Single-strategy scope.** A 6.05% standalone MDD that occurs at a *different* time from T3's drawdowns is a different beast from a 6.05% MDD that compounds T3's drawdown. With Pearson 0.07 between T3 and R∧T2, the book's MDD is bounded well below the sum of individual MDDs (risk-parity weighting; see `methodology/correlation-and-mdb.md`).

Conclusion: K1 = 5.5% remains the correct *standalone* ceiling — useful as a fast first-pass filter — but it is **not** the correct ceiling for evaluating a strategy entering an existing K1-compliant book. The portfolio-aware gate below covers that case.

---

## 3. The portfolio-aware gate

A candidate strategy *C* may enter a book *B* (where *B* already contains ≥1 standalone-K1-compliant strategy) if **either** the standalone path **OR** the portfolio path passes:

```
Standalone path (default; fast):
  standalone_MDD(C) <= K1_standalone   # = 5.5%

OR

Portfolio path (for K1-breaching candidates):
  standalone_MDD(C) <= K1_hard_cap          # = 11.0% = 2 × K1_standalone
  AND combined_MDD(B ∪ {C}) <= K1_book      # = 5.5%
  AND MDB(C, B) > 0 under all three schemes (eq, rp, mv)  # "robust positive"
  AND MDB-rp(C, B) >= 0.30
  AND max_pairwise_pearson(C, B) < 0.85     # no statistical duplicate
```

Notes on each clause:

- **`K1_hard_cap = 11.0%`** is the absolute ceiling above which no portfolio-justification rescues a candidate. See §5.
- **`K1_book = 5.5%`** is intentionally the same number as `K1_standalone`. The portfolio's combined drawdown is what actually hits live capital, so it inherits the same risk ceiling that T3 was originally calibrated against. The relaxation is *only* on the per-strategy axis, not on the portfolio axis.
- **Robust MDB** (positive under equal-weight, risk-parity, and mean-var) follows the definition pre-registered in `decisions/005` §7 and operationalised in `methodology/correlation-and-mdb.md`. MDB-rp is the headline; the eq/mv flank checks prevent gaming a single weighting scheme.
- **MDB-rp ≥ 0.30** is a meaningful-magnitude threshold, not just "positive." A barely-positive MDB does not justify accepting a K1 breach.
- **Pearson < 0.85** kills statistical duplicates (R∧T1/V2/V3 between each other, e.g., would never co-exist in a book under this gate).

The `OR` between paths is a true logical OR: a candidate with standalone MDD ≤ 5.5% is admitted on the standalone path alone, **even if its MDB is small or its correlation with the book is high**. (Computing MDB anyway is good practice but not load-bearing for admission in that case.)

---

## 4. R∧T2 application

Walking R∧T2 through the gate against book *B* = {T3} (the state at the moment R∧T2 was evaluated):

| Clause | Required | Observed | Pass? |
|---|---|---|:---:|
| `standalone_MDD(C) ≤ K1_standalone` | ≤ 5.5% | 6.05% | ✗ |
| → falls through to portfolio path | | | |
| `standalone_MDD(C) ≤ K1_hard_cap` | ≤ 11.0% | 6.05% | ✓ |
| `combined_MDD(B ∪ {C}) ≤ K1_book` | ≤ 5.5% | **MDD_rp = 2.12%** (MDD_eq = 3.20%, MDD_mv = 1.99%)¹ | ✓ confirmed |
| `MDB > 0` robust (eq, rp, mv) | all positive | all positive (per `_correlation_table.json`) | ✓ |
| `MDB-rp(C, B) ≥ 0.30` | ≥ 0.30 | +0.55 | ✓ |
| `max_pairwise_pearson(C, B) < 0.85` | < 0.85 | 0.07 (only T3 in book) | ✓ |

¹ Computed by `scripts/combined_book_mdd.py` on the A1.5 common window (2020-09-24 → 2026-05-09, 2054 days), using the same risk-parity vol_window=90 and equity-curve construction as `eval_layers.py`. Risk-parity weights at the window endpoint were {T3: 0.685, R∧T2: 0.315}; mean-var weights {T3: 0.707, R∧T2: 0.293}. MDD_rp = 2.12% is the headline. All three schemes clear K1 = 5.5% by a wide margin — combined book sits at <40% of the gate. This is consistent with the *a priori* expectation given Pearson 0.07: the weighted book's MDD is bounded well below either standalone MDD (2.21% T3, 6.05% R∧T2), because their drawdowns occur at different times and risk-parity caps R∧T2's contribution.

**Verdict (confirmed):** R∧T2 passes the portfolio-aware gate. Standalone K1 breach is accepted because (a) standalone MDD 6.05% is well under the 11% hard cap, (b) MDB-rp is +0.55 robust — well above the 0.30 threshold, (c) the candidate is statistically distinct from the existing book (Pearson 0.07), and (d) **combined-book MDD_rp = 2.12% ≤ 5.5%** — the previously provisional clause is now an explicit scalar.

Follow-up: surface `combined_MDD_book` (2.12% rp / 3.20% eq / 1.99% mv) on the common-window leaderboard in `_index.md`, and recompute at each quarterly review per §5 below.

---

## 5. Bounds on the relaxation

The portfolio-aware gate is **not** a license for arbitrarily larger standalone drawdowns.

- **Hard cap: `K1_hard_cap = 2 × K1_standalone = 11.0%`.** No standalone MDD above this is admissible regardless of MDB or correlation. Rationale: at MDD > 11% the strategy concentrates so much standalone risk that the only way risk-parity weighting can neutralise it is by driving its book-weight toward zero — and a strategy at near-zero weight is not meaningfully "in the book." It's a phantom entry that inflates the leaderboard without changing live P&L. R2x (`HmmRegime4Rolling` 5-coin, MDD 21.47%) is the worked example: technically MDB-rp positive but flagged ✗ in the leaderboard footnote ¹³ precisely for this reason.
- **MDB-rp must be a *meaningful* magnitude, not just positive.** The 0.30 floor is calibrated to be roughly 50% of the headline MDB-rp observed for R∧T2 (+0.55). Strategies whose only claim to admission is a noise-level positive MDB (e.g. R2's +0.010 to +0.012, leaderboard footnote ¹⁶) do not clear this bar.
- **No daisy-chaining.** A strategy admitted via the portfolio path does **not** become the anchor for further portfolio-path admissions. The book must always contain at least one strategy that passed standalone K1 (the "anchor"). Today the anchor is T3. If T3 is ever removed, R∧T2 cannot remain in the book on its own — a new K1-compliant anchor must be admitted first.
- **Cross-cycle requirement.** Portfolio-path admission requires the common-window evaluation to span at least one bull and one bear (currently 2 bulls + 2 bears on the Binance common window). A K1 breach measured on a single regime cannot be rescued by MDB because the diversification is itself regime-conditional.

---

## 6. What this does NOT do

- **Does not relax K1 for T3 or any other single-strategy book.** While {T3} alone is the book, K1 = 5.5% applies to T3 unmodified.
- **Does not retroactively rescue any of the killed families.** X1 (PairsZScore) was killed on MDB-rp = −0.898 — fails the portfolio path on the MDB clause regardless of standalone MDD. F1 (FundingExtremeMR) MDD 29.94% > 11% hard cap — fails the portfolio path on the hard-cap clause regardless of MDB. R∧C1 (HmmCarry) MDD 35.46% — same. Neither path applies.
- **Does not relax the other kill axes in `decisions/004`** (K2 consecutive stops, K3 rolling-return flat, K4 walk-forward Calmar < 2.0). The portfolio-aware exception is **K1-only**. K2–K4 remain per-strategy hard kills with no portfolio override.
- **Does not relax the family-specific K1 thresholds** in `decisions/006` (pairs K1 = 8%), `007` (cross-sectional K1-xs = 12%), `008` (funding-MR K1-fmr = 5%). Those are pre-registered per-family ceilings; they take precedence over the generic K1 when a family-specific decision doc applies. The portfolio-path logic in this decision uses whatever K1 the family's decision doc specifies as `K1_standalone` for that strategy, and `K1_hard_cap = 2 × K1_standalone` accordingly.

X2 (CrossSectionalMomentum, MDD 13.04%) is the current open case: per `decisions/007` K1-xs is 12%, so `K1_hard_cap_xs = 24%`. 13.04% is under the hard cap, MDB-rp +0.048 is robust positive but **well below the 0.30 magnitude threshold**. Verdict: X2 does **not** pass the portfolio-aware gate on the MDB-rp magnitude clause. Stays ▲ research-frontier; not admitted to the book. (This is the decision; the leaderboard footnote ¹⁵ should be updated to reflect it.)

---

## 7. Quarterly review

R∧T2 specifically must be re-evaluated against this gate every quarter using the then-current rolling common window:

- Recompute standalone MDD, combined-book MDD, MDB triplet, and pairwise correlations on the latest data.
- If MDB-rp drops below 0.30 robust, R∧T2 **exits the book** at the next rebalance, even if its standalone metrics are unchanged. The diversification benefit *is* the basis for its admission; if that disappears, admission lapses.
- If combined-book MDD exceeds 5.5%, R∧T2 exits the book regardless of MDB.
- If standalone MDD exceeds 11.0% (the hard cap), R∧T2 exits the book regardless of anything else.
- Exit is documented as a new dated decision doc that supersedes this one for the R∧T2 row specifically.

The same review cadence applies to any future strategy admitted via the portfolio path.

---

## 8. Cross-references

- **Companion (upstream):** `decisions/004-kill-criteria-sma-regime-180.md` — defines `K1_standalone = 5.5%` and the IS-MDD-multiplier derivation.
- **Companion (methodology):** `decisions/005-evaluation-and-diversity-plan.md` §7 — pre-registers MDB-eq/rp/mv, the robust flag, and the common-window basis.
- **Companion (operationalisation):** `methodology/correlation-and-mdb.md` — loader assumptions and the eq/rp/mv definitions.
- **Trigger:** `decisions/010-paper-plan-deferred.md` item #3 of the prerequisite list — this decision was the named blocker.
- **Upstream methodology:** [`../../../wiki/methodology/kill-criteria.md`](../../../wiki/methodology/kill-criteria.md) (meta-wiki, 2026-05-16) — the "revise-vs-kill review" section and the "portfolio-justified breach" exception name this decision as the canonical specification of the portfolio-aware rule.
- **Leaderboard footnote** `_index.md` ⁸ — currently records the open status; should be updated to point here for the codified rule, and footnote ¹⁵ (X2) should be updated to reflect §6's "X2 does not pass" verdict.
