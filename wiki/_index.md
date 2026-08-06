# Algo Traders Wiki

Shared knowledge distilled from trading experiments; concrete results remain with their owning project.

> **Now:** `evaluation-framework/evaluation/` is built out as an installable, tested package (ledger, PBO, purged splits, sealed holdout, costs, live reconciliation — 155 tests, 96% coverage) per `evaluation-framework/PLAN.md`. The cross-project trial registry (`project`/`venue`/`evidence_stage`/`gate_outcome` on `TrialRecord`) now spans both `hmm-slope-experiment` and `mean-variance-paper`. All `hmm-slope-experiment` analysis drivers are migrated onto the package (formula duplication removed); doing so surfaced and fixed a real annualisation bug in `run_correlation_mdb.py` (was silently using 252 instead of crypto's 365).
> **Queue:** Review the first adaptive-keyword literature PR; separately cross-cycle validate signed MV or park it before another paper run.

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
- [`../evaluation-framework/`](../evaluation-framework/) — reusable evaluation code and its evolving manuscript/essays.
- [`../literature/`](../literature/) — primary sources, paper notes, and literature indexes.
- [`../quant-research-agent/`](../quant-research-agent/) — reusable search and research-loop automation.

Promotion rule: only reusable conclusions belong here. Experiment-specific facts remain with their experiment and are linked as evidence.
