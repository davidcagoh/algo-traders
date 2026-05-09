# Data Sourcing

**Status:** Working notes. Last updated 2026-05-09.

Default order of preference for market data, with the rationale for each. Goal: avoid reaching for exotic tools when boring free APIs cover the case.

---

## Default order

1. **Subproject's existing downloader** — if a subproject already has a verified path (e.g. `backtesting/scripts/download_hyperliquid.py`), use it. Don't reimplement.
2. **`ccxt`** — unified Python library wrapping ~100+ exchanges. Free, no auth for public endpoints. Covers OHLCV, funding rates, order book snapshots, public trades. First choice for any new exchange.
3. **Direct exchange REST API** — when ccxt's wrapper is missing a specific endpoint or imposes overhead you don't want. Binance, Bybit, OKX, Coinbase all publish documented free public APIs.
4. **Exchange S3 archives** — for bulk historical data that REST APIs cap (e.g., Hyperliquid L2 snapshots at `s3://hyperliquid-archive/market_data/`). Massive; only ingest when a specific hypothesis needs it.
5. **`yfinance`** — equities/ETFs/spot crypto, daily and hourly. Free. Use for macro covariates (SPY, DXY, VIX, gold) feeding into a crypto regime model. **Not** a perp/funding/intraday source.
6. **Scrapers (`Scrapling`, `playwright`, etc.)** — only when the data exists in a website but not in any API. Bookmark, don't default.

## Per-domain notes

### Crypto OHLCV

- Hyperliquid: custom downloader exists (`backtesting/scripts/download_hyperliquid.py`); 5000-candle hard cap per (pair, timeframe). 4h ≈ 833d, 1h ≈ 208d. See `backtesting/wiki/decisions/002`.
- Binance / Bybit / OKX perps: ccxt covers all. Binance BTC perp data goes back to ~2019 — useful for *training* regime models with more cycles, **not** for *evaluating* a Hyperliquid strategy (microstructure differs).
- Coinbase / Kraken spot: ccxt covers; useful for spot vs perp basis signals.

### Funding rates

- Binance: `/fapi/v1/fundingRate` — free, no auth, paginated, years of history.
- Bybit: `/v5/market/funding/history` — same.
- Hyperliquid: covered by `backtesting/scripts/download_hyperliquid.py --funding`; 8-hourly periods, incremental update support.
- Use case: CEX→DEX funding lead-lag (see `backtesting/wiki/learnings.md` open #6); funding-aligned HMM covariate (open #9); threshold-gated carry strategy (next experiment #2).

### Order book / microstructure

- Hyperliquid: REST `/info l2Book` for live snapshot; S3 archive for historical L2 (large, not yet ingested).
- Binance: WebSocket depth stream + REST snapshot; `python-binance` or ccxt pro for sustained capture.
- Use case: SaR slippage proxy (`backtesting/wiki/learnings.md` open #8); OFI as 1h mean-reversion signal (open #10).

### Equities / A-shares (feishu)

- Feishu competition: data is delivered by competition organisers in-band; no external sourcing needed for the IS+OOS windows.
- For independent equity research: `yfinance` (US), Tushare or AkShare (China A-share, free with rate limits).

### Macro covariates

- `yfinance` for SPY, DXY, VIX, gold, treasuries.
- FRED API (`fredapi`) for rates, CPI, M2 — free with key.

---

## Anti-patterns

- **Reimplementing what ccxt already wraps.** Confirm ccxt doesn't cover the endpoint before writing custom requests code.
- **Scraping when an API exists.** Adds anti-bot fragility; loses the rate-limit guarantees the API gives you.
- **Mixing CEX and DEX history without flagging the venue change.** Microstructure differences (fee, funding mechanism, liquidity tier) are not just numerical — they change which strategies work.
- **Ingesting S3 archives "in case we need them."** Storage cost is real; ingest only when an experiment is queued that needs them.
