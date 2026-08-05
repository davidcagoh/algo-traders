# Research analysis drivers

Experiment-specific evaluation and reporting built on the reusable package in
the repository root at [`../../../evaluation/`](../../../evaluation/).

- `eval_layers.py` — Freqtrade ZIP adapter and Layer-5 report generator
- `dsr_analysis.py` — DSR analysis across the selected backtest archives
- `run_correlation_mdb.py` — correlation matrix and MDB driver
- `combined_book_mdd.py` — candidate-book drawdown check
- `generate_pareto_chart.py` — experiment leaderboard visualization

These drivers intentionally remain local because they name this experiment’s
strategies, backtest archives, and output paths. Reusable metric calculations
and ZIP readers live in the root `evaluation/` package.
