# Open Threads

Mutable. Active cross-project questions and next steps only.

---

## Next Steps

- Whether Ethan wants "cross-cycle validation required before paper-trading" to formally gate `mean-variance-paper` — that requirement was written by an earlier Claude session during the 2026-08-05 repo consolidation, inherited from `hmm-slope-experiment`'s methodology, not something he decided for this project (see `decisions-archive.md`/`learnings-archive.md` 2026-08-06 for the resolved half of this thread — the monitor's deployment status).
- Investigate why https://vercel-paper-dashboard.vercel.app/ isn't working — get logs/errors from Ethan or check the deployment directly.
- Align the four aurora-forecaster text sources (GDELT, Alpha Vantage, Currents, Guardian — see `decisions-archive.md` 2026-08-06) into one per-timestep text-context input, then run the actual unimodal vs. GDELT vs. Alpha Vantage vs. Currents comparison this whole feasibility test has been building toward. Guardian stays unwired until that comparison shows a need for it.
- Candidate future text source for aurora-forecaster: a personal Straits Times Opinion Forum scraper (`/Users/davidgoh/LocalFiles/Post-Duke/st_forum_scraper/`) — Selenium, non-headless by design, targets `opinion/forum` markup. Not built into aurora-forecaster; would need headless capability and re-verified selectors for Business/Finance/Wealth sections first. Per standing decision, don't wire in until the four existing sources are actually compared.
- Extend `evaluation-framework` (or wrap separately) to score a probabilistic/distributional forecast output — its current metrics assume realized trade/portfolio returns, which `aurora-forecaster`'s `model.generate(...)` output doesn't directly provide.
- Investigate uncommitted changes noted in `evaluation-framework/` (`PLAN.md`, `STATUS.md`, new `spa.py`/`test_spa.py`) and `literature/strategy-evaluation/` (two new PDFs, updated `_index.md`) found via `git status` 2026-08-06 — predate this session, not touched or committed here. Possibly the literature-search workflow's first run (`gh run 31125217798`) landing changes, or leftover unstaged work.
- The liquid-majors proxy backtest (`mean-variance-paper/analysis/cross_cycle_liquid_majors.py`; finding in `learnings-archive.md` 2026-08-06) argues against signed MV's construction having a robust edge, but can't touch the actual `WLFI`/`VVV`/`XPL`-containing book. The only way to get real evidence on the actual book is forward accumulation (deploy the paper monitor) — backtesting cannot resolve it.
- Both projects' ledgers are still a **floor**, not the true search size (each has an explicit gap-marker record saying so). Extending either backfill to cover more of the discussed-but-undocumented parameter variants would tighten this, but isn't scheduled.
- Pre-register hard-kill and continuous-shrinkage criteria before the next strategy graduates to paper execution.
- Write a generic cross-cycle validation protocol after a second project completes the gate.
- Run the first bounded-grammar Pareto sweep only when a project has enough independent trades per fold for meaningful purged cross-validation.
- Check for the literature-search workflow's PR (`gh run 31125217798`, manually triggered 2026-08-06 — its first-ever run) and review it once it lands.

## Open Questions

- Does the signed mean-variance portfolio survive multiple crypto cycles without depending on VVV/HYPE momentum or near-market-neutral concentration?
- Is the evaluation framework's strongest contribution the ledger-backed deflation (DSR+PBO), the sealed-holdout mechanism, or the backtest-to-live reconciliation verdict?
- Is there a strategy hypothesis strong enough to justify a new experiment after the failed Freqtrade paper run?
- What bounded signal grammar is broad enough to avoid LLM path dependence without making the search space unauditable?
