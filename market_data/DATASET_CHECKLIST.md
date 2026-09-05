# Market dataset checklist

Build date: **2026-09-01**. Local store: `data/market/` (**640 MB**). Exact
row counts, members, coverage, SHA-256 hashes, and validation results are in
[`data/market/manifest.json`](../data/market/manifest.json). The reproducible
builder and universe are in [`market_data/`](./).

Status meanings: **acquired** = downloaded, normalized, and present locally;
**partial** = useful data is present but coverage, freshness, or source quality
does not meet the full target; **not acquired** = desired follow-up data.

## Acquired and usable now

- [x] **Crypto spot OHLCV — acquired.** 2,182,370 hourly bars and 91,016
  UTC-derived daily bars for 45 Binance USDT pairs, spanning 2017-08-17 through
  2026-07-31. Fields include OHLC, base/quote volume, trade count, and taker-buy
  base/quote volume. Universe: BTC, ETH, BNB, XRP, SOL, ADA, DOGE, TRX, LINK,
  AVAX, TON, DOT, LTC, BCH, XLM, UNI, ATOM, NEAR, APT, FIL, ETC, ICP, AAVE,
  ARB, OP, SUI, INJ, TIA, RUNE, SEI, TAO, FET, MATIC, POL, MKR, LDO, CRV, ENA,
  PAXG, SHIB, PEPE, BONK, WIF, USDC, and FDUSD. Source: [Binance Public
  Data](https://github.com/binance/binance-public-data). Normalized:
  `data/market/normalized/crypto/spot_1h.parquet` and `spot_1d.parquet`. Raw:
  `data/market/raw/binance/data/spot/monthly/klines/`.

- [x] **Crypto perpetual OHLCV — acquired.** 1,809,057 hourly bars and 75,393
  daily bars for 42 Binance USD-M perpetuals, spanning 2020-01-01 through
  2026-07-31. `1000SHIB`, `1000PEPE`, and `1000BONK` are normalized to their
  underlying symbols with an explicit `contract_multiplier`; no hidden unit
  conversion is applied. Normalized:
  `data/market/normalized/crypto/perpetual_1h.parquet` and
  `perpetual_1d.parquet`. Raw:
  `data/market/raw/binance/data/futures/um/monthly/klines/`.

- [x] **Exchange funding — acquired on Binance.** 244,398 funding observations
  for all 42 perpetuals, from 2020-01-01 through 2026-07-31. The table retains
  the venue-supplied interval because Binance has used both 4-hour and 8-hour
  funding. Location:
  `data/market/normalized/derivatives/funding_binance.parquet`.

- [x] **Spot/perpetual basis — acquired.** 1,794,451 hourly matched observations
  for 42 underlyings, from 2020-01-01 through 2026-07-31. Multiplier contracts
  are scale-adjusted before basis is calculated. Location:
  `data/market/normalized/derivatives/spot_perpetual_basis_1h.parquet`.

- [x] **S&P, Nasdaq, Russell, and tradable equity proxies — acquired.** Daily
  OHLCV/adjusted-close history for S&P 500, Nasdaq Composite, Russell 2000,
  SPY, QQQ, and IWM. The combined traditional-market table has 129,928 rows
  across 14 instruments and begins with S&P data on 1927-12-30. Source: Yahoo
  chart endpoint. Location:
  `data/market/normalized/markets/traditional_daily.parquet`.

- [x] **VIX — acquired from two sources.** CBOE VIX close from FRED (`VIXCLS`)
  from 1990-01-02 and daily Yahoo OHLC from 1990-01-02. Locations:
  `data/market/normalized/macro/fred.parquet` and the traditional-market table.

- [x] **US policy rate — acquired.** Effective fed funds (`DFF`), lower and
  upper target bounds (`DFEDTARL`, `DFEDTARU`), and SOFR, through 2026-08-28/31.
  Source: [FRED](https://fred.stlouisfed.org/). Location:
  `data/market/normalized/macro/fred.parquet`.

- [x] **US rates and yield curve — acquired.** Constant-maturity Treasury
  yields at 1m, 3m, 6m, 1y, 2y, 5y, 10y, and 30y; 10y–2y and 10y–3m spreads;
  plus TLT and the continuous 10-year Treasury-note futures contract. FRED
  series generally run through 2026-08-28/31; the longest Treasury series begin
  in 1962. Locations: macro and traditional-market tables.

- [x] **Financial conditions, credit, and dollar — acquired.** NFCI, US
  high-yield option-adjusted spread, HYG, broad trade-weighted dollar, and DXY.
  Locations: macro and traditional-market tables.

- [x] **Federal Reserve/Treasury liquidity — acquired.** Fed total assets
  (`WALCL`), overnight reverse repo (`RRPONTSYD`), and Treasury General Account
  (`WTREGEN`). Location: macro table.

- [x] **Inflation, labor, and money — acquired.** CPI, unemployment, nonfarm
  payrolls, and M2. The macro table contains 207,696 observations across 27
  successfully fetched FRED series, with overall history from 1939-01-01
  through 2026-08-31.

- [x] **Oil and gold — acquired.** FRED WTI spot plus Yahoo WTI futures, gold
  futures, and GLD. Locations: macro and traditional-market tables.

- [x] **BTC/ETH on-chain and valuation — acquired.** 10,501 daily Coin Metrics
  Community observations from 2009-01-03 through 2026-08-31: USD price, current
  market cap, active addresses, transaction count, and current supply for BTC
  and ETH. Source: [Coin Metrics Community API](https://docs.coinmetrics.io/api/v4/).
  Location: `data/market/normalized/onchain/coinmetrics_daily.parquet`.

- [x] **Stablecoin supply, DeFi TVL, and DEX volume — acquired.** 11,041 daily
  observations across aggregate USD stablecoin supply, total DeFi TVL, and
  total DEX volume, from 2014-02-17 through 2026-09-01. Source:
  [DefiLlama API](https://defillama.com/docs/api). Location:
  `data/market/normalized/defi/defillama_daily.parquet`.

- [x] **Crypto Fear & Greed — acquired.** 3,131 daily observations from
  2018-02-01 through 2026-09-01. Source:
  [Alternative.me](https://alternative.me/crypto/fear-and-greed-index/).
  Location: `data/market/normalized/sentiment/fear_greed_daily.parquet`.

- [x] **Freqtrade consumption layer — acquired and verified.** 174 per-pair
  Parquet files: spot 1h/1d for 45 pairs and futures 1h/1d for 42 pairs. Both
  BTC and ETH spot/futures files were recognized by `freqtrade list-data`, with
  the expected row counts and timeranges. Location: `data/market/freqtrade/binance/`.

## Partial, with explicit limitations

- [~] **Cross-exchange funding — partial.** 147,994 cached Hyperliquid funding
  observations for BTC, HYPE, PAXG, TON, TRX, VVV, WLFI, XPL, and ZRO, from
  2023-05-12 through 2026-06-09. The public endpoint throttled full-history
  refreshes during this build; the builder now checkpoints pages for resumable
  retries. Location:
  `data/market/normalized/derivatives/funding_hyperliquid.parquet`.

- [~] **Fresh crypto archive month — partial.** Binance’s monthly archive was
  complete locally through 2026-07-31 when built. August 2026 had not yet been
  published to the monthly archive. Refresh after publication; do not forward
  fill prices or funding across the missing month.

- [~] **Point-in-time crypto universe — partial.** Listing dates and delisted
  MATIC/MKR/TON tails are preserved, but the catalog is a present-day monitoring
  universe, not historical index membership. It does not include every failed
  or delisted coin. Backtests must apply listing-age and point-in-time liquidity
  rules to avoid survivorship bias.

- [~] **Traditional continuous futures OHLC — partial.** Yahoo contains 471
  rows where `close` falls outside the reported high/low (mostly early gold and
  Treasury continuous-contract history, plus a few WTI rows and one current VIX
  row). These rows are retained and flagged in the manifest; use close-only
  features or clean them before OHLC-dependent tests. Yahoo is also an
  unofficial, non-contractual endpoint.

- [~] **Gold fixing — partial.** FRED’s former London gold-fixing series returned
  HTTP 404. Gold futures and GLD were acquired instead; the missing series
  remains in `market_data/catalog.json` as a visible source gap.

- [~] **Macro vintage/release timing — partial.** FRED observation history is
  present, but ALFRED vintages and exact release timestamps are not. Lag macro
  features by when they were actually public; using observation dates directly
  can introduce look-ahead bias.

- [~] **On-chain breadth — partial.** Free Coin Metrics history covers the five
  selected BTC/ETH metrics. Realized cap, fees, exchange flows, miner flows,
  holder cohorts, and broad alt-chain metrics require other sources or paid
  credentials.

## Desired next data, not acquired in this build

- [ ] **Perpetual open interest, liquidations, and long/short ratios.** Binance
  exposes daily bulk metrics, but ingesting thousands of one-day archives needs
  a separate partitioned job and clearer retention policy.

- [ ] **Options surface.** Deribit/CME implied volatility, skew, term structure,
  volume, and open interest would materially improve volatility-paper tests.

- [ ] **Tick trades and order-book depth.** Needed for execution, slippage,
  market-impact, and microstructure papers; too large for this bar-level store.

- [ ] **Point-in-time market-cap ranks and complete delisting history.** Needed
  to construct survivorship-free top-N and sector universes.

- [ ] **Crypto ETF flows and holdings.** No stable, free, auditable historical
  source was selected.

- [ ] **CME crypto futures and CFTC positioning.** Useful for institutional
  basis, term structure, and positioning regimes.

- [ ] **Individual stablecoin and chain-level supply.** Aggregate supply is
  present; issuer/chain composition, mint/burn flows, and depeg event metadata
  are not.

- [ ] **Broader cross-exchange prices/funding.** Coinbase/Kraken spot and
  Bybit/OKX/Deribit perpetual data would quantify venue-specific results and
  provide outage redundancy.

- [ ] **News, social, and event data.** No auditable historical news/social
  corpus, protocol calendar, unlock schedule, hack database, or regulatory
  event set was acquired.

- [ ] **Global macro.** ECB/BoJ policy, global yields, China liquidity, FX
  crosses, commodities beyond oil/gold, and global equity indexes remain to be
  added if a paper needs them.

## Rebuild and backtest entry points

```bash
# Full refresh. Raw downloads are cached; Hyperliquid resumes page by page.
freqtrade/.venv/bin/python market_data/build_dataset.py --groups all

# Fast deterministic rebuild using the existing Hyperliquid cache.
freqtrade/.venv/bin/python market_data/build_dataset.py \
  --groups all --hyperliquid-local-only

# Confirm that Freqtrade sees the generated spot data.
freqtrade/.venv/bin/freqtrade list-data \
  --exchange binance \
  --data-dir data/market/freqtrade/binance \
  --data-format-ohlcv parquet \
  --show-timerange
```

For every paper result, copy or reference `data/market/manifest.json`. That pins
the exact dataset hashes and prevents a later refresh from silently changing a
reported backtest.
