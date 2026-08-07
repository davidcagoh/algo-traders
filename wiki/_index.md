# Algo Traders Wiki

Shared knowledge distilled from trading experiments; concrete results remain with their owning project.

> **Now:** `mean-variance-paper`'s forward accumulation is fixed and fully automated (2026-08-07, confirmed end-to-end). The original design re-ran a full backtest over Hyperliquid's ~208-day capped window each day, which structurally froze N at 148 forever; `forward_state.py` now persists equity/notional/day_counter and advances one real day at a time, backfilled with the 148 days already observed. Daily GitHub Action `.github/workflows/forward-accumulation.yml` (cron `30 1 * * *` UTC) refreshes data, runs the accumulation, commits state back to `main`, and pings healthchecks.io — verified via manual `workflow_dispatch`: correctly no-op'd on a same-day rerun, success ping confirmed received. ~102 more days to the N=250 DSR-binding floor, unattended from here. Signed MV's first-148-day result (dominates equal-weight on Sharpe/Calmar/return, triggers decision-012's Kill If rule on max drawdown) is still not settled: needs a bootstrap CI on the MDD gap before trusting a point estimate below the DSR-binding floor.
> **Queue:** Bootstrap the MDD CI; relay the TON delisting to Ethan. Separately: `aurora-forecaster/` now has a working rolling-forecast loop + scoring module + a visualization joining both (2026-08-07) — first real result on 4 BTC origins found badly overconfident calibration (nominal 50/80/95% coverage only ~20/28/38% empirical), still needs its four text sources aligned into one input for the unimodal-vs-multimodal comparison, and its `artifacts/` output is still undecided between committed-evidence and `.gitignore`d. Also check for the literature-search workflow's first-ever PR (`gh run 31125217798`, triggered 2026-08-06).

---

## Routing Table

| If you need to… | Read |
|---|---|
| Know what is actionable or unresolved | [`open-threads.md`](open-threads.md) |
| Understand the latest workspace changes | [`session-log.md`](session-log.md) |
| Find confirmed findings or ruled-out directions | [`learnings-archive.md`](learnings-archive.md) (grep) |
| Find a committed cross-project decision | [`decisions-archive.md`](decisions-archive.md) (grep) |
| Read reusable methodology or reference material | [`concepts/`](concepts/) |
| Inspect retained historical evidence | [`artifacts/`](artifacts/) |

## File Inventory

### Hot state

- [`open-threads.md`](open-threads.md)
- [`session-log.md`](session-log.md)
- [`learnings-archive.md`](learnings-archive.md)
- [`decisions-archive.md`](decisions-archive.md)

### Concepts

- [`concepts/correlation-and-mdb.md`](concepts/correlation-and-mdb.md)
- [`concepts/cv-and-deflation.md`](concepts/cv-and-deflation.md)
- [`concepts/data-sourcing.md`](concepts/data-sourcing.md)
- [`concepts/divergence_portfolio_theory.md`](concepts/divergence_portfolio_theory.md)
- [`concepts/kill-criteria.md`](concepts/kill-criteria.md)
- [`concepts/live-execution.md`](concepts/live-execution.md)
- [`concepts/multi-objective-search.md`](concepts/multi-objective-search.md)
- [`concepts/random-projection-stability.md`](concepts/random-projection-stability.md)
- [`concepts/strategy-archetypes.md`](concepts/strategy-archetypes.md)

### Artifacts

- [`artifacts/equity-trend-vol/README.md`](artifacts/equity-trend-vol/README.md)
- [`artifacts/equity-trend-vol/decisions/001-track-a-gate.md`](artifacts/equity-trend-vol/decisions/001-track-a-gate.md)
- [`artifacts/equity-trend-vol/decisions/004-track-a-hedged-mechanism.md`](artifacts/equity-trend-vol/decisions/004-track-a-hedged-mechanism.md)
- [`artifacts/equity-trend-vol/decisions/006-cross-cycle-stress-test.md`](artifacts/equity-trend-vol/decisions/006-cross-cycle-stress-test.md)
- [`artifacts/equity-trend-vol/results/2026-05-20-cross-cycle-hsi-BINDING.md`](artifacts/equity-trend-vol/results/2026-05-20-cross-cycle-hsi-BINDING.md)
- [`artifacts/equity-trend-vol/results/2026-05-20-hedged-mechanism-heldout-BINDING.md`](artifacts/equity-trend-vol/results/2026-05-20-hedged-mechanism-heldout-BINDING.md)
- [`artifacts/equity-trend-vol/results/2026-05-20-hedged-mechanism-tuning.md`](artifacts/equity-trend-vol/results/2026-05-20-hedged-mechanism-tuning.md)
- [`artifacts/equity-trend-vol/results/2026-05-20-sanity-sweep.md`](artifacts/equity-trend-vol/results/2026-05-20-sanity-sweep.md)
- [`artifacts/equity-trend-vol/results/2026-05-20-sgx-idx-baseline.md`](artifacts/equity-trend-vol/results/2026-05-20-sgx-idx-baseline.md)

## Related Stores

- [`../freqtrade-experiment/`](../freqtrade-experiment/) — completed crypto experiment and evidence.
- [`../aurora-forecaster/`](../aurora-forecaster/) — new forecasting-archetype experiment (multimodal generative forecaster, DecisionIntelligence/Aurora); smoke-tested locally, text-context design still open.
- [`../evaluation-framework/`](../evaluation-framework/) — reusable evaluation code and its evolving manuscript/essays.
- [`../literature/`](../literature/) — primary sources, paper notes, and literature indexes.
- [`../quant-research-agent/`](../quant-research-agent/) — reusable search and research-loop automation.

Promotion rule: only reusable conclusions belong here. Experiment-specific facts remain with their experiment and are linked as evidence.
