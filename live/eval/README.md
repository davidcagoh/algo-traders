# live/eval/

Six-layer evaluation stack. Cross-venue port from `feishu/eval/`.

## Differences vs feishu/eval/

| Field | feishu | live |
|---|---|---|
| Annualisation | hardcoded 242 | per-call parameter; venue constants in `layers.py` |
| `competition_score` | included in `LayeredMetrics` | removed (track-specific scoring lives in gate driver) |
| Index assumption | ordinal `D001`..`D484` | works with either ordinal strings or DatetimeIndex |
| DSR carve-out | inlined comment | exported as `is_dsr_binding()` helper |

## Venue constants

```python
from live.eval import SGX_ANNUAL, IDX_ANNUAL, CRYPTO_ANNUAL, ASHARES_ANNUAL
```

| Constant | Value | Use |
|---|---|---|
| `SGX_ANNUAL` | 252 | SGX equities (Track A) |
| `IDX_ANNUAL` | 245 | IDX equities (Track A) |
| `CRYPTO_ANNUAL` | 365 | Hyperliquid perps (Track B) |
| `ASHARES_ANNUAL` | 242 | reference (feishu) |

## Files

- `layers.py` — L1/L2/L3/L5 metrics + `compute()` aggregator
- `dsr.py` — L4 Deflated Sharpe + carve-out helper
- `correlation_mdb.py` — L6 MDB + correlation

## Usage sketch

```python
import pandas as pd
from live.eval import compute, SGX_ANNUAL, format_markdown_table

wallet = pd.Series(...)  # portfolio value over time
m = compute(wallet, annualisation=SGX_ANNUAL)
print(format_markdown_table(m, title="SGX trend_vol v1 — tuning window"))
```

## What's not ported yet

- `walk_forward.py`, `regime_analysis.py`, `pca_residual.py`, `ou_halflife.py`, `ic_correlation.py` — these are feishu-specific exploratory tools. Port on demand when a Track A or Track B experiment needs them.
- `backtest.py` — feishu competition backtester. Each track here has its own backtest harness (yfinance for Track A, Freqtrade for Track B).
- `run_eval.py` — driver. Each track will write its own driver against this layer pack.
