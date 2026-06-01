# Drop the separate `freqtrade_hyperliquid_download-data` repo

**Date:** 2026-04-24
**Status:** decided

## Decision

Remove the `freqtrade_hyperliquid_download-data` gitlink and use freqtrade's native `download-data` into `freqtrade/user_data/data/hyperliquid/` instead.

## Why

Ethan created that separate repo last year because freqtrade didn't yet support Hyperliquid and he had to source OHLCV data externally. The current freqtrade main branch ships a Hyperliquid adapter, and `download-data` works for it — just with Hyperliquid-specific limits (see below). Keeping two repos wired together by a gitlink adds operational overhead for no remaining benefit.

## Consequences

- One repo to manage, not two.
- Data lives in the conventional freqtrade location, so no `--data-dir` override needed.
- We lose whatever historical candles Ethan had stockpiled in that separate repo. He can't find how he got them, so they weren't reproducible anyway. See `wiki/decisions/002-hyperliquid-deep-history.md` for how to rebuild deep history if needed.
