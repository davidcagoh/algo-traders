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

## Shared material

- [Wiki](wiki/) — H3L hot/cold knowledge base with active threads, archives, concepts, and retained artifacts.
- [Evaluation framework](evaluation-framework/) — reusable metrics package, manuscript, essay, and worked example in one ongoing project.
- [Literature](literature/) — indexed PDFs, paper notes, surveys, and per-thread search history.
- [Quant research agent](quant-research-agent/) — reusable research-loop pattern and search automation specification.

## Layout

```text
algo-traders/
├── freqtrade-experiment/   # sibling crypto experiments
├── evaluation-framework/  # evaluation code and evolving publication outputs
├── literature/             # PDFs and paper notes
├── quant-research-agent/   # reusable autonomous-research workflow
└── wiki/                   # H3L shared knowledge and hot state
```

The archived SGX/IDX/HSI `trend_vol` records remain under
[`wiki/artifacts/equity-trend-vol/`](wiki/artifacts/equity-trend-vol/); their
implementation is not part of this repository.
