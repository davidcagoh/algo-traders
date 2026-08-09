# Algo Traders Wiki

Shared knowledge distilled from trading experiments; concrete results remain with their owning project.

> **Now:** `aurora-forecaster`'s stream-ablation harness ran at n=12 origins (2026-08-09, 8/10 `STANDARD_CONFIGS` — `gdelt`/`gdelt+currents` still blocked by GDELT rate limiting): the striking n=4 `funding-vision` result (beat unimodal p=0.000) did **not replicate** — no config beats `unimodal` significantly at n=12. Next priority: revisit the original, more fundamental calibration-miscalibration finding (nominal 50/80/95% coverage vs. ~20/28/38% empirical, first found 2026-08-07 at n=4) against the now-available 12-origin `unimodal` ledger — scoped for a future session. Dashboard/leaderboard tooling (`artifacts/dashboard.html`, `leaderboard_history.jsonl`) now exists to track this across reruns.
> **Queue:** `mean-variance-paper`'s forward accumulation is automated and running (2026-08-07, `.github/workflows/forward-accumulation.yml`, daily cron, ~102 more days to N=250); still needs a bootstrap CI on the signed-MV MDD gap and the TON delisting relayed to Ethan. `GDELT_ONLY`/`GDELT_CURRENTS` remain low-priority-blocked. `aurora-forecaster/artifacts/` still undecided between committed-evidence and `.gitignore`d.

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
