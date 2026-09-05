# Algo Traders

Algorithmic-trading research workspace with one completed crypto experiment,
shared evaluation tooling, a cross-cutting knowledge base, literature, and
active writing projects.

## Current experiment

[`freqtrade-experiment/`](freqtrade-experiment/) contains two sibling projects:
the original HMM/slope lifecycle and a collaborator-owned mean-variance track.

The `HmmSmaSlopeV2` paper run is stopped and parked. The original 30-day gate
was incomplete with two closed trades. The full extended run closed 21 trades
for -35.40 USDC (-3.54%), with a 4.8% win rate and an 11-loss streak. See the
[canonical experiment record](freqtrade-experiment/hmm-slope-experiment/EXPERIMENT.md).

Key paths:

- [Research](freqtrade-experiment/hmm-slope-experiment/research/) — strategies, configs, data, backtests, and reports.
- [Execution records](freqtrade-experiment/hmm-slope-experiment/execution/records/) — binding gate, checkpoints, final evaluation, and shutdown.
- [Monitoring](freqtrade-experiment/hmm-slope-experiment/monitoring/) — read-only SQLite → Supabase → Vercel tape.
- [Mean-variance paper project](freqtrade-experiment/mean-variance-paper/) — collaborator-owned signed-MV paper monitor, separate from live monitoring.

## Forecasting experiment

[`aurora-forecaster/`](aurora-forecaster/) — new forecasting archetype using
[DecisionIntelligence/Aurora](https://huggingface.co/DecisionIntelligence/Aurora),
a pretrained multimodal generative forecaster. Separate from
`freqtrade-experiment/` because it isn't a Freqtrade strategy. Smoke-tested
locally on Apple Silicon; see its README for status and open design
questions.

## Shared material

- [Backtesting guide](backtest_guide.md) — beginner-friendly steps from a strategy class to reports and cost sweeps.
- [EDA guide](EDA_guide.md) — beginner-friendly steps for finding, plotting, correlating, and regressing time series.
- [Wiki](wiki/) — H3L hot/cold knowledge base with active threads, archives, concepts, and retained artifacts.
- [Market dataset](market_data/DATASET_CHECKLIST.md) — shared crypto, derivatives, macro, market, on-chain, DeFi, and sentiment store with coverage checklist.
- [Time-series lab](timeseries-lab/) — searchable notebook API for loading, transforming, plotting, correlating, and regressing any stored series.
- [Backtesting suite](backtesting-suite/) — platform-agnostic target-weight simulation with independently configured execution and transaction costs.
- [Evaluation framework](evaluation-framework/) — reusable metrics package, manuscript, essay, and worked example in one ongoing project.
- [Literature](literature/) — indexed PDFs, paper notes, surveys, and per-thread search history.
- [Quant research agent](quant-research-agent/) — reusable research-loop pattern and search automation specification.

## Layout

```text
algo-traders/
├── backtesting-suite/     # platform-agnostic simulation and reporting
├── research_strategies/   # strategy logic, kept outside execution
├── market_data/           # reproducible shared-data ingestion
├── timeseries-lab/        # notebook-first time-series exploration
├── notebooks/             # runnable exploratory workflows
├── freqtrade-experiment/   # sibling crypto experiments
├── aurora-forecaster/      # multimodal forecasting experiment (Aurora)
├── evaluation-framework/  # evaluation code and evolving publication outputs
├── literature/             # PDFs and paper notes
├── quant-research-agent/   # reusable autonomous-research workflow
└── wiki/                   # H3L shared knowledge and hot state
```

The archived SGX/IDX/HSI `trend_vol` records remain under
[`wiki/artifacts/equity-trend-vol/`](wiki/artifacts/equity-trend-vol/); their
implementation is not part of this repository.
