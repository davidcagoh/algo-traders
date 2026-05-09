# Random-Projection Stability Tests

**Status:** Parked idea, not yet attached to an experiment. Filed 2026-05-09.

## The portable trick

When you want to enforce or measure a *global* property of a complex object (a high-dim distribution, a returns time series across regimes, a strategy across sub-windows), and the property is hard to test directly, the trick is:

1. **Project** onto many random low-dimensional (often 1D) views.
2. **Run a cheap, statistically tractable test** on each projection (normality, KS, t-test, autocorrelation, whatever the property requires in 1D).
3. **Aggregate** the test statistics across projections.

The aggregate gives you the multivariate / global guarantee that the individual 1D tests don't. This is the same epistemology as **sliced Wasserstein distance** and the **divergence portfolio** (`../references/divergence_portfolio_theory.md`) — single test misses the picture; aggregated multi-view tests capture it.

## Where it showed up

LeWorldModel (Maes et al. 2026, arXiv 2603.19312) uses **SIGReg** for anti-collapse in JEPA training: project latent embeddings onto random 1D directions, run a normality test on each projection, sum the statistics. This forces the full multivariate latent distribution to be isotropic Gaussian without ever testing multivariate Gaussianity directly. Different domain (robotic world models from pixels), same principle.

## Possible algotrading application

**Regime-stability test for a strategy's per-period returns.** Concretely:

- Take a strategy's returns time series (T bars).
- Define many random "temporal projections" — each is a weighted average over a random sub-window or a random linear combination of windows.
- For each projection, compute a stability statistic: rolling Sharpe variance, rolling Calmar deviation from full-period Calmar, drawdown deepening, whatever target stability metric matters.
- Aggregate. A strategy is regime-stable iff most random projections show low instability.

This would complement the **OOS-stability** objective in `../methodology/multi-objective-search.md` — that objective uses the variance across CPCV folds, which depends on the specific fold partitioning. Random projections are partition-free and could be a more robust stability measure, or a Pareto-front companion that flags configs whose stability is fold-artifact rather than real.

## Why this is parked, not active

- No concrete experiment needs it yet. The first multi-objective sweep doesn't exist; the OOS-stability fold-variance objective hasn't been measured against anything.
- The right time to pull this off the shelf: **after** the first sweep produces a Pareto front, when you want to validate that the stability signal is real and not a fold artifact.
- Could also be useful for the **kill-criteria** open hypothesis (`../learnings.md` open #2) — random-projection stability collapsing in real time could be a model-retirement trigger.

## Anti-pattern to avoid

Don't dress this up into a methodology doc before there's an experiment to attach it to. The trick is one paragraph; the application is one paragraph; the rest is implementation that depends on what's actually being measured. Resist the urge to formalize prematurely.
