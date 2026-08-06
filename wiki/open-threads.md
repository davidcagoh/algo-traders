# Open Threads

Mutable. Active cross-project questions and next steps only.

---

## Next Steps

- Commit this session's `evaluation-framework/` build (package + archive move + wiki cross-refs + `dsr_analysis.py` migration) — nothing is committed to git yet.
- Extend `TrialRecord` (`evaluation-framework/evaluation/ledger.py`) with `project`, `venue`, `evidence_stage`, and `gate_outcome` fields toward a principled cross-project trial registry; then backfill from the ~34 dated report cards in `hmm-slope-experiment/` plus `mean-variance-paper/`'s history. Filter/group by evidence maturity and venue — do not build a single ranked leaderboard, which would misleadingly compare killed IS-backtests against live-tested strategies and mix incompatible Sharpe scales across venues.
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
