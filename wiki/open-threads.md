# Open Threads

Mutable. Active cross-project questions and next steps only.

---

## Next Steps

- Relay to Ethan: TON is confirmed delisted from Hyperliquid (see `learnings-archive.md` 2026-08-06), and the first real forward-accumulation result (148 days, real 8-coin book) dominates equal-weight on Sharpe/Calmar/return but triggered decision-012's Kill If rule on max drawdown — get his judgment before treating the kill as decisive (see session-log 2026-08-06 for the full result and the reasoning on why this shouldn't be accepted as settled yet).
- Bootstrap a confidence interval on the MDD comparison that triggered decision-012's Kill If rule (signed -23.40% vs baseline -19.92%, N=148, below the DSR-binding floor) using `evaluation-framework/evaluation/bootstrap.py`/`intervals.py` (already built, not yet applied here) — determine whether that gap is a real tail-risk signal or noise at this sample size before treating the kill as settled either way.
- The multi-regime cross-cycle gate question (does the strategy need to survive a second, structurally different regime before scaling capital) stays open until a second regime is actually observed — not resolvable by any amount of within-regime accumulation.
- **Priority for next session:** revisit the calibration-miscalibration finding (see Open Questions below) using the real n=12 unimodal ledger now available — more fundamental than covariate/encoding choice and unrevisited since the original 4-origin run. Explicitly scoped by the user to run with a fresh agent/session.
- `GDELT_ONLY` and `GDELT_CURRENTS` remain unrun at the current n=12 window — GDELT rate-limits even at 10s inter-call spacing (`GDELT_ONLY` got through 8/12 origins on the last attempt before a 429). Low priority; `artifacts/btc_ablation_report.md` and `dashboard.html` currently reflect 8/10 `STANDARD_CONFIGS`. Recovery procedure if retried: delete the partial ledger before rerunning (duplicate `origin_timestamp`s break `ablation_core.LossSeries`'s uniqueness check).
- `funding-vision`'s striking n=4 result (beat `unimodal` p=0.000, beat `funding` text p=0.040) did **not** replicate at n=12 — see `learnings-archive.md` 2026-08-09. No config currently beats `unimodal` significantly at n=12. Not actionable further unless n is pushed even higher (currently low priority relative to the calibration question).
- If the archived Aurora experiment resumes, a candidate future text source is a personal Straits Times Opinion Forum scraper (`/Users/davidgoh/LocalFiles/Post-Duke/st_forum_scraper/`) — Selenium, non-headless by design, targets `opinion/forum` markup. It would need headless capability and re-verified selectors for Business/Finance/Wealth sections first. Per standing decision, don't wire it in until the four existing sources are compared.
- Real order-book capture for `evaluation-framework/evaluation/stress.py` (`depth_from_ohlcv` remains an explicitly-labeled OHLCV proxy) — deliberately deferred 2026-08-06, not forgotten. No strategy is currently live-paper-trading, so there's nothing to capture real book depth against yet. If revisited before a strategy graduates to paper execution, scope as a forward-only capture stub (poll the live venue's order-book endpoint going forward) rather than a historical-backfill project — no L2 data source exists anywhere in this repo today.
- The liquid-majors proxy backtest (`mean-variance-paper/analysis/cross_cycle_liquid_majors.py`; finding in `learnings-archive.md` 2026-08-06) argues against signed MV's construction having a robust edge, but can't touch the actual `WLFI`/`VVV`/`XPL`-containing book. The only way to get real evidence on the actual book is forward accumulation (deploy the paper monitor) — backtesting cannot resolve it.
- Both projects' ledgers are still a **floor**, not the true search size (each has an explicit gap-marker record saying so). Extending either backfill to cover more of the discussed-but-undocumented parameter variants would tighten this, but isn't scheduled.
- Pre-register hard-kill and continuous-shrinkage criteria before the next strategy graduates to paper execution.
- Write a generic cross-cycle validation protocol after a second project completes the gate.
- Run the first bounded-grammar Pareto sweep only when a project has enough independent trades per fold for meaningful purged cross-validation.
- Check for the literature-search workflow's PR (`gh run 31125217798`, manually triggered 2026-08-06 — its first-ever run) and review it once it lands.

## Open Questions

- **Now actionable with real data:** is aurora-forecaster's severe calibration miss (nominal 50/80/95% coverage empirically only ~20/28/38%, first found `learnings-archive.md` 2026-08-07 at n=4) a real property of the model at a 96h horizon, or was it itself a small-n artifact? The `unimodal` ledger now has 12 real scored origins (`archive/aurora-forecaster/artifacts/btc_unimodal_forecast_scored.jsonl`, 2026-08-09) — recompute `calibration_coverage` against it directly (`archive/aurora-forecaster/aurora_forecaster/scoring.py`) before doing any further covariate/encoding work. This is more fundamental than which stream/encoding wins and hasn't been checked since the original 4-origin run.
- Does the signed mean-variance portfolio survive multiple crypto cycles without depending on VVV/HYPE momentum or near-market-neutral concentration?
- Is the evaluation framework's strongest contribution the ledger-backed deflation (DSR+PBO), the sealed-holdout mechanism, or the backtest-to-live reconciliation verdict?
- Is there a strategy hypothesis strong enough to justify a new experiment after the failed Freqtrade paper run?
- What bounded signal grammar is broad enough to avoid LLM path dependence without making the search space unauditable?
