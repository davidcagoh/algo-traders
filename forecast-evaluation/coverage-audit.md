# Forecast data coverage audit

## Decision

The pinned evaluation input is the latest BTC/ETH data available from the
configured ClickHouse source at the audit date. Preserve it as-is; do not
rewrite the existing snapshot or frozen forecast run.

## Evidence

- Read-only `bt data inspect binance.candles_1m` reported 937,760,295 estimated
  source rows and active-part temporal bounds from 2020-01-01 through
  **2026-09-16 23:59 UTC**. ClickHouse had no later source observations to
  snapshot as of 2026-10-14.
- The local normalized snapshot is `f1c29fc3e938bfa7b208`, from
  `binance.candles_1m`, 1-hour spot bars, BTC and ETH, requested 2024-01-01
  through 2026-09-16 inclusive. The manifest and Parquet SHA-256 are checked by
  `timesfm-eval validate` before analysis.
- Validation found 23,760 hourly bars per symbol, from 2024-01-01 00:00 through
  2026-09-16 23:00 UTC, no missing/duplicate hourly bars, positive finite
  closes, and identical BTC/ETH timestamp grids.
- Historical replay: 135 origins per symbol; origins are seven days apart and
  the longest forecast is 168 hours. Target windows at a given lead do not
  overlap. Each of leads 1–168 has 135 scored observations for each
  asset/mode; cumulative horizons 1, 6, 24, 72, and 168 hours each have 135.
  Context windows do overlap; resampling therefore operates over origin-level
  paired errors and uses blocks.
- Post-release freshness: 15 daily origins, 2026-09-01 through 2026-09-15,
  scored at leads 1, 6, and 24 (15 per asset/mode/lead). Only cumulative
  horizon 1 can be reconstructed from these sparse saved leads; no 6h or 24h
  cumulative values are available in that slice. The latest snapshot cannot
  increase this count. A new release-independent evaluation needs later
  upstream observations or a different source with validated identical
  coverage.
- The frozen run made 450 TimesFM inference calls: 405 historical and 45
  post-release across univariate and joint modes. The run metadata does not
  record elapsed inference time, so a wall-clock cost estimate cannot be
  recovered; future runs should record per-segment runtime.

## Scope and caveats

The source coverage bounds are ClickHouse active-part metadata, not a full
fresh query of the 937-million-row table. The bounded local snapshot provides
the exact observations used for every reported score. The post-release slice
is exploratory and low power; it is not the same as a large confirmatory
sample. Data availability does not make historical replay pretraining-clean.

## Reproduction

```bash
uv run --project backtesting-suite bt data inspect binance.candles_1m
forecast-evaluation/.venv/bin/timesfm-eval validate
```

The inspect command issues metadata/coverage reads only. It does not export or
modify warehouse data.
