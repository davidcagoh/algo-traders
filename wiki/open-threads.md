# Open Threads

Mutable. Active cross-project questions and next steps only.

---

## Next Steps

- Backfill `mean-variance-paper`'s history (`freqtrade-experiment/mean-variance-paper/analysis/results/*.md`) into a `TrialLedger`, using the new `project`/`venue`/`evidence_stage`/`gate_outcome` fields — no ledger or backfill script exists for that project yet. `hmm-slope-experiment`'s ledger (10 trials + gap marker) already carries the new fields; use its `backfill_ledger.py` as the template. Once both projects are in one registry, group with `TrialLedger.registry_groups()` (by evidence_stage, venue) rather than a single ranked leaderboard — killed IS-backtests and live-tested strategies aren't comparable, and Sharpe scales differ by venue.
- Cross-cycle validate the signed mean-variance result before treating its short-window headline metrics as evidence; first confirm whether its Vercel paper monitor is deployed anywhere.
- Migrate remaining `hmm-slope-experiment` analysis drivers (`eval_layers.py`, `run_correlation_mdb.py`, `combined_book_mdd.py`, `generate_pareto_chart.py`) onto the package's ledger-backed DSR, bootstrap CIs, and cost/live modules — currently only `dsr_analysis.py` uses the package.
- Pre-register hard-kill and continuous-shrinkage criteria before the next strategy graduates to paper execution.
- Write a generic cross-cycle validation protocol after a second project completes the gate.
- Run the first bounded-grammar Pareto sweep only when a project has enough independent trades per fold for meaningful purged cross-validation.
- Review the first multi-thread literature-search pull request before accepting its source characterizations or adaptive keyword proposals.

## Open Questions

- Does the signed mean-variance portfolio survive multiple crypto cycles without depending on VVV/HYPE momentum or near-market-neutral concentration?
- Is the evaluation framework's strongest contribution the ledger-backed deflation (DSR+PBO), the sealed-holdout mechanism, or the backtest-to-live reconciliation verdict?
- Is there a strategy hypothesis strong enough to justify a new experiment after the failed Freqtrade paper run?
- What bounded signal grammar is broad enough to avoid LLM path dependence without making the search space unauditable?
