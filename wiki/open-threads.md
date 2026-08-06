# Open Threads

Mutable. Active cross-project questions and next steps only.

---

## Next Steps

- Relay to Ethan: TON is confirmed delisted from Hyperliquid (see `learnings-archive.md` 2026-08-06), and the first real forward-accumulation result (148 days, real 8-coin book) dominates equal-weight on Sharpe/Calmar/return but triggered decision-012's Kill If rule on max drawdown — get his judgment before treating the kill as decisive (see session-log 2026-08-06 for the full result and the reasoning on why this shouldn't be accepted as settled yet).
- Run `forward_accumulate.py` (`freqtrade-experiment/mean-variance-paper/analysis/`) daily to genuinely accumulate forward observations (the first run is a retrospective read over the most recent available historical slice, not yet day-by-day observation) toward the N=250 DSR-binding floor.
- Bootstrap a confidence interval on the MDD comparison that triggered decision-012's Kill If rule (signed -23.40% vs baseline -19.92%, N=148, below the DSR-binding floor) using `evaluation-framework/evaluation/bootstrap.py`/`intervals.py` (already built, not yet applied here) — determine whether that gap is a real tail-risk signal or noise at this sample size before treating the kill as settled either way.
- The multi-regime cross-cycle gate question (does the strategy need to survive a second, structurally different regime before scaling capital) stays open until a second regime is actually observed — not resolvable by any amount of within-regime accumulation.
- Align the four aurora-forecaster text sources (GDELT, Alpha Vantage, Currents, Guardian — see `decisions-archive.md` 2026-08-06) into one per-timestep text-context input, then run the actual unimodal vs. GDELT vs. Alpha Vantage vs. Currents comparison this whole feasibility test has been building toward. Guardian stays unwired until that comparison shows a need for it.
- Candidate future text source for aurora-forecaster: a personal Straits Times Opinion Forum scraper (`/Users/davidgoh/LocalFiles/Post-Duke/st_forum_scraper/`) — Selenium, non-headless by design, targets `opinion/forum` markup. Not built into aurora-forecaster; would need headless capability and re-verified selectors for Business/Finance/Wealth sections first. Per standing decision, don't wire in until the four existing sources are actually compared.
- Extend `evaluation-framework` (or wrap separately) to score a probabilistic/distributional forecast output — its current metrics assume realized trade/portfolio returns, which `aurora-forecaster`'s `model.generate(...)` output doesn't directly provide.
- Real order-book capture for `evaluation-framework/evaluation/stress.py` (`depth_from_ohlcv` remains an explicitly-labeled OHLCV proxy) — deliberately deferred 2026-08-06, not forgotten. No strategy is currently live-paper-trading, so there's nothing to capture real book depth against yet. If revisited before a strategy graduates to paper execution, scope as a forward-only capture stub (poll the live venue's order-book endpoint going forward) rather than a historical-backfill project — no L2 data source exists anywhere in this repo today.
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
