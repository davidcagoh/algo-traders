# David’s ClickHouse data workflow

This guide covers David’s read-only ClickHouse access and local snapshot workflow. It is separate from [the shared backtest guide](backtest_guide.md), which remains focused on Ethan’s established backtesting workflow.

## Credentials and safety

Set `CLICKHOUSE_PASSWORD` in the repository-root `.env` file. The CLI reads it from the environment; do not put credentials in commands, config files, manifests, reports, or screenshots. The ClickHouse client issues metadata queries and bounded `SELECT` queries only. Snapshots are written locally under the ignored `data/clickhouse/` directory.

## Discover available data

Install the suite in the existing repository Python environment if needed:

```bash
freqtrade/.venv/bin/pip install -e evaluation-framework
freqtrade/.venv/bin/pip install -e 'backtesting-suite[dev]'
```

List warehouse databases and tables, then inspect a table’s schema and coverage:

```bash
bt data sources
bt data inspect binance.candles_1m
```

## Export a bounded snapshot

Always choose explicit time bounds. For example, export Binance BTC spot candles aggregated to hourly bars:

```bash
bt data snapshot binance.candles_1m \
  --start 2024-01-01 --end 2024-03-31 \
  --symbol BTC --timeframe 1h --market spot
```

The command prints a local manifest path. Date-only end values include the whole end date. Exports are capped at 2,000,000 rows by default; narrow the date range or instrument selection if the cap is reached. Snapshot content is addressed by hash, so identical exports reuse the same data identity.

Hyperliquid candles are perpetual data and the warehouse snapshot does not include funding. Use `--market perpetual` and configure `execution.funding: false` when running these snapshots. Binance candles are verified spot data; the CLI will not label them as perpetual.

## Run a supported bar snapshot

Use the printed manifest in the regular run configuration, with matching timeframe and canonical symbol:

```yaml
data:
  manifest: data/clickhouse/<snapshot>/manifest.json
  market: spot
  timeframe: 1h
  universe: [BTC]
  start: 2024-01-01
  end: 2024-03-31
```

Then use the normal local workflow:

```bash
bt validate path/to/run.yaml
bt run path/to/run.yaml
```

The resulting run artifacts record the dataset manifest and its identity.

## Export other warehouse tables

Tables outside the supported candle sources can be saved as bounded raw Parquet snapshots by selecting a time column and, where relevant, an instrument column:

```bash
bt data snapshot ivydb.opprcd2025 \
  --start 2025-01-01 --end 2025-01-31 \
  --column date --column symbol --column cp_flag --column strike_price \
  --time-column date --instrument-column symbol --symbol AAPL
```

Raw snapshots are marked unsupported by the bar backtester. Inspect the manifest and domain semantics before using a table for research. Feature tables and future-horizon targets must remain separate to avoid look-ahead leakage.

## Data boundaries

- Binance and Hyperliquid candles can be normalized for the existing bar engine, subject to their market and funding semantics.
- CRSP, feature warehouse, options, and prediction-market data require domain-specific validation or execution models before their results can be treated as bar backtests.
- Local snapshots are bounded research inputs; they do not replace source data or alter the shared backtest configuration contract.
