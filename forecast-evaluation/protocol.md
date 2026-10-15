# TimesFM 3.0 BTC/ETH evaluation protocol

Status: frozen before model inference. Do not change the snapshot, origins,
transforms, horizons, or baselines after inspecting model scores. Any change
requires a new protocol version and run identity.

## Data pin

- Source: read-only `binance.candles_1m` ClickHouse snapshot, normalized to UTC
  hourly Binance spot OHLCV by the existing `bt data snapshot` workflow.
- Snapshot ID: `f1c29fc3e938bfa7b208`.
- Parquet SHA-256: `2b60d1bf63d96ba0098c9b04b84b13e396b1accd270c4439075d48f28e83167e`.
- Local manifest: `data/clickhouse/binance/candles_1m/f1c29fc3e938bfa7b208/manifest.json`
  (ignored local data; the ID and hash above are the tracked pin).
- Requested bounds: 2024-01-01 through 2026-09-16 inclusive, UTC.
- Observed bounds: 2024-01-01 00:00 through 2026-09-16 23:00 UTC.
- 23,760 rows each for BTC and ETH. Audit found no duplicate timestamps,
  missing hourly bars, or nonfinite closes. Recheck these invariants whenever
  loading the pinned snapshot.

## Forecast target and timing

For each symbol, calculate hourly close-to-close log returns
`r[t] = log(close[t] / close[t-1])`. The first return is undefined and is
discarded. An origin at bar timestamp `t` has observed returns through `t`;
the forecast at lead 1 is the return ending at the next hourly bar. No gap
filling, interpolation, scaling learned from future data, or cross-symbol
alignment repair is allowed. Reject invalid prices, duplicate timestamps,
irregular hourly grids, and nonfinite returns.

Use a fixed 512-return context for every model call. Keep BTC and ETH univariate
results separate. After those pass, run a joint two-target BTC/ETH forecast on
identical aligned origins as a secondary experiment. No covariates are used.

## Evaluation windows

TimesFM 3.0 was announced by Google Research on 2026-08-31. Target observations
before that date are a historical replay and may overlap model pretraining; do
not interpret that slice as an uncontaminated zero-shot test.

- **Historical replay:** origins every 168 hours, starting after 512 valid
  context returns; every scored target must end before 2026-08-31 00:00 UTC.
  Forecast all leads 1–168 hours. This gives nonoverlapping one-hour targets
  across origin windows at each lead and 135 origins per symbol.
- **Post-release freshness check:** origins daily at 00:00 UTC from 2026-09-01
  through 2026-09-15. Score leads 1, 6, and 24 hours only. These outcomes are
  strictly after release and available in the snapshot, but the approximately
  15 origins make this a low-power exploratory check, not confirmatory evidence.

All origins are UTC and chronological. Historical and freshness results must
be reported separately.

## Baselines and scores

Compare TimesFM to two frozen baselines:

1. **Zero return:** predict zero at every future hour (equivalent to a
   price-level random walk).
2. **Last-return persistence:** repeat the latest observed hourly return at
   every future hour.

At each forecast lead, score one-hour return MAE, RMSE, sign directional
accuracy, q10/q50/q90 pinball loss, q10–q90 empirical coverage, and mean band
width. Report nominal 80% bands as uncalibrated; sorted quantiles do not imply
calibration. At cumulative horizons 1, 6, 24, 72, and 168 hours, sum hourly
median/point forecasts and realized returns, then report cumulative-return
MAE/RMSE and skill versus each baseline. Do not sum marginal q10/q90 values or
present them as cumulative-return quantiles.

The short freshness check reports only leads 1, 6, and 24. Do not add
significance claims or trading-performance claims from this small sample.

## Model and reproducibility

- Package: `timesfm==3.0.2`; use the TimesFM 3.0 API, not the 2.5 wrapper.
- Backend: PyTorch CPU on the current host; batch size 1. Record actual device.
- Checkpoint: `google/timesfm-3.0-pytorch`, immutable revision
  `43046b85ec22d584a13f8098c2ed39c889e129c2`.
- Return quantiles q10 through q90, validate shapes/finiteness, and sort before
  scoring. Point forecast is q50 (index 4).
- The checkpoint license restricts downloaded/self-hosted weights to
  non-commercial, non-production use. Do not use these weights commercially or
  in production.
- Each run records snapshot ID and SHA-256, protocol version/hash, package and
  checkpoint revisions, model configuration, device, origin schedule,
  transforms, horizons, baselines, start time, and evaluation-code revision.
- Forecast once and persist raw per-origin outputs. The HTML viewer reads only
  these outputs; it must not need ClickHouse, model weights, or network access.

## Report views

The self-contained Plotly HTML report will provide:

- an interactive example of per-hour realized returns, median forecasts, and
  marginal q10–q90 bands, with the forecast origin marked;
- point-score and baseline-relative skill charts by lead and cumulative
  horizon;
- a nominal coverage chart with the 80% reference and corresponding band-width
  chart;
- separate historical and post-release sections, origin counts, snapshot/model
  provenance, and limitations.

Plot q10–q90 bands only for the marginal one-hour return at each lead. Do not
draw a cumulative fan from summed marginal quantiles.

## Sources

- Google Research announcement, 2026-08-31: <https://research.google/blog/timesfm-3-a-zero-shot-foundation-model-for-multivariate-forecasting/>
- Reviewed TimesFM 3.0 API and license notes:
  [`../wiki/skills/timesfm-forecasting/references/timesfm3.md`](../wiki/skills/timesfm-forecasting/references/timesfm3.md)
