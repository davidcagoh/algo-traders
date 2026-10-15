# Open Threads

Mutable. Active cross-project questions and next steps only.

---

## Next Steps

- Relay to Ethan: TON is confirmed delisted from Hyperliquid (see `learnings-archive.md` 2026-08-06), and the first real forward-accumulation result (148 days, real 8-coin book) dominates equal-weight on Sharpe/Calmar/return but triggered decision-012's Kill If rule on max drawdown — get his judgment before treating the kill as decisive (see session-log 2026-08-06 for the full result and the reasoning on why this shouldn't be accepted as settled yet).
- Revisit the confidence interval on the decision-012 MDD comparison with the latest forward state (N=216 on 2026-10-14; the gap was first flagged at N=148) using `evaluation-framework/evaluation/bootstrap.py` / `intervals.py` before treating the drawdown rule as settled.
- The multi-regime cross-cycle gate question (does the strategy need to survive a second, structurally different regime before scaling capital) stays open until a second regime is actually observed — not resolvable by any amount of within-regime accumulation.
- **Priority for the TimesFM demo:** before any confirmatory superiority claim, preregister the estimand, endpoint/baseline family, multiplicity plan, and sample-size rationale, then collect more genuinely post-release origins under that frozen protocol. The current 15-origin freshness slice and post-hoc 1,400-comparison analysis are exploratory; non-significance does not establish equivalence.
- CSLab is a possible compute option for future model runs, but verify VPN, account access, scheduler availability, and one measured job in David's own workspace before treating the cluster as available. See `skills/cslab-compute/SKILL.md`.
- Normalize warehouse domains only when a concrete research question needs them. Feature research must preserve point-in-time availability and exclude future-horizon targets; CRSP, options, and prediction-market snapshots are not bar-engine datasets yet. See `concepts/data-sourcing.md` and `../david_clickhouse_guide.md`.
- Real order-book capture for `evaluation-framework/evaluation/stress.py` (`depth_from_ohlcv` remains an explicitly-labeled OHLCV proxy) — deliberately deferred 2026-08-06, not forgotten. No strategy is currently live-paper-trading, so there's nothing to capture real book depth against yet. If revisited before a strategy graduates to paper execution, scope as a forward-only capture stub (poll the live venue's order-book endpoint going forward) rather than a historical-backfill project — no L2 data source exists anywhere in this repo today.
- The liquid-majors proxy backtest (`mean-variance-paper/analysis/cross_cycle_liquid_majors.py`; finding in `learnings-archive.md` 2026-08-06) argues against signed MV's construction having a robust edge, but can't touch the actual `WLFI`/`VVV`/`XPL`-containing book. The only way to get real evidence on the actual book is forward accumulation (deploy the paper monitor) — backtesting cannot resolve it.
- Both projects' ledgers are still a **floor**, not the true search size (each has an explicit gap-marker record saying so). Extending either backfill to cover more of the discussed-but-undocumented parameter variants would tighten this, but isn't scheduled.
- Pre-register hard-kill and continuous-shrinkage criteria before the next strategy graduates to paper execution.
- Write a generic cross-cycle validation protocol after a second project completes the gate.
- Run the first bounded-grammar Pareto sweep only when a project has enough independent trades per fold for meaningful purged cross-validation.
- Check for the literature-search workflow's PR (`gh run 31125217798`, manually triggered 2026-08-06 — its first-ever run) and review it once it lands.

## Open Questions

- What is the smallest preregistered, adequately powered post-release TimesFM evaluation that can demonstrate the evaluation process without turning the demo into a claim that TimesFM is superior?
- Does the signed mean-variance portfolio survive multiple crypto cycles without depending on VVV/HYPE momentum or near-market-neutral concentration?
- Is the evaluation framework's strongest contribution the ledger-backed deflation (DSR+PBO), the sealed-holdout mechanism, or the backtest-to-live reconciliation verdict?
- Is there a strategy hypothesis strong enough to justify a new experiment after the failed Freqtrade paper run?
- What bounded signal grammar is broad enough to avoid LLM path dependence without making the search space unauditable?

## Parked with archived projects

- **Aurora calibration and stream ablation:** the n=4 calibration warning and the n=4-to-n=12 `funding-vision` replication remain historical findings. Do not resume the calibration recheck, GDELT retries, or Straits Times source work unless `archive/aurora-forecaster/` is explicitly reopened. References: `learnings-archive.md` and `archive/aurora-forecaster/`.
