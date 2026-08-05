# Multi-Objective Strategy Search

**Status:** Design draft, no runs yet. Last updated 2026-05-09.

Frame for escaping the "LLM picks SMA, then refines along SMA forever" trap observed in both feishu and backtesting. Inspired by the divergence-portfolio principle (`../references/divergence_portfolio_theory.md`): no single metric captures a strategy, just as no single α captures a distribution.

---

## Premise

Single-objective optimisation (max Sharpe, max Calmar, max Score) overfits regardless of search method — sweep, RL, evolutionary, LLM-guided. The fix is **not** more configs; it's structurally harder targets.

A strategy that is **Pareto-non-dominated across multiple negatively-correlated objectives** is much harder to overfit than one that maxes a single metric, because the noise winner has to be lucky on multiple uncorrelated axes simultaneously.

## Five design choices

### 1. Bounded primitive grammar (not "all strategies")

"All possible strategies" is infinite, and any DSL choice embeds priors equivalent to the LLM's — you'd just be moving the bias from the model to the grammar designer. So make the grammar small and auditable:

| Family | Examples | Hyperparams |
|--------|----------|-------------|
| Trend | SMA-cross, slope-gate, breakout | window, slope_lookback |
| Reversion | z-score, RSI-extreme, OFI | window, threshold |
| Volatility | ATR-breakout, vol-ranking, Bollinger | window, z |
| Carry | funding-rate threshold, basis | threshold, holding_period |
| Regime | HMM state, SMA-regime, vol-regime | n_states, lookback |
| Flow | OI imbalance, liquidation cascade, taker imbalance | window, threshold |

Strategies are compositions: `(regime_filter) AND (entry_signal) → (exit_rule)`. ~6 families × 2–3 hyperparams each → ~10³ configs, not 10⁶. Auditable, finite, covers the archetypes from `wiki/concepts/strategy-archetypes.md`.

### 2. Pareto objectives that are negatively correlated under noise

Objectives must disagree on overfit configs but agree on real edges. Working set:

- **Calmar-bull** (CAGR / MDD on bull-regime sub-windows)
- **Calmar-bear** (same on bear-regime sub-windows)
- **Ulcer index** (depth-weighted drawdown, not just max)
- **Turnover-adjusted profit factor** (penalises high-frequency noise harvesting)
- **OOS-stability** (variance of per-fold Calmar across CPCV folds)

A noise winner has to look good on bull AND bear AND drawdown shape AND turnover AND fold consistency. That's a much narrower target than max-Calmar.

### 3. Combinatorial Purged Cross-Validation with embargo

Standard walk-forward leaks across fold boundaries because returns autocorrelate. López de Prado's CPCV:

- Disjoint test windows
- 1–5% embargo between train and test (proportional to max holding period)
- Each fold must cover both bull and bear sub-windows or it's optimising regime presence
- Report per-fold metric, not just mean — the variance is the OOS-stability objective

### 4. Pre-registered deflation gate

Before running the sweep, write down the pass criteria. Otherwise you'll move goalposts after seeing results. Minimum:

- Deflated Sharpe Ratio > X (computed from N_configs tested)
- Pareto-non-dominated on ≥4 of 5 objectives
- Probability of Backtest Overfitting (PBO) < 0.5
- Survives an additional held-out window untouched during search

If a config fails the gate, it does not get a leaderboard row. Period.

### 5. Search method (last, not first)

Once 1–4 are settled, the search algorithm matters less than people think:

- **NSGA-II** for the Pareto frontier — well-understood, no RL pathologies, finds the trade-off curve directly.
- **CMA-ES** if objectives are smooth and you only want one point on the frontier.
- **Random search baseline** — always run this; if NSGA-II doesn't beat random by a clear margin you have a setup bug.
- **RL/MaxRL** — avoid for strategy discovery. Backtest envs are non-stationary, reward is noisy, exploration finds sim exploits. Reasonable for execution policies, not for alpha discovery.

---

## Data preconditions (must clear before running)

Documented separately in `learnings.md` and `freqtrade-experiment/hmm-slope-experiment/research/analysis/reports/learnings.md`:

- ≥250–500 independent trades per CV fold (multi-asset multiplies sample; correlation deflates effective N)
- Each fold spans at least one bull and one bear sub-window
- Realistic execution model loaded (fees, funding, slippage proxy) — sweep without these finds sim exploits
- Pre-registered deflation rule written and committed before first run

If these aren't met, the sweep result is statistically dead on arrival regardless of method.

---

## Open questions

- What's the right size for the primitive grammar? Too small and you can't represent real edges; too large and Bonferroni eats you.
- Are 5 objectives enough, or does adding more (e.g., tail-risk, max-consecutive-losses) help structurally or just add noise?
- Does Pareto-front rank predict OOS performance better than single-metric rank? Empirical question — measure on a held-out year before trusting the framework.
- Can the divergence-portfolio loss formulation (`../references/divergence_portfolio_theory.md`) be applied directly as a strategy-evaluation loss, or is the analogy purely structural?

---

## Production-scale endpoint (for orientation, not prescription)

The Pareto-frontier-of-objectives framing here is structurally the same architecture that production quant funds run, just at much smaller scale. From Leek 2025 (popular-press but consistent with what's documented elsewhere about Citadel, Two Sigma, AQR):

> *"Instead of one grand model, they run hundreds of small, specialized ones. Each targets a distinct horizon — milliseconds: market-making and order-flow prediction; hours: short-term flow and liquidity shocks; weeks: trend and relative momentum; months: valuation, factor rotation, or regime-switch models. Some firms operate with a higher-level meta-strategy which allocates capital dynamically across these sub-models, smoothing performance across time and market conditions."*

Map to the framework:
- **Each "small specialized model"** ≈ one config on the Pareto frontier — a (primitive grammar config, holding horizon, asset universe) tuple optimized for one or two objectives.
- **The meta-allocator** ≈ the Pareto-front itself: rather than picking one config, you hold a portfolio across the frontier and dynamically weight by recent regime fit.
- **The horizon stratification** is the implicit covering structure that makes the objectives non-degenerate — a 1ms market-making model and a 3-month factor model have nearly orthogonal failure modes by construction.

This is **not** a near-term goal (we don't have the data, infra, or capital to operate at that scale). It's a sanity check that the structural direction isn't a dead end — the production version exists and works. The near-term goal is just to get *one* Pareto front out of *one* primitive grammar on *one* asset, with proper deflation, and see whether multi-objective rank predicts OOS performance better than single-metric rank.
