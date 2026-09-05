# How to use Ethan's new EDA tools:

The time-series lab is for quick investigation before writing a full strategy.
It lets us search the shared data, load a series with one string, make plots,
compare variables, and run a quick regression.

It reads the existing files in `data/market/`. It does not make another copy of
the database.

## 1. Set up the tools once

From the repository root, run:

```bash
source freqtrade/.venv/bin/activate
pip install -e 'timeseries-lab[plot,notebook,dev]'
```

Open [`notebooks/timeseries_quickstart.ipynb`](notebooks/timeseries_quickstart.ipynb)
and select `freqtrade/.venv/bin/python` as the Python kernel.

You can also use these commands in any other notebook.

To update the local store before starting, run either all data groups or only
the groups you need:

```bash
python market_data/build_dataset.py --groups all
python market_data/build_dataset.py --groups macro markets
```

The available groups are `crypto`, `funding`, `macro`, `markets`, `onchain`,
`defi`, and `sentiment`. Add `--refresh` when you want to replace cached source
downloads. Create a new `TimeSeriesLab()` after a data build finishes so it
reads the new manifest.

## 2. Start the lab

```python
from timeseries_lab import TimeSeriesLab

lab = TimeSeriesLab()
```

## 3. Search for data

Type any useful word or symbol:

```python
lab.search("vix")
lab.search("BTC funding")
lab.search("Treasury")
lab.search("S&P 500")
```

The result shows the exact series IDs, descriptions, and available dates.

A full series ID normally looks like:

```text
table:member:field
```

Examples:

```text
spot_1d:BTC:close
perpetual_1h:ETH:quote_volume
funding_binance:BTC:funding_rate
fred:VIXCLS:value
traditional_daily:SPY:close
coinmetrics_daily:btc:AdrActCnt
```

Some shorter names work too. For example, `fred:VIXCLS` automatically uses the
`value` field. If a short name such as `BTC` could mean several things, the lab
will ask for a more specific ID and show suggestions.

## 4. Load one series

```python
btc = lab["spot_1d:BTC:close"]
vix = lab["fred:VIXCLS"]

btc.tail()
```

The result is a pandas Series with UTC timestamps. Normal pandas commands such
as `.head()`, `.tail()`, `.describe()`, and `.loc[]` work normally.

## 5. Transform a series

Add transformations after `|`:

```python
btc_returns = lab["spot_1d:BTC:close | log_return"]
vix_change = lab["fred:VIXCLS | diff"]
funding_zscore = lab[
    "funding_binance:BTC | resample:1D:sum | rolling_zscore:90"
]
weekly_btc = lab["spot_1d:BTC:close | resample:W:last"]
```

Useful transformations are:

- `pct_change` for percentage returns.
- `log_return` for log returns.
- `diff` for changes in levels.
- `lag:1` for the previous observation.
- `shift_time:1D` for moving the timestamp forward by one day.
- `rolling_mean:30` for a 30-observation moving average.
- `rolling_zscore:90` for a rolling 90-observation z-score.
- `resample:1D:sum` or `resample:W:last` for changing frequency.
- `normalize` for rebasing a series to 100.

Transformations run from left to right.

## 6. Put several series in one table

```python
panel = lab.frame(
    {
        "btc_return": "spot_1d:BTC:close | log_return",
        "vix_change": "fred:VIXCLS | diff",
        "two_year_change": "fred:DGS2 | diff",
    },
    start="2020-01-01",
    end="2026-07-31",
    freq="1D",
    fill="ffill",
    fill_limit=4,
)

panel.tail()
```

The names on the left become the column names. `freq="1D"` puts the series on
a daily calendar. `fill="ffill"` carries the last known value forward, and
`fill_limit=4` stops it from filling a long missing period.

## 7. Plot series

```python
lab.plot(
    {
        "BTC": "spot_1d:BTC:close",
        "S&P 500": "traditional_daily:SPY:close",
    },
    start="2020-01-01",
    normalize=True,
    title="BTC and the S&P 500",
)
```

`normalize=True` rebases both lines to 100 so their percentage performance is
easy to compare. The returned Plotly chart is interactive inside the notebook.

## 8. Check correlations

Use returns or changes when comparing market relationships:

```python
lab.correlation(
    {
        "btc": "spot_1d:BTC:close | log_return",
        "eth": "spot_1d:ETH:close | log_return",
        "spy": "traditional_daily:SPY:close | log_return",
    },
    start="2020-01-01",
    freq="1D",
    join="inner",
)
```

This returns a normal pandas correlation matrix.

## 9. Run a quick regression

The first argument is what we want to explain. The second argument contains the
variables that may explain it:

```python
result = lab.regress(
    "spot_1d:BTC:close | log_return",
    {
        "vix_change": "fred:VIXCLS | diff",
        "two_year_change": "fred:DGS2 | diff",
    },
    start="2020-01-01",
    freq="1D",
    fill="ffill",
    fill_limit=4,
)

result.summary
```

The summary includes the coefficient, standard error, t-statistic, and an
approximate p-value for each variable. Newey-West standard errors are used by
default because time-series errors are often related across nearby dates.

This is a quick diagnostic. A significant result does not prove that one
variable causes another or that the relationship will work in a backtest.

## 10. Add a paper's CSV or Parquet series

The file needs one timestamp column and one numeric value column:

```python
paper_signal = lab.read_file(
    "downloads/paper_signal.csv",
    timestamp="date",
    value="signal",
    name="paper signal",
)

lab.plot(
    {
        "paper signal": paper_signal,
        "BTC": "spot_1d:BTC:close",
    }
)
```

The same pandas Series can be passed into `lab.frame()`, `lab.correlation()`, or
the explanatory variables in `lab.regress()`.

## 11. Avoid the common mistakes

- Do not use future data to explain the past. Use `lag` or `shift_time` when
  appropriate.
- FRED dates are observation dates, not guaranteed release timestamps. A result
  can look predictive if we pretend a macro number was known too early.
- Forward filling is sometimes reasonable. Backward filling uses future data
  and is normally unsafe for research.
- Full-sample `zscore` uses future observations. Prefer `rolling_zscore` for a
  time-based strategy.
- Correlation and regression are starting points, not trading results. Put a
  promising relationship into the backtesting suite before trusting it.

Once a relationship looks useful, follow [`backtest_guide.md`](backtest_guide.md)
to turn it into a strategy with explicit execution and transaction costs.
