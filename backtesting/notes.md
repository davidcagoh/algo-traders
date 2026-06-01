# Hyperliquid - things to note
- USDC as the quote currency
- Futures pair notation: `BTC/USDC:USDC` (base/quote:settle)
- Data format on disk: Feather

# Backtesting command

Updated 2026-04-24 — paths are now repo-relative. See `wiki/_index.md` for the full setup / download flow.

```shell
freqtrade backtesting \
  --userdir user_data \
  -c user_data/config.json \
  --data-format-ohlcv feather \
  -s LongOnlyStrategy -i 5m \
  -p BTC/USDC:USDC \
  --eps --max-open-trades 1
```
