# Open Threads

Mutable. Active cross-project questions and next steps only.

---

## Next Steps

- Ask Ethan (mean-variance-paper collaborator) two things: (1) whether he ever deployed the Vercel paper monitor without pushing it — no `.vercel` dir or other local evidence it's live; (2) whether he actually wants "cross-cycle validation required before paper-trading" to gate this project — that requirement was written by an earlier Claude session during the 2026-08-05 repo consolidation, inherited from `hmm-slope-experiment`'s methodology, not something he decided for this project (see session-log 2026-08-06).
- A liquid-majors proxy backtest (`mean-variance-paper/analysis/cross_cycle_liquid_majors.py`) found `shrunk_mean_variance_signed` does NOT reproduce its headline edge outside the original window — last-of-5 in a bull window, merely "least bad" in a chop window. This is evidence against the *construction* having a robust edge; it says nothing about the actual `WLFI`/`VVV`/`XPL`-containing book, which cannot be proxy-tested (those tokens have no prior cycle on any venue, on Hyperliquid or elsewhere). The only way to get real evidence on the actual book is forward accumulation (deploy the paper monitor) — backtesting cannot resolve it.
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
