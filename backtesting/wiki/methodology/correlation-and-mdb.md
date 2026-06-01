# Correlation and Marginal Diversification Benefit (MDB)

**Purpose:** Define how we measure whether a candidate strategy *adds independent signal* to the existing paper-trade book, rather than just duplicating it.

This doc is the methodology spine for the "is this strategy worth deploying?" question. Per pre-decisions locked in decision 005, every candidate strategy in `_index.md` reports three numbers alongside its standalone metrics:
- `corr_to_book` — Pearson correlation of daily wallet returns with the book's combined return
- `MDB-rp` (headline) — Sharpe of (book ∪ {candidate}) minus Sharpe of book, under risk-parity weights
- `robust?` — boolean: positive MDB under *all three* weighting schemes

---

## Why correlation is not enough

A candidate with correlation 0 to the book could still hurt portfolio Sharpe if it has higher volatility than return. Correlation is a *necessary* but not *sufficient* condition for diversification.

MDB is the sufficient version: it answers "does adding this strategy improve the portfolio's Sharpe?" — which is what we actually care about for live deployment.

---

## The three MDB flavours

We compute MDB under three weighting schemes and report all three. Each answers a slightly different question.

### MDB-eq — equal-weight

Weights are 1/N for every strategy in the book.

**Question answered.** "If I split my capital evenly across these strategies, does adding the candidate help?"

**Pros.** Zero parameters. Fully transparent. Doesn't depend on vol-estimation choices.

**Cons.** A high-vol strategy dominates the combined return by *risk contribution*. If T3's annualised vol is 5% and the candidate's is 20%, the equal-weight portfolio is 80% candidate by risk — so MDB-eq mostly measures the candidate's standalone Sharpe, not its diversification benefit.

### MDB-rp — risk-parity inverse-vol (headline)

Weights are 1/σ for each strategy, normalised. Vol is estimated over a 90-day trailing window.

**Question answered.** "If I scale every strategy to contribute equal risk, does adding the candidate help?"

**Pros.** Cleanest "orthogonality" reading. Every strategy is on equal risk footing, so MDB-rp directly reflects correlation and not just "I added a vol bomb." This is the **leaderboard headline column**.

**Cons.** Introduces a parameter (vol window). 90 days chosen as a compromise between responsive (60d) and stable (180d). Different vol windows give slightly different MDB-rp values.

### MDB-mv — Markowitz mean-variance (upper bound)

Long-only tangency portfolio: w ∝ Σ⁻¹μ, clipped to [0, ∞), normalised.

**Question answered.** "If I optimise the weights to maximise Sharpe, can adding the candidate help at all?"

**Pros.** Theoretically the upper bound. If MDB-mv ≤ 0, the candidate is *strictly* not improving — no weighting scheme can rescue it.

**Cons.** Famously unstable at small N. Mean-return estimates are dominated by noise; the optimiser happily allocates 150% to whatever happened to have the best in-sample mean. **Read MDB-mv as a generous upper bound, not as "the right answer."**

---

## The `robust` flag

A candidate is robustly diversifying iff MDB > 0 under *all three* schemes. This is the strongest available test from a 12-strategy leaderboard:
- MDB-eq > 0 → diversifies under naive splitting
- MDB-rp > 0 → diversifies after risk-equalisation
- MDB-mv > 0 → even the optimiser can't rule out adding it

A candidate that's robust by this test is a strong addition. A candidate that's positive under only one scheme is a weighting-dependent artifact and should be treated with caution.

---

## The book

The book is the set of strategies currently tagged ★ (paper-trade candidate) in `wiki/reference/strategy-taxonomy.md`. As of 2026-05-16:

- **T3** SmaRegime180

The book auto-updates as new strategies graduate to ★. MDB for every candidate is recomputed against the expanded book in each new A2-style sweep.

---

## Loader assumptions

These are locked-in via decision 005 pre-decisions:

| Choice | Value | Why |
|---|---|---|
| Annualisation | 365 days | Crypto trades 365 (locked Q1) |
| Correlation window | Global intersection 2020-09 → 2026-05 (5.5y) | Single deterministic window (locked Q1) |
| Missing-day fill | 0.0 (flat) | Strategy not deployed = no return contribution |
| Vol window (MDB-rp) | 90 days trailing | Compromise between responsive and stable |
| Markowitz constraint | Long-only, normalised | Avoids unbounded leverage |

The `missing-day = 0` choice **pulls correlations toward zero by construction.** If two strategies are flat on different days, their pairwise correlation is closer to zero than if we'd used pairwise-complete observations. We accept this because: (a) it makes the matrix deterministic, (b) zero-fill matches how the portfolio would actually behave (no return when flat), and (c) pairwise-complete is reserved as a v2 alternative if it shows different conclusions.

---

## When MDB-rp and MDB-eq disagree

The most informative case. Look for it:

- **MDB-eq > 0, MDB-rp < 0**: candidate's standalone Sharpe is good but its risk dominates the equal-weight portfolio. Risk-parity reveals it's actually a *high-vol diluter*. C1 (FundingCarry 5-coin) is the canonical example: MDB-eq +0.131, MDB-rp −0.275.
- **MDB-eq < 0, MDB-rp > 0**: candidate has bad standalone Sharpe but low vol; equal-weight overweights it relative to its risk contribution. Risk-parity rescales it to a small position where it still adds. R2 (HmmRegime4Rolling) is borderline here: MDB-eq −0.070, MDB-rp +0.017.

The robust flag catches both cases — it requires *all three* schemes to agree.

---

## Implementation

Code: `scripts/eval_layers.py` — functions `build_returns_matrix`, `correlation_matrix`, `marginal_diversification_benefit`, `mdb_robust_flag`, `render_heatmap`.

Driver: `scripts/run_correlation_mdb.py` — reads all 12 A1.5 ZIPs, emits `wiki/assets/correlation_matrix.png` + `wiki/results/_correlation_table.json`.

Run after each new strategy backtest:

```shell
./freqtrade/.venv/bin/python scripts/run_correlation_mdb.py
```

---

## Open questions

1. **Pairwise-complete observations** as a v2 to current zero-fill. Would change correlations on strategies with very different trade frequencies.
2. **Rolling 90-day correlation** rather than global intersection. Would surface regime-conditional correlation breakdowns (e.g. do strategies decorrelate more in bears than in bulls?).
3. **MDB stability at small book sizes.** With book = {T3} alone, MDB depends entirely on (corr_to_T3, vol_ratio). When book grows to 3+ strategies, MDB becomes a richer measurement.
4. **Held-out MDB.** Currently MDB is computed in-sample. The forward held-out window (Binance 2026-06 → 2026-12, locked by Q3) will produce a one-shot OOS MDB at D2 ship.
