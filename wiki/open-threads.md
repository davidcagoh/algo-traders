# Open Threads

Mutable. Active cross-project questions and next steps only.

---

## Next Steps

- Cross-cycle validate the signed mean-variance result before treating its short-window headline metrics as evidence; first confirm whether its Vercel paper monitor is deployed anywhere. (Now backed by a ledger record: `mean-variance-paper`'s `shrunk_mean_variance_signed` trial is `gate_outcome="passed"` on the pre-registered decision-012 thresholds — but that's a single short-window backtest pass, not cross-cycle validation.)
- Both projects' ledgers are still a **floor**, not the true search size (each has an explicit gap-marker record saying so). Extending either backfill to cover more of the discussed-but-undocumented parameter variants would tighten this, but isn't scheduled.
- Pre-register hard-kill and continuous-shrinkage criteria before the next strategy graduates to paper execution.
- Write a generic cross-cycle validation protocol after a second project completes the gate.
- Run the first bounded-grammar Pareto sweep only when a project has enough independent trades per fold for meaningful purged cross-validation.
- Review the first multi-thread literature-search pull request before accepting its source characterizations or adaptive keyword proposals.

## Open Questions

- Does the signed mean-variance portfolio survive multiple crypto cycles without depending on VVV/HYPE momentum or near-market-neutral concentration?
- Is the evaluation framework's strongest contribution the ledger-backed deflation (DSR+PBO), the sealed-holdout mechanism, or the backtest-to-live reconciliation verdict?
- Is there a strategy hypothesis strong enough to justify a new experiment after the failed Freqtrade paper run?
- What bounded signal grammar is broad enough to avoid LLM path dependence without making the search space unauditable?
