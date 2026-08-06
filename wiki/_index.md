# Algo Traders Wiki

Shared knowledge distilled from trading experiments; concrete results remain with their owning project.

> **Now:** New project `aurora-forecaster/` — a multimodal forecasting archetype (`DecisionIntelligence/Aurora`, arXiv:2509.22295), genuinely different from every existing archetype (predicts forward returns directly vs. trading a current mispricing to an anchor). Target securities BTC/SPY, chosen for domain-fit with Aurora's TimeMMD pretraining rather than the actual illiquid book. Full multimodal forward pass confirmed working end-to-end locally (Apple Silicon MPS) with all four text sources (GDELT, Alpha Vantage, Currents, Guardian) smoke-tested against live endpoints. Found and fixed a real bug in `aurora-model==0.2.0` along the way (batch-collapsing `.squeeze(0)` in its `generate(text_inputs=...)` path).
> **Queue:** Next for aurora-forecaster: align the four text sources into one per-timestep input and run the actual unimodal-vs-multimodal comparison. Separately: Ethan confirmed his Vercel paper monitor is deployed but not working, corroborating the proxy-backtest doubt on signed MV's edge — still need his call on whether cross-cycle validation should formally gate `mean-variance-paper`. Also check for the literature-search workflow's first-ever PR (`gh run 31125217798`, triggered 2026-08-06).

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
