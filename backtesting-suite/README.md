# Backtesting suite

Platform-agnostic research backtesting optimized for rapid paper replication.
Strategies express only ideal target portfolio weights. Execution timing,
transaction costs, slippage, market impact, funding, borrow, constraints, and
accounting are independently configured and handled by an execution model.

## Install

From the repository root, using the existing Python environment:

```bash
freqtrade/.venv/bin/pip install -e evaluation-framework
freqtrade/.venv/bin/pip install -e 'backtesting-suite[dev]'
```

The suite is not coupled to Freqtrade; that environment is only a convenient
workspace Python runtime.

## Run

```bash
bt validate backtesting-suite/examples/btc_sma.yaml
bt run backtesting-suite/examples/btc_sma.yaml
bt run backtesting-suite/examples/cross_sectional_momentum.yaml
```

Or without installing the command:

```bash
PYTHONPATH=backtesting-suite:. freqtrade/.venv/bin/python \
  -m backtesting_suite.cli run backtesting-suite/examples/btc_sma.yaml
```

An identical config + dataset/features + strategy module + execution backend +
suite source produces the same content-addressed run ID. Artifacts are written to:

```text
backtest-artifacts/<experiment>/<run-id>/
├── resolved-config.yaml
├── dataset-manifest.json
├── metadata.json
├── summary.json
├── report.md
├── report.html
├── returns.parquet
├── equity.parquet
├── targets.parquet
├── executed_weights.parquet
├── ending_weights.parquet
├── turnover.parquet
├── trades.parquet
└── costs.parquet
```

`report.html` is a self-contained interactive dashboard with equity and benchmark
performance, rolling Sharpe and volatility, drawdowns, weights, exposure,
turnover, costs, monthly returns, return distribution, historical stress
windows, and the deepest drawdown episodes. Open it directly in any browser;
it does not require a server or internet connection.

Every new completed specification is also appended to
`backtest-artifacts/trials.jsonl` through the existing evaluation package.

## ClickHouse data

The ClickHouse account is used in read-only mode. Put `CLICKHOUSE_PASSWORD` in
the repository-root `.env` file; it is never written to snapshots or reports.
The data commands issue metadata queries or bounded `SELECT` queries only.

```bash
bt data sources
bt data inspect binance.candles_1m
bt data snapshot binance.candles_1m \
  --start 2024-01-01 --end 2024-03-31 \
  --symbol BTC --timeframe 1h --market spot
```

The command prints a local manifest path under `data/clickhouse/`. Use that
path as `data.manifest` in the usual run YAML, with the same timeframe and
canonical symbol (`BTC`). Snapshots are content-addressed and ignored by Git.
Daily date-only end values include the whole end date. Exports are capped at
2,000,000 rows by default; use a smaller range or universe if the cap is hit.

Hyperliquid candles are perpetual data and currently have no funding series in
the warehouse snapshot, so set `execution.funding: false` for those runs. The
ClickHouse Binance candle table is verified as spot only. The CLI refuses to
label it as perpetual.

`bt data inspect` catalogs schema and time coverage. Other warehouse domains
can be exported as bounded raw Parquet snapshots, for example:

```bash
bt data snapshot ivydb.opprcd2025 --start 2025-01-01 --end 2025-01-31 \
  --column date --column symbol --column cp_flag --column strike_price \
  --time-column date --instrument-column symbol --symbol AAPL
```

Raw snapshots are explicitly marked unsupported by the bar backtester. Feature
and target warehouse tables remain separate; target columns are never loaded
into strategy features by this workflow. Large tables require explicit column
selection, and all snapshots require time bounds.

## Strategy contract

Strategies live outside the suite and implement one method:

```python
class MyStrategy:
    def generate_targets(self, data, params):
        close = data.field("close")
        signal = close > close.rolling(100).mean()
        return signal.astype(float)  # UTC index × instruments
```

Target values are desired fractions of equity. Positive is long, negative is
short, zero is flat. A multi-asset strategy uses one column per instrument.
Strategies do not receive execution configuration and should not subtract fees
or funding themselves.

The examples include single-asset spot and perpetual SMA strategies plus a
12-asset long/short cross-sectional momentum strategy. The latter is explicitly
illustrative: its fixed present-day universe is not survivorship-bias safe.

Auxiliary point-in-time features can be declared in the run file:

```yaml
data:
  features:
    - name: macro
      path: data/market/normalized/macro/fred.parquet
      members: [VIXCLS, DFF]
      availability_lag: 1D
```

The strategy reads them with `data.feature("macro")`. `availability_lag` is
applied before forward filling onto the bar index.

## Execution and transaction costs

The built-in `bar` execution model:

- shifts targets by `signal_delay_bars`;
- fills at `open` or `close`;
- supports `rebalance_policy: every_bar` (restore exact target weights each
  bar) and `target_change` (hold drifting positions until the requested target
  vector changes);
- lets weights drift between rebalances;
- keeps cash and leveraged/short exposures explicit;
- applies positive funding as a payment by longs and receipt by shorts;
- charges annual borrow only on short notional;
- enforces portfolio constraints centrally;
- refuses to invent required missing prices by default. The optional
  `zero_return` policy carries held positions across isolated missing bars, but
  still refuses to fill a trade without a price.

Transaction costs are composable:

```yaml
execution:
  transaction_costs:
    - {type: proportional, name: fee, bps: 3.5}
    - {type: proportional, name: slippage, bps: 2.0}
    - {type: fixed, name: ticket, amount_per_trade: 1.0}
    - type: square_root_impact
      name: impact
      coefficient_bps: 20
      max_participation: 0.02
```

Custom execution backends implement `simulate(data, targets, config)` and are
selected with `execution.model: module:object`. Strategy code remains unchanged.

## Timing convention

With the recommended `price_field: open` and `signal_delay_bars: 1`, a target
computed from bar `t` data executes at bar `t+1` open and earns the return from
that open to the following open. The optional no-lookahead check reruns each
strategy on truncated data and rejects targets that change when future rows are
removed.

## Comparing runs

```bash
bt compare \
  backtest-artifacts/experiment/run-a \
  backtest-artifacts/experiment/run-b
```

Sweep a named proportional fee or slippage component without modifying the
strategy or creating extra configuration files:

```bash
bt sweep-costs backtesting-suite/examples/btc_sma.yaml \
  --component fee --bps 0 2.5 5 10
```

Existing identical scenarios are read from the cache. Each new scenario gets
its own immutable run directory and trial-ledger entry.
