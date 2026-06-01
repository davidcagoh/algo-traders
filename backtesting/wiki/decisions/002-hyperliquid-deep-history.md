# Hyperliquid deep-history data sourcing

**Date:** 2026-04-24
**Status:** decided (accept the constraint for now)

## Decision

Use `scripts/download_hyperliquid.py` (hits the public `/info candleSnapshot` endpoint directly) as the baseline data source, capped at ~5000 candles per (pair, timeframe). **Note:** freqtrade's own `download-data` command does *not* work for Hyperliquid — verified 2026-04-24, the adapter sets `ohlcv_has_history=False` and the command refuses with "Hyperliquid does not support downloading trades or ohlcv data." The custom script is the workaround. If deeper history becomes necessary, reconstruct from Hyperliquid's S3 archive rather than hunting for a third-party dump.

## Why

Hyperliquid's public API only returns ~5000 historic candles per request, and the exchange **does not publish bulk OHLCV data**. Confirmed from the official docs (`hyperliquid.gitbook.io/hyperliquid-docs/historical-data`): "No other historical data sets are provided via S3 (e.g. candles or spot asset data)."

This is also visible inside freqtrade itself — `freqtrade/exchange/hyperliquid.py` sets:
```python
"ohlcv_has_history": False,
"trades_has_history": False,
```

So no downloader — freqtrade's or otherwise — can pull deep OHLCV directly. That is why Ethan had to source data "from elsewhere" last year, and why he couldn't retrace where he got it: there is no canonical source.

What 5000 candles covers:

| Timeframe | Window | Adequate for |
|-----------|--------|--------------|
| 1m | ~3.5 days | Intraday signal work |
| 5m | ~17 days | Short-horizon strategy sanity checks |
| 15m | ~52 days | Multi-day swing |
| 1h | ~208 days | Most trend strategies |
| 4h | ~833 days | Longer-horizon / regime work |
| 1d | 5000+ days (exchange age caps this) | Macro |

## Options if 5000 candles is not enough

1. **Incremental accumulation.** Run `freqtrade download-data` on a schedule — freqtrade appends new candles. Over time this builds a proprietary deep history. Fine for "start trading soon", useless for "backtest 2023".
2. **Reconstruct from S3 L2 snapshots.** Hyperliquid publishes L2 book snapshots at `s3://hyperliquid-archive/market_data/` and asset contexts at `s3://hyperliquid-archive/asset_ctxs/`. Candles can be rebuilt from these. Significant data-engineering cost; only worth it if multi-year deep history is a hard requirement.
3. **Third-party aggregator.** tardis.dev and similar cover Hyperliquid for a fee. Lowest effort, ongoing cost.

## Consequences

- No blocker for getting a working backtest loop running today.
- Strategies requiring multi-year 1m data on Hyperliquid are off-limits without extra work.
- If a given strategy works on 1h / 4h data, there's no problem — 5000 candles is plenty.
- Profiling and "speed" work (the original revisit goal) is still the right next step once the loop runs.
