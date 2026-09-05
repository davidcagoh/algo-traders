# Shared market-data store

This directory defines the reproducible data layer shared by paper replications
and backtests. Generated data lives in `data/market/` and is intentionally not
committed; `data/market/manifest.json` records the exact local build.

## Build

Use the existing Freqtrade Python environment, which already contains pandas,
Requests, PyArrow, and the Freqtrade data handlers:

```bash
freqtrade/.venv/bin/python market_data/build_dataset.py --groups all
```

Add `--refresh` to replace cached raw responses. Individual groups can be
refreshed independently, for example:

```bash
freqtrade/.venv/bin/python market_data/build_dataset.py --groups macro markets
```

Hyperliquid full-history funding is heavily rate-limited. The builder resumes
from a page-level raw checkpoint. Use `--hyperliquid-local-only` for a fast,
deterministic rebuild from the experiment's existing cache.

## Layout

```text
data/market/
├── raw/           # cached, source-native ZIP/CSV/JSON responses
├── normalized/    # research tables in long-form UTC Parquet
├── freqtrade/     # per-pair Parquet files using Freqtrade names/schema
└── manifest.json  # row counts, coverage, members, hashes, validation
```

The canonical universe and source-series definitions are in `catalog.json`.
The normalized OHLCV schema uses `timestamp`, UTC, explicit venue and market,
base and quote volumes, trade count, and taker-buy volumes. Daily crypto bars
are derived from hourly bars on UTC boundaries, so the two resolutions cannot
silently disagree.

## Explore in notebooks

[`timeseries-lab/`](../timeseries-lab/) adds searchable string addresses,
selective loading, transforms, alignment, plotting, correlations, and quick
regressions without creating another copy of the store. Start with
[`notebooks/timeseries_quickstart.ipynb`](../notebooks/timeseries_quickstart.ipynb).

## Research rules

- Use `manifest.json` in every result bundle to pin the dataset build.
- Treat the catalog as a present-day monitoring universe, not point-in-time
  membership. Apply listing-date and liquidity filters inside each backtest.
- Lag macro releases by their publication timestamp when testing predictive
  claims. FRED observation dates are not release timestamps.
- Continuous futures from Yahoo are monitoring features, not execution prices.
- Keep source/venue fixed inside a comparison, or explicitly model basis and
  venue effects.
