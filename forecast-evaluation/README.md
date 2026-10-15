# TimesFM 3.0 ClickHouse evaluation

This isolated evaluation uses the pinned BTC/ETH hourly snapshot and protocol
in [`protocol.md`](protocol.md). New model, scoring, and viewer code stays in
this directory. The ClickHouse snapshot itself is local and git-ignored.

## Install

Create a dedicated environment so this experiment does not change the repo's
other Python projects:

```bash
uv venv forecast-evaluation/.venv
uv pip install --python forecast-evaluation/.venv/bin/python \
  -e 'forecast-evaluation[model,report,test]'
```

TimesFM 3.0 downloaded/self-hosted weights are restricted to non-commercial,
non-production use. The TimesFM package code's Apache license does not change
the checkpoint's weight terms. The current host's preflight must show at least
4 GiB available RAM before loading the 330M checkpoint; use batch size 1. The
checkpoint is pinned by immutable Hub revision and stays in the local Hugging
Face cache, never in this repository.

## Run

From the repository root, using the dedicated environment:

```bash
forecast-evaluation/.venv/bin/timesfm-eval validate
forecast-evaluation/.venv/bin/timesfm-eval evaluate
forecast-evaluation/.venv/bin/timesfm-eval report \
  forecast-evaluation/runs/<run-id>
```

The evaluator verifies the manifest ID and Parquet SHA-256 before inference.
It saves per-origin forecasts, score tables, model and protocol provenance,
and the run identity under `forecast-evaluation/runs/`. A run identity includes
the snapshot, frozen protocol, and evaluator source hash; an existing identical
run is not overwritten.

The first command evaluates BTC and ETH separately. Once the univariate path
passes, add the joint BTC/ETH mode:

```bash
forecast-evaluation/.venv/bin/timesfm-eval evaluate --include-multivariate
```

The report is generated from saved files only. It embeds Plotly locally and
opens without ClickHouse, TimesFM weights, a server, or network access.

## Statistical review bundle

After the forecasts are saved, add paired forecast-loss uncertainty and a
family-wise multiple-comparison adjustment without rerunning the model:

```bash
forecast-evaluation/.venv/bin/timesfm-eval analyze \
  forecast-evaluation/runs/<run-id>
```

This creates a versioned review bundle under
`forecast-evaluation/analyses/<run-id>/<analysis-id>/` with `analysis.json`
and a standalone `report.html`. It reuses the shared stationary-bootstrap
index generator, resamples paired origin losses jointly across BTC/ETH and
forecast modes, and applies Holm correction across every saved lead and
cumulative-horizon comparison. The fixed defaults are 10,000 replicates, a
mean block length of four origins, and seed `20261014`.

The statistical protocol was specified after inspecting the existing run, so
the results are exploratory. It does not establish a confirmatory model win or
a trading edge. See [`method-map.md`](method-map.md) and
[`coverage-audit.md`](coverage-audit.md) for the estimand, method choices,
coverage limits, and provenance.

## Test without network or weights

```bash
forecast-evaluation/.venv/bin/python -m pytest forecast-evaluation/tests
```

The suite uses mocked forecasts and temporary Parquet snapshots. It does not
connect to ClickHouse or download a checkpoint.
