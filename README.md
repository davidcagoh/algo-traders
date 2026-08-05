# Algo Traders

Algorithmic-trading research workspace with one completed crypto experiment,
shared evaluation tooling, a cross-cutting knowledge base, literature, and
publications.

## Current experiment

[`freqtrade-experiment/`](freqtrade-experiment/) contains the complete
Hyperliquid/Freqtrade lifecycle: research, strategy selection, paper execution,
monitoring, and dated evidence.

The `HmmSmaSlopeV2` paper run is stopped and parked. The original 30-day gate
was incomplete with two closed trades. The full extended run closed 21 trades
for -35.40 USDC (-3.54%), with a 4.8% win rate and an 11-loss streak. See the
[canonical experiment record](freqtrade-experiment/EXPERIMENT.md).

Key paths:

- [Research](freqtrade-experiment/research/) — strategies, configs, data, backtests, and reports.
- [Execution records](freqtrade-experiment/execution/records/) — binding gate, checkpoints, final evaluation, and shutdown.
- [Monitoring](freqtrade-experiment/monitoring/) — read-only SQLite → Supabase → Vercel tape.
- [Mean-variance paper project](freqtrade-experiment/mean-variance-paper/) — collaborator-owned signed-MV paper monitor, separate from live monitoring.

## Shared material

- [Wiki](wiki/) — H3L hot/cold knowledge base with active threads, archives, concepts, and retained artifacts.
- [Evaluation](evaluation/) — reusable six-layer metrics, DSR, Freqtrade readers, and portfolio-diversification utilities.
- [Literature](literature/) — source PDFs and source-specific notes.
- [Quant research agent](quant-research-agent/) — research-loop pattern, search automation specification, and thematic source dives.
- [Publications](publications/) — outputs grouped by intellectual project; currently the six-layer evaluation framework.

## Layout

```text
algo-traders/
├── freqtrade-experiment/   # concrete crypto experiment
├── evaluation/             # reusable evaluation code
├── literature/             # PDFs and paper notes
├── publications/           # project-grouped public outputs
├── quant-research-agent/   # reusable autonomous-research workflow
└── wiki/                   # H3L shared knowledge and hot state
```

The archived SGX/IDX/HSI `trend_vol` records remain under
[`wiki/artifacts/equity-trend-vol/`](wiki/artifacts/equity-trend-vol/); their
implementation is not part of this repository.
