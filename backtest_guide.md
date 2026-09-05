# How to use Ethan's new backtesting suite:

The strategy decides what we want to own. The backtesting suite handles when
we trade, transaction costs, slippage, funding, borrow costs, and portfolio
limits.

## 1. Set up the suite once

From the repository root, run:

```bash
source freqtrade/.venv/bin/activate
pip install -e evaluation-framework
pip install -e 'backtesting-suite[dev]'
```

The suite uses this Python environment, but it does not depend on Freqtrade.

## 2. Add a strategy

Create a file such as `research_strategies/my_strategy.py`:

```python
import pandas as pd

from backtesting_suite.data import DataBundle


class MyStrategy:
    def generate_targets(self, data: DataBundle, params) -> pd.DataFrame:
        close = data.field("close")
        average = close.rolling(params["window"]).mean()
        signal = close > average
        return signal.astype(float)
```

The strategy must return a DataFrame with timestamps as rows and symbols as
columns. Each value is the fraction of the portfolio we want in that symbol:

- `1.0` means 100% long.
- `0.5` means 50% long.
- `0.0` means no position.
- `-0.5` means 50% short.

Do not put fees, slippage, funding, or trade timing inside the strategy. Those
belong in the execution settings.

## 3. Create a backtest file

Copy an example:

```bash
cp backtesting-suite/examples/btc_sma.yaml \
  backtesting-suite/examples/my_strategy.yaml
```

Then edit the new YAML file. The main sections are:

```yaml
experiment: my_strategy

data:
  manifest: data/market/manifest.json
  market: spot
  timeframe: 1d
  universe: [BTC, ETH]
  start: 2020-01-01
  end: 2026-07-31

strategy:
  import: research_strategies.my_strategy:MyStrategy
  params:
    window: 100
  no_lookahead_check: true

execution:
  model: bar
  price_field: open
  signal_delay_bars: 1
  rebalance_policy: target_change
  initial_cash: 100000
  funding: false
  annual_borrow_bps: 0
  missing_price_policy: raise
  transaction_costs:
    - {type: proportional, name: fee, bps: 5}
    - {type: proportional, name: slippage, bps: 3}
  constraints:
    max_gross_exposure: 1.0
    max_net_exposure: 1.0
    max_abs_weight: 1.0
    min_cash_weight: 0.0
    violation: raise

evaluation:
  profile: research
  benchmark: BTC
  bootstrap_samples: 0
  regimes: true

artifacts_dir: backtest-artifacts
```

With `signal_delay_bars: 1`, a signal calculated today trades at the next bar's
open. This is the recommended starting point because it avoids trading on
information we did not have yet.

Use `market: perpetual` and `funding: true` when testing perpetual futures.

## 4. Check and run the backtest

From the repository root:

```bash
bt validate backtesting-suite/examples/my_strategy.yaml
bt run backtesting-suite/examples/my_strategy.yaml
```

`validate` checks that the configuration and requested data exist. `run`
generates the targets, checks for simple look-ahead problems, runs execution,
and creates the report.

If the exact same run already exists, the suite will show its folder instead of
silently overwriting it. Use `--force` only when you intentionally want to
recalculate it.

## 5. Read the results

Results appear under:

```text
backtest-artifacts/my_strategy/<run-id>/
```

Start with:

- `report.html` for the interactive charts and tables.
- `report.md` for the short written report.
- `summary.json` for the headline numbers.
- `equity.parquet` for portfolio value over time.
- `trades.parquet` for every simulated fill.
- `costs.parquet` for fees, slippage, funding, and borrow costs.
- `executed_weights.parquet` for the positions actually held.

The folder also contains the exact configuration, data manifest, and source
hashes used for the run.

## 6. Test different transaction costs

Change a named proportional cost without changing the strategy or making more
YAML files:

```bash
bt sweep-costs backtesting-suite/examples/my_strategy.yaml \
  --component fee --bps 0 2.5 5 10
```

This prints the return, Sharpe ratio, and total costs for each assumption. Each
assumption also gets its own result folder.

## 7. Compare completed runs

```bash
bt compare \
  backtest-artifacts/my_strategy/<first-run-id> \
  backtest-artifacts/my_strategy/<second-run-id>
```

For simple investigation before writing a strategy, use
[`EDA_guide.md`](EDA_guide.md).
