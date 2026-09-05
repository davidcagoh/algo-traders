# Time-series lab

A notebook-first exploration layer over `data/market/manifest.json`. It does not
copy data or introduce a new database. Instead, it gives each stored series a
searchable string address and handles selective Parquet reads, transformations,
calendar alignment, plotting, correlations, and quick OLS regressions.

## Install

From the repository root:

```bash
freqtrade/.venv/bin/pip install -e 'timeseries-lab[plot,notebook,dev]'
```

The existing environment is only a convenient Python runtime; the package has
no dependency on Freqtrade or the backtesting suite.

Refresh the underlying store with `python market_data/build_dataset.py --groups
all`, or select only the required data groups. Create a new `TimeSeriesLab`
instance after the build completes so it reads the updated manifest.

## Five-minute workflow

```python
from timeseries_lab import TimeSeriesLab

lab = TimeSeriesLab()

# Search IDs and human-readable descriptions.
lab.search("vix")
lab.search("BTC funding")

# Load one Series. The full address is table:member:field.
btc = lab["spot_1d:BTC:close"]
vix = lab["fred:VIXCLS"]              # unambiguous shorthand

# Compose explicit transforms in the query string.
btc_returns = lab["spot_1d:BTC:close | log_return"]
funding_z = lab["funding_binance:BTC | rolling_zscore:90"]

# Align different calendars with readable column names.
panel = lab.frame(
    {
        "btc": "spot_1d:BTC:close | log_return",
        "vix_change": "fred:VIXCLS | diff",
        "two_year_change": "fred:DGS2 | diff",
    },
    start="2020-01-01",
    freq="1D",
    fill="ffill",
    fill_limit=4,
)

# HAC errors are the default for exploratory time-series regressions.
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

lab.plot(
    {"BTC": "spot_1d:BTC:close", "S&P 500": "traditional_daily:SPY:close"},
    start="2020-01-01",
    normalize=True,
)

# Mix in a paper-supplied CSV without registering a new manifest table.
paper_signal = lab.read_file(
    "downloads/paper_signal.csv", timestamp="date", value="signal"
)
lab.plot({"paper signal": paper_signal, "BTC": "spot_1d:BTC:close"})
```

See [the quickstart notebook](../notebooks/timeseries_quickstart.ipynb) for a
runnable version.

## Address and transform grammar

Canonical addresses are:

```text
table:member:field
```

Memberless tables use `table:field`. Sensible defaults make
`fred:VIXCLS`, `funding_binance:BTC`, and `spot_1d:BTC` valid shorthands.
An ambiguous address such as `BTC` fails with concrete suggestions rather than
guessing a venue, market, frequency, or field.

Transforms are evaluated left-to-right after `|`:

- `pct_change[:periods]`, `log_return[:periods]`, `diff[:periods]`, `log`;
- `lag[:periods]` and `shift_time:<duration>`;
- `rolling_mean:<window>`, `rolling_std:<window>`, `rolling_zscore:<window>`;
- `resample:<frequency>[:last|first|mean|sum|max|min]`;
- `normalize`/`rebase`, and full-sample `zscore`.

Example:

```python
lab["funding_binance:ETH | resample:1D:sum | rolling_zscore:90 | lag:1"]
```

`read_file()` accepts one numeric series from CSV, TSV, or Parquet. A pandas
`Series` can be mixed directly with stored addresses in `frame()`, `plot()`,
`correlation()`, or the independent variables passed to `regress()`.

## Research cautions

- `fill="bfill"`, interpolation, full-sample `zscore`, and same-period
  regressions can introduce look-ahead. They are available for exploration, not
  automatically safe for backtesting.
- FRED rows are observation dates, not release timestamps. Use an explicit
  `shift_time` or a point-in-time release dataset for predictive work.
- A regression is a fast diagnostic, not causal identification. Reported
  p-values use a normal approximation; Newey-West errors address serial
  correlation but not endogeneity, multiple testing, or data mining.
- Use `TimeSeriesLab(verify_checksums=True)` when exact data integrity matters.
  The backtesting suite always verifies its selected inputs.
