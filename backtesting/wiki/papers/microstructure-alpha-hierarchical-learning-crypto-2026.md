# Microstructure Alpha: Hierarchical Learning and Cross-Asset Transfer in Cryptocurrency Markets

**Authors:** Not identified in available sources
**Venue/Source:** Frontiers in Blockchain (peer-reviewed open-access)
**arXiv/DOI:** https://doi.org/10.3389/fbloc.2026.1811716
**Date:** 2026 (published May 2026 based on DOI)

---

## Core Claim
Classical microstructure features — including OFI, spread proxies, and realized volatility — are stably predictive at minute granularity on Binance perpetual futures, but once data leakage is properly controlled, gradient-boosted models overfit severely and **no strategy survives realistic exchange fees** at minute frequency. Models trained on one cryptocurrency do not transfer to another; however, models transfer well between the spot and futures venues of the same asset.

---

## Method
**Data**: 3+ million minute-level observations from 6 major cryptocurrencies (specific tickers not surfaced in abstract) on Binance spot markets AND Binance perpetual futures — paired same-asset, giving a natural spot→futures transfer experiment.

**Features tested** (9 microstructure measures):
- Order Flow Imbalance (OFI) at multiple LOB levels
- Range-based spread proxies (high–low / OHLC spread estimators)
- Realized volatility (various windows)
- Bid-ask spread proxies
- Depth imbalance at top-of-book

**Models**: gradient boosting (XGBoost/LightGBM) with SHAP feature attribution, wrapped in a hierarchical learning pipeline (asset-level models aggregated by meta-learner), stability selection to identify robustly useful features.

**Evaluation protocol**: purged walk-forward cross-validation (no leakage of future bar OFI into past feature windows), benchmarked against naive (always-long) forecasters. Fee levels tested: Binance maker 0.01% and taker 0.04% per side.

---

## Results
- **Feature stability**: All 9 features are stably selected at minute granularity. Range-based spread proxies and realized volatility are the most consistent (appear in all 6 coins × both venues). OFI is selected but with lower stability than spread/vol.
- **Predictive signal exists**: Before leakage controls and fees, models show detectable short-term return predictability at minute level.
- **After leakage control**: Gradient-boosted models overfit severely — OOS R² collapses when the same purged CV used for training is applied consistently. The signal is genuine but weaker than it appears in naive backtest setups.
- **After fees**: No strategy survives Binance taker fees (0.04%/side) at minute frequency. Even maker-only strategies (0.01%/side) do not produce consistent net-positive returns.
- **Cross-asset transfer**: Models trained on BTC **do not transfer** to ETH, SOL, etc. Feature importance rankings differ substantially across assets.
- **Spot→futures transfer**: Models trained on Binance BTC spot **do transfer** to Binance BTC perpetual futures (same-asset, different venue). Feature rankings are preserved and predictive power is maintained.

---

## Relevance to this project
This is the most directly relevant paper for our P4 open question (does microstructure OFI survive at 1h aggregation?). The negative result at minute level is the key input:

1. **Minute-level OFI is killed by fees**: At Binance taker 0.04%/side, no strategy works at 1-minute bars. Our Hyperliquid taker is 0.035%/side — nearly identical. This means we cannot build a minute-level OFI strategy; **1h aggregation is the natural next step** to test, not to abandon.

2. **Range spread + realized vol are the most stable features**: For our mean-reversion strategy design, these are better OFI proxies than raw LOB-depth imbalance. Specifically, a high realized-vol bar at 1h suggests elevated temporary OFI pressure that may revert — this aligns with our hypothesis that the OFI concavity-at-extremes (from arXiv 2602.00776, already indexed) creates a mean-reversion opportunity at 70th–90th percentile.

3. **Spot→futures transfer is valid**: For Hyperliquid, which lacks rich tick data, this result justifies using Binance BTC spot OFI (hourly-aggregated) as a proxy signal for Hyperliquid BTC perp entry. We already download Binance candle data; adding hourly NBV (net buy volume = volume × (close - open) / (high - low)) requires no new data source.

4. **Cross-asset failure warns against 5-coin homogeneous OFI strategy**: Don't use BTC hourly OFI as a signal for SOL or DOGE. Build per-coin OFI features or drop OFI entirely for alts.

```python
# Hourly net-buy-volume proxy (no tick data needed — OHLCV only)
# From arXiv 2602.00776 (Bieganowski): moderate OFI (70th-90th pct) is the entry zone
def ofi_proxy_from_ohlcv(df):
    """Range-based NBV proxy — Binance spot candles as signal for Hyperliquid perp entry."""
    body_frac = (df['close'] - df['open']) / (df['high'] - df['low'] + 1e-9)
    nbv = df['volume'] * body_frac.clip(-1, 1)  # net buy volume in [-vol, +vol]
    nbv_z = (nbv - nbv.rolling(168).mean()) / nbv.rolling(168).std()
    return nbv_z  # entry at 1.5 < nbv_z < 3.0 (moderate OFI zone, avoids extremes)
```

**Key implication for P4 priority update**: The question is no longer "does OFI exist as a signal?" (it does) but "does it survive hourly aggregation AND our fee level (0.035%/side)?" This paper narrows the lower bound: minute-level doesn't. A single paper testing hourly-aggregated OFI on Binance perp with fee accounting would close P4.

**Addresses priority:** P4 (OFI-based mean-reversion at 1h–4h in crypto perps — negative result at minute level is the missing boundary condition for our hourly investigation).

---

## Concepts
→ [[order flow imbalance]] | [[microstructure]] | [[leakage control]] | [[cross-asset transfer]] | [[spot-futures transfer]] | [[Binance perp futures]] | [[range spread]] | [[realized volatility]]
