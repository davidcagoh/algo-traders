# Evaluation Framework

A reusable evaluation package first, methods paper second — see
[`STATUS.md`](STATUS.md) for the priority call and current state, and
[`PLAN.md`](PLAN.md) for the phased build-out.

- [`evaluation/`](evaluation/) — reusable Python metrics, Freqtrade readers,
  DSR, and portfolio-diversification utilities.
- [`../literature/strategy-evaluation/_index.md`](../literature/strategy-evaluation/_index.md)
  — screened evaluation literature backing every module in the plan.
- [`archive/manuscript-2026-05/`](archive/manuscript-2026-05/) — the May 2026
  methods-paper draft (manuscript, essay, worked example), archived and
  stale; see its README before citing anything in it.
- [`archive/ranking-narrative.md`](archive/ranking-narrative.md) — superseded
  discovery narrative retained for provenance.

Experiment evidence remains under [`../freqtrade-experiment/`](../freqtrade-experiment/).

## Relationship to forecast_eval (time-series)

`time-series/forecast_eval/` scores predicted-vs-realized forecast values
(CRPS, MASE, calibration coverage, a Diebold-Mariano paired test) — it has
no trade/position/portfolio concept. This package scores realized
trade/portfolio returns and assumes something has already been traded.
Boundary: needs a position/trade/portfolio weight → here; only needs a
(predicted, realized) pair → forecast_eval. `evaluation.spa` (Hansen's SPA)
here and `diebold_mariano` there are the same statistical family applied one
level apart — not merged, since they operate on different units, but worth
knowing both exist before reinventing one from the other.
