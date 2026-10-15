# Algo Traders Wiki

Shared knowledge distilled from trading experiments; concrete results remain with their owning project.

> **Archive:** Feishu and Aurora were moved under [`archive/`](../archive/) on 2026-10-14. `backtesting-suite/` remains in place because ownership and ongoing work are uncertain. Aurora's n=12 result did not replicate its n=4 headline; dormant follow-ups are recorded in [`open-threads.md`](open-threads.md).
> **Now:** ClickHouse is available through bounded read-only snapshots for the existing `bt` manifest workflow. The TimesFM 3.0 BTC/ETH evaluation is reproducible, but its post-hoc tests found no Holm-adjusted significant comparison (minimum adjusted p=0.140); see [`forecast-evaluation/findings.md`](../forecast-evaluation/findings.md). `mean-variance-paper`'s latest recorded sample is N=216 (2026-10-14), with DSR checkpoint N=250.
> **Queue:** A confirmatory TimesFM result needs a prospectively frozen protocol and more post-release outcomes; current inference is exploratory. CSLab access and scheduler availability remain unverified until VPN access is available.

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
| Use the personal ClickHouse warehouse with backtests | [David's ClickHouse guide](../david_clickhouse_guide.md) |
| Reproduce the TimesFM demo and inspect its limits | [`forecast-evaluation/`](../forecast-evaluation/README.md) and [findings](../forecast-evaluation/findings.md) |

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

### Skills

- [`skills/timesfm-forecasting/`](skills/timesfm-forecasting/) — upstream forecasting reference with TimesFM 3.0 API and license notes.
- [`skills/cslab-compute/SKILL.md`](skills/cslab-compute/SKILL.md) — David-scoped CSLab access, Slurm, storage, and TimesFM resource workflow.
- [`skills/strategy-skills`](skills/strategy-skills) — local symlink to the strategy-skills collection; individual skills are also linked into Codex's default skill directory on David's machine.

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
- [`../backtesting-suite/`](../backtesting-suite/) — reusable bar simulation and execution layer.
- [`../evaluation-framework/`](../evaluation-framework/) — reusable portfolio metrics, statistical checks, and inference.
- [`../forecast-evaluation/`](../forecast-evaluation/) — forecast-versus-realized scoring and the TimesFM demonstration.
- [`../archive/aurora-forecaster/`](../archive/aurora-forecaster/) — archived forecasting-archetype experiment (multimodal generative forecaster, DecisionIntelligence/Aurora).
- [`../archive/feishu-competition/`](../archive/feishu-competition/) — archived competition project.
- [`../literature/`](../literature/) — primary sources, paper notes, and literature indexes.
- [`../quant-research-agent/`](../quant-research-agent/) — reusable search and research-loop automation.

Promotion rule: only reusable conclusions belong here. Experiment-specific facts remain with their experiment and are linked as evidence.
