# Cross-Cutting Learnings

Facts, hypotheses, and ruled-out directions that apply to **both** subprojects. Subproject-specific learnings stay in their own wikis.

---

## Confirmed (cross-project)

- **LLM-driven sequential strategy refinement gets geometrically trapped.** Both feishu and backtesting independently saw an LLM start from a simple template (SMA, momentum) and refine along that vein for many iterations without exploring orthogonal signal families. The local-minimum is the LLM's prior, not the data.
- **Single-objective optimisation overfits at any scale.** Feishu IS-parameter-space exhaustion was reached at modest sweep size; further tuning was flagged as overfitting risk. Backtesting's thin samples (N=6, N=32) make any single-metric ranking noise-dominated.

## Open hypotheses (cross-project)

1. **Multi-objective Pareto search beats single-metric max** when objectives are negatively correlated under noise (Calmar-bull, Calmar-bear, ulcer, turnover-adjusted PF, OOS-stability). Inspired by `references/divergence_portfolio_theory.md` — same logic as α-portfolio for distribution fitting.
   - **Test:** scaffold an NSGA-II run on a small primitive grammar (~6 signal families × 2–3 hyperparams) once a subproject has enough independent trades per fold.
   - **Open methodology:** see `methodology/` (to be written).

## Ruled out (cross-project)

- *(none yet — promote from subproject wikis as patterns appear in both)*

---

## Methodology to write up

- **Combinatorial purged CV with embargo** — protocol doc in `methodology/` once first sweep is run.
- **Deflated Sharpe / PBO gate** — pre-registration template before any sweep.
- **Primitive grammar for signal search** — bounded DSL of signal families to avoid the "infinite strategy space" trap.
