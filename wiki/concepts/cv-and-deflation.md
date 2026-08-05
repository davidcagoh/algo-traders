# Cross-Validation and Deflation

**Status:** Reference notes. Last updated 2026-05-09.

How to validate strategy results once you're running more than one configuration. Applies to any sweep, hyperparameter search, or LLM-iterated refinement loop.

---

## Why this matters

If you try N strategy configurations and pick the winner by max-Sharpe, the expected max Sharpe under the null (no real edge) grows with √log(N). At N=100 random configs on 32 trades, you can expect a "winner" with Sharpe ~1.5 that has zero true edge. This is the structural source of the backtest-to-live deterioration documented in Liu 2026 (`../../quant-research-agent/source-dives/backtest-regime-timing-live-performance-2026.md`).

The fix is two-part: **proper cross-validation** (so each tested config gets honest OOS scores) + **deflation** (so the act of testing many configs is accounted for in the final claim).

---

## Cross-validation

### Walk-forward (minimum bar)

- Split chronologically: train on [t0, t1], test on (t1, t2], train on [t0, t2], test on (t2, t3], etc.
- Always preserves time order. Required for any strategy with state or autocorrelated residuals.
- Insufficient at sweep scale because adjacent fold boundaries leak information through autocorrelated returns.

### Combinatorial Purged CV (CPCV) — preferred at sweep scale

López de Prado, *Advances in Financial Machine Learning*, ch. 7.

- Partition the timeline into K disjoint groups.
- Train on K−k groups, test on the k held-out groups; repeat across all combinations.
- **Purge** training samples whose labels overlap test windows (matters for any holding period > 1 bar).
- **Embargo** a buffer (typically 1–5% of total data, or ≥ max holding period) between train and test to kill autocorrelation leakage.
- Yields multiple held-out paths, not just one — variance across paths is itself a signal (the `OOS-stability` objective in `multi-objective-search.md`).

### Fold-level requirements

- Each fold must cover at least one bull and one bear sub-window — otherwise you optimise for regime presence, not strategy skill.
- Each fold must contain enough trades for the metric to be statistically meaningful (≥30–50 closed trades minimum for Calmar; SQN works at lower N).
- Report per-fold metrics, not just the mean. A strategy with mean Calmar 5 and per-fold variance 4 is worse than one with mean 4 and variance 0.5.

---

## Deflation

### Deflated Sharpe Ratio (DSR)

Bailey & López de Prado 2014.

- Adjusts observed Sharpe for the number of trials, skewness, and kurtosis of returns.
- Inputs: observed SR, N (trials), variance of trial SRs, return skew/kurtosis, sample length.
- Output: probability that true SR > 0 given the trial structure.
- Use as the primary gate: a config that doesn't clear DSR > some threshold (often 0.95) does not graduate.

### Probability of Backtest Overfitting (PBO)

Bailey, Borwein, López de Prado, Zhu 2014.

- Combinatorial procedure: split data into N pairs of (in-sample, out-of-sample), compute fraction of trials where the IS-best config performs below median OOS.
- PBO < 0.5 means the in-sample winner is more often than not actually skilled OOS.
- Complements DSR: DSR adjusts a single metric for trial count; PBO measures the *consistency* of IS-OOS rank.

### Held-out window

- Beyond CPCV folds, hold out a final window untouched during all search and tuning.
- Run the gate-passing config on it once, at the end, no further tuning.
- This is the only number you should trust when deciding whether to paper-trade live.

---

## Pre-registration

**Write the gate before running the sweep**, not after. Suggested template:

```
Sweep: <name>
Search space: <primitive grammar, N total configs>
CV: CPCV with K=<K>, embargo=<%>
Pareto objectives: <list>
Gate (must pass ALL):
  - DSR > <threshold>
  - PBO < <threshold>
  - Pareto-non-dominated on ≥<n> of <total> objectives
  - Held-out window: positive Calmar AND positive Sharpe
Held-out window: <date range, untouched>
```

Commit this to the repo before the first run. After the run, only configs that clear the pre-registered gate get a leaderboard row.

---

## Anti-patterns

- **Reporting the best of N without disclosing N.** Sharpe of 2.5 from a sweep of 1000 configs is not the same as Sharpe 2.5 from a single hypothesis-driven backtest. The leaderboard should record both the metric and the search size.
- **Iterating on the held-out window.** Once you peek, it's no longer held out. Burn it and use a new one.
- **CV without purge or embargo.** Adjacent folds will leak; you'll get inflated OOS scores that collapse live.
- **Single-fold "OOS" as a deflation substitute.** One held-out window passes by chance ~50% of the time for a noise strategy. CPCV gives you the variance across paths, which is the actual signal.
