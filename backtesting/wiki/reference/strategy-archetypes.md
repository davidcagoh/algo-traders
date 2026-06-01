# Strategy Archetypes Reference

<!-- Source: derived from IMC Prosperity podium writeups (P1 2023, P2 2024, P3 2025), generalised for equities and crypto spot -->

**Annotation convention:** `Backtester notes` sections contain one-line pointers to `wiki/results/*.md` or `wiki/learnings.md` where findings live. Do not restate findings inline — that creates a second source of truth. If a backtest result is relevant to an archetype, add: `> See wiki/results/<date>-<strategy>.md — <one-sentence summary>.`

**Scope note:** This taxonomy is HFT/prop-desk in origin. Archetypes #1 (market making), #2 (regression MM), #5 (options), and #6 (order flow) require tick-level or L2 data we don't have in this setup (OHLCV-only, 1h/4h). Archetypes #3 (stat arb / ETF spread), #4 (mean reversion), and #7 (cross-exchange) are applicable at our timeframes and are annotated with current findings.

**Relation to learnings.md:** `wiki/learnings.md` records what we've confirmed/ruled-out/hypothesised from actual runs. This file records how each archetype works in principle. They answer different questions and should stay separated.

---

## Document structure

Each strategy is specified with a consistent schema:

- **Archetype** — canonical name and category
- **Applicable assets** — what real-world instruments this maps to
- **Core idea** — one-paragraph intuition
- **Fair value model** — how to estimate the "true" price
- **Signal logic** — entry condition
- **Exit / inventory rule** — when and how to unwind
- **Position sizing** — how large to trade
- **Key parameters** — tunable variables for backtester search
- **Known failure modes** — when this strategy breaks
- **Friction adjustments** — what must be added for real-world use
- **Backtester notes** — one-line pointers to results files where findings live

---

## 1. Pure market making

**Category:** Microstructure

**Applicable assets:** Crypto spot (BTC/USDT, ETH/USDT on CEXes with maker rebates), liquid equities with direct market access

**Core idea:**
Post limit orders on both sides of the book inside the current bid-ask spread, collecting the spread as profit. Manage inventory to stay roughly flat. Take aggressively when the market price deviates significantly from your fair value estimate.

**Fair value model:**
```
fair_value = WallMid
           = (best_bid_with_large_size + best_ask_with_large_size) / 2

# WallMid: identify the dominant passive liquidity provider's quotes.
# Their mid is a better fair value estimate than the raw top-of-book mid,
# which is noisy from small retail orders.
# Alternative: volume-weighted mid (VWAP of top N levels).
```

**Signal logic:**
```
# Take (aggressive):
if best_bid > fair_value + take_edge:
    sell market
if best_ask < fair_value - take_edge:
    buy market

# Make (passive):
post_bid = fair_value - make_spread
post_ask = fair_value + make_spread

# Inventory skew (shift quotes to reduce position):
skew = inventory / position_limit * skew_factor
post_bid -= skew
post_ask -= skew
```

**Exit / inventory rule:**
```
# Soft limit: skew quotes more aggressively as |inventory| grows
# Hard limit: if |inventory| > hard_limit, take aggressively at unfavourable price to flatten
if abs(inventory) >= hard_limit:
    flatten at market (accept crossing spread)
```

**Position sizing:**
Scale order size with available spread. In thin markets, reduce size.
```
order_size = base_size * (spread / min_viable_spread)
order_size = min(order_size, position_limit - abs(inventory))
```

**Key parameters:**
| Parameter | Description | Suggested search range |
|---|---|---|
| `make_spread` | Half-spread for passive quotes | 0.5–5 ticks |
| `take_edge` | Minimum mispricing to take aggressively | 1–3 ticks |
| `skew_factor` | Inventory skew aggressiveness | 0.1–1.0 |
| `hard_limit` | Inventory level triggering forced unwind | 50–100% of position limit |
| `base_size` | Default order quantity | Asset-dependent |

**Known failure modes:**
- **Adverse selection:** informed traders systematically hit your quotes right before a price move. Your fills become systematically bad. Monitor: if average fill price is consistently worse than subsequent mid, you are being adversely selected.
- **One-sided inventory buildup:** in trending markets, inventory accumulates on the losing side and skew is insufficient to flatten. Add a trend filter to pause quoting in strong momentum.
- **Spread compression:** if other market makers tighten the spread, your edge disappears. Monitor spread distribution over time.
- **Fat-finger / wash trades:** in crypto, occasional erroneous large prints can trigger aggressive takes incorrectly. Add a price sanity filter.

**Friction adjustments for real-world use:**
- Add exchange fees (maker rebate or taker fee depending on order type)
- Model latency: assume your cancel/replace is N milliseconds behind the market; stale quotes get picked off
- For equities: add short-sale availability check before posting ask below fair value
- For crypto: account for withdrawal/funding friction if arbitraging across exchanges

**Backtester notes:**
> Not applicable at current data resolution (OHLCV 1h/4h). Requires L2 order book data and sub-second execution.

---

## 2. Regression-based fair value + market making

**Category:** Microstructure / Statistical

**Applicable assets:** Crypto spot pairs with correlated assets, equities with sector ETF relationship

**Core idea:**
When an asset's price is predictable via a short-horizon regression (e.g. lagged values, correlated asset returns), use the regression output as fair value rather than the raw mid. Quote and take around this estimate. Works best for mean-reverting or slowly drifting assets.

**Fair value model:**
```
# Linear regression on recent mid prices (autoregressive):
fair_value_t = β0 + β1 * mid_{t-1} + β2 * mid_{t-2} + ... + βk * mid_{t-k}

# Or with correlated asset:
fair_value_t = α + β * correlated_asset_price_t + ε

# Fit coefficients on rolling window of recent data (avoid lookahead).
# Validate: R² on out-of-sample window should be meaningful (>0.5 to be useful).
# Coefficients should be re-estimated periodically (daily or weekly in live trading).
```

**Signal logic:**
```
predicted = regress(recent_prices, window=regression_window)
error = mid_t - predicted

# Take if mispriced:
if error > take_threshold:
    sell (price expected to revert down)
if error < -take_threshold:
    buy (price expected to revert up)

# Make: quote around predicted fair value, same as archetype 1
```

**Exit / inventory rule:**
```
# Exit when error reverts to zero (price returns to regression estimate)
# Or time-based: exit after max_holding_period bars regardless
```

**Position sizing:**
```
size = base_size * (abs(error) / take_threshold)
size = min(size, position_limit)
```

**Key parameters:**
| Parameter | Description | Suggested search range |
|---|---|---|
| `regression_window` | Lookback bars for fitting | 5–50 bars |
| `take_threshold` | Error size triggering aggressive take | 0.5–3 σ of residuals |
| `max_holding_period` | Max bars to hold before forced exit | 5–20 bars |
| `refit_frequency` | How often to refit coefficients | Daily / weekly |

**Known failure modes:**
- **Overfitting:** short regression windows on short histories overfit to noise. Validate out-of-sample rigorously.
- **Regime change:** coefficients fitted in a low-volatility regime fail in high-volatility periods. Add a regime filter (e.g. VIX level, rolling volatility percentile).
- **Spurious correlation:** the IMC trick of using prior-year data worked because IMC reused generators. This does not generalise. Do not mine cross-year correlations without strong structural justification.
- **Non-stationarity:** mid prices are typically I(1) (unit root). Regress on *returns*, not levels, unless you have confirmed cointegration.

**Friction adjustments:**
- Regression fit must use only data available at trade time (no lookahead)
- In equities: be aware of overnight gaps resetting intraday regression
- Transaction costs shrink the profitable error band significantly — test net of fees

**Backtester notes:**
> Not applicable at current data resolution (OHLCV 1h/4h). Requires tick-level or at minimum 1m data for signal quality. Possible future application: ETH/BTC or SOL/BTC cointegration at 1h using the regression variant — not yet explored.

---

## 3. Statistical arbitrage — basket / ETF spread

**Category:** Statistical Arbitrage

**Applicable assets:**
- Equities: ETF vs underlying basket (e.g. SPY vs SPX components, sector ETFs vs holdings)
- Crypto: index products vs constituents, funding-rate neutral perp vs spot (use spot version for this system)
- Any pair or basket with stable long-run spread (cointegrated)

**Core idea:**
Two assets that are economically linked (ETF and its NAV, or two cointegrated instruments) will have a spread that mean-reverts. Trade the spread: buy the cheap leg, sell the rich leg, unwind when the spread converges.

**Fair value model:**
```
# Pair case:
spread_t = price_A_t - β * price_B_t

# Basket case (ETF):
fair_value_ETF = Σ (weight_i * price_i)  # theoretical NAV
spread_t = ETF_price_t - fair_value_ETF_t

# Estimate β via OLS on cointegrated pair (Engle-Granger or Johansen test first).
# Re-estimate β periodically. Confirm cointegration before trading.
```

**Signal logic:**
```
mu = rolling_mean(spread, window=zscore_window)
sigma = rolling_std(spread, window=zscore_window)
z = (spread_t - mu) / sigma

if z > entry_z:
    sell A, buy B  (spread too wide, expect reversion)
if z < -entry_z:
    buy A, sell B  (spread too narrow, expect reversion)
if abs(z) < exit_z:
    close position  (spread has reverted)
```

**Exit / inventory rule:**
```
# Primary: z-score reverts inside exit_z
# Secondary (stop-loss): if z exceeds stop_z (spread widens further), cut loss
# Tertiary: time-based exit after max_holding_period
```

**Position sizing:**
```
# Dollar-neutral: size both legs to equal dollar exposure
size_A = capital_per_trade / price_A
size_B = size_A * β * price_A / price_B  # adjust for β

# Or volatility-scaled: size so each leg has equal vol contribution
```

**Key parameters:**
| Parameter | Description | Suggested search range |
|---|---|---|
| `zscore_window` | Rolling window for mean/std of spread | 20–120 bars |
| `entry_z` | Z-score threshold to enter | 1.5–3.0 |
| `exit_z` | Z-score threshold to exit | 0.0–0.5 |
| `stop_z` | Z-score stop-loss | 3.0–5.0 |
| `max_holding_period` | Max bars held | 20–100 bars |
| `beta_window` | Window for estimating hedge ratio β | 60–250 bars |

**Known failure modes:**
- **Cointegration breakdown:** the long-run relationship dissolves (ETF changes composition, company merger, macro regime shift). Always test cointegration before entering and monitor the spread's half-life.
- **Execution slippage on both legs:** entering two legs simultaneously is harder than it looks. In crypto on CEX this is manageable; in equities with market orders, one leg can move against you before the second fills.
- **Beta drift:** β estimated on historical data may not match the current ratio, causing a systematically biased hedge. Re-estimate frequently.
- **Crowded trade:** many participants running the same spread means mean reversion is faster and the edge thins.

**Friction adjustments:**
- Both legs incur fees — net spread must exceed 2× round-trip cost to be viable
- In equities: borrowing cost for the short leg (short-sale fee) must be included
- For ETF arbitrage in equities: creation/redemption mechanism means large players can arbitrage to zero; retail edge is limited to intraday micro-dislocations

**Backtester notes:**
> Funding-rate carry is the closest applicable variant for this setup: perp funding rate = implicit spread between the perpetual and a synthetic spot position. See `wiki/learnings.md` H4 (open hypothesis) for the current state — DEX carry on Drift has empirical Sharpe 23.55 (Zhivkov 2025), but ~60% of apparent edge is eaten by costs at threshold <20 bps. Hyperliquid-specific threshold and fee structure not yet empirically tested; funding-rate data collector not yet built. ETH/BTC or SOL/BTC cointegration spread is a separate untested variant at this setup's 1h/4h resolution.

---

## 4. Mean reversion on volatility spikes

**Category:** Statistical / Mean Reversion

**Applicable assets:** Crypto spot (high-volatility pairs: SOL, DOGE, meme coins), small/mid-cap equities

**Core idea:**
Highly volatile assets occasionally spike sharply in one direction with no fundamental driver. These spikes tend to revert. Trade against the spike, sizing proportionally to its magnitude.

**Fair value model:**
```
# Rolling mean and standard deviation of mid price returns:
mu_r = rolling_mean(returns, window=vol_window)
sigma_r = rolling_std(returns, window=vol_window)

# Z-score of current return:
z_t = (return_t - mu_r) / sigma_r
```

**Signal logic:**
```
if z_t > spike_threshold:
    sell  (price spiked up, expect reversion)
if z_t < -spike_threshold:
    buy   (price spiked down, expect reversion)
```

**Exit / inventory rule:**
```
# Exit when price returns to pre-spike level (or rolling mean)
# Hard stop-loss: if price continues in spike direction by stop_multiple * sigma, cut
target_exit = entry_price - sign(trade) * revert_fraction * abs(spike_size)
stop_price  = entry_price + sign(trade) * stop_multiple * sigma_r
```

**Position sizing:**
```
# Scale with spike magnitude — larger spike = more confident reversion
size = base_size * min(abs(z_t) / spike_threshold, max_size_multiple)
```

**Key parameters:**
| Parameter | Description | Suggested search range |
|---|---|---|
| `vol_window` | Rolling window for σ estimation | 10–50 bars |
| `spike_threshold` | Z-score triggering entry | 2.0–4.0 |
| `revert_fraction` | Fraction of spike to target as profit | 0.3–0.8 |
| `stop_multiple` | Stop-loss as multiple of σ beyond entry | 1.0–2.5 |
| `max_size_multiple` | Cap on size scaling | 2–5× |

**Known failure modes:**
- **Momentum continuation:** some spikes are the start of a trend, not noise. Distinguish: check volume profile (spike on no volume = likely noise; spike on high volume = potential fundamental move).
- **Thin liquidity at spike prices:** the best reversion entry is at the spike extreme, but liquidity is worst there. Use limit orders; accept partial fills.
- **Fat tails in crypto:** crypto distributions have much fatter tails than equities. What looks like a 4σ event happens far more often than a Gaussian would predict. Calibrate thresholds empirically from the asset's own history.

**Friction adjustments:**
- High-vol assets have wide spreads at spike moments — include spike-time spread in cost model
- For equities: short-side spikes may require borrows that are unavailable at the moment of the spike

**Backtester notes:**
> Open hypothesis in `wiki/learnings.md` H4. SOL/USDC:USDC and ETH/USDC:USDC data are available (1h and 4h Feather files exist). Not yet backtested. The weekly paper search has not yet found strong intraday mean-reversion evidence for crypto at 1h–4h; the mechanism (retail overreaction) likely exists but horizon calibration is open. Candidate first test: z-score spike filter on SOL 1h returns, threshold 2.5σ, exit at mean reversion to 0, stop at 1.5σ beyond entry.

---

## 5. Options pricing — implied volatility mispricing

**Category:** Derivatives

**Applicable assets:** Equity options (SPY, single-name), crypto options (Deribit: BTC, ETH)

**Core idea:**
Use Black-Scholes to compute the theoretical fair value of an option given the current underlying price, strike, time-to-expiry, and an estimate of implied volatility. When the market price deviates from the model price, trade the mispricing and delta-hedge the directional exposure to isolate the volatility bet.

**Fair value model:**
```python
from scipy.stats import norm
import numpy as np

def black_scholes(S, K, T, r, sigma, option_type='call'):
    """
    S: underlying price
    K: strike
    T: time to expiry (years)
    r: risk-free rate
    sigma: implied volatility (annualised)
    """
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == 'call':
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

def delta(S, K, T, r, sigma, option_type='call'):
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return norm.cdf(d1) if option_type == 'call' else norm.cdf(d1) - 1

def implied_vol(market_price, S, K, T, r, option_type='call'):
    # Solve for sigma via bisection or Newton-Raphson
    ...
```

**Signal logic:**
```
# Compute IV for each strike from market prices
IV_market = implied_vol(market_price, S, K, T, r)

# Fit the IV surface (smile):
# Plot IV vs moneyness m = log(K/S) / sqrt(T)
# Fit a parabola: IV(m) = a + b*m + c*m²
# The fitted parabola is your "model" IV surface

# Mispricing signal:
IV_model = a + b * moneyness + c * moneyness**2
edge = IV_market - IV_model

if edge > iv_entry_threshold:
    sell option (overpriced vol), delta-hedge with underlying
if edge < -iv_entry_threshold:
    buy option (underpriced vol), delta-hedge with underlying
```

**Delta hedging:**
```
# After entering option position:
delta_exposure = position_size * delta(S, K, T, r, sigma)
hedge_trade = -delta_exposure * S  # buy/sell underlying to offset

# Re-hedge periodically (or when delta drifts by rehedge_threshold):
current_delta = position_size * delta(S_now, K, T_remaining, r, sigma)
if abs(current_delta - last_hedged_delta) > rehedge_threshold:
    adjust underlying position
```

**Exit / inventory rule:**
```
# Exit when IV mispricing reverts (edge closes)
# Or at expiry (option expires, delta hedge unwound)
# Stop-loss: if edge widens further (IV moves more against you), cut at stop_iv_loss
```

**Key parameters:**
| Parameter | Description | Suggested search range |
|---|---|---|
| `iv_entry_threshold` | Min IV edge to enter | 0.5–2 vol points |
| `smile_fit_degree` | Polynomial degree for smile fit | 2 (quadratic) |
| `rehedge_threshold` | Delta change triggering re-hedge | 0.05–0.2 |
| `stop_iv_loss` | IV move stopping out the trade | 2–5 vol points |

**Known failure modes:**
- **Model risk:** Black-Scholes assumes constant vol and log-normal returns — both false. Skew and term structure require extensions (Heston, SABR). Use BS as a first approximation only.
- **Gamma/pin risk near expiry:** as T → 0, delta changes rapidly; hedging becomes expensive and discontinuous. Avoid holding through last trading day unless intentional.
- **Liquidity in options:** individual strikes can be illiquid; bid-ask spreads in options are wide. Slippage eats IV edge quickly.
- **Early exercise (American options):** BS is for European options. American options on dividend-paying stocks may be optimally exercised early; use binomial or finite-difference pricing instead.

**Friction adjustments:**
- Include options bid-ask spread (often 5–20% of premium for OTM options) in cost model
- Include delta-hedge transaction costs for each re-hedge
- Crypto options (Deribit): fees are lower and spreads tighter than equity options for BTC/ETH

**Backtester notes:**
> Out of scope for this setup. Freqtrade does not support options instruments. Would require a separate options data feed (Deribit API) and pricing library. Not planned.

---

## 6. Order flow / informed trader signal

**Category:** Alternative Data / Flow

**Applicable assets:** Equities (13F filings, dark pool prints, institutional flow proxies), crypto (whale wallet tracking, large on-chain transfers)

**Core idea:**
Certain market participants trade with an informational edge and leave detectable footprints. Following their direction — after identifying them as consistently profitable — provides a directional signal. This is the generalisation of the "copy Olivia" strategy from Prosperity.

**Signal construction:**
```
# Equity version — 13F lag strategy:
1. Download 13F filings (quarterly, 45-day lag after quarter end)
2. Identify managers with consistent alpha (information ratio > threshold over N quarters)
3. On filing release, buy their new positions / sell their exits
4. Weight by position size change and manager conviction score

# Crypto version — whale tracking:
1. Monitor large on-chain transfers to/from exchanges
2. Large inflow to exchange → potential sell pressure
3. Large outflow from exchange → potential accumulation (bullish)
4. Weight signal by transfer size relative to daily volume
```

**Signal logic:**
```
# Directional:
if informed_trader_bought:
    go long, size = base_size * signal_strength
if informed_trader_sold:
    go short (or reduce long), size = base_size * signal_strength

signal_strength = trade_size / avg_daily_volume  # normalise by liquidity
```

**Exit / inventory rule:**
```
# Follow until counter-signal from same trader
# Or time-based: position decays linearly over signal_decay_period
# Stop-loss at stop_loss_pct from entry
```

**Key parameters:**
| Parameter | Description | Suggested search range |
|---|---|---|
| `signal_decay_period` | Bars over which signal fades | 1–20 days |
| `min_trader_track_record` | Quarters of consistent alpha required | 4–12 |
| `signal_strength_threshold` | Min normalised trade size to act on | 0.1–0.5% of ADV |
| `stop_loss_pct` | Stop-loss from entry | 1–3% |

**Known failure modes:**
- **Signal crowding:** once a manager's 13F is public, many quant funds trade the same signal. Alpha decays quickly, especially for large-cap stocks.
- **Stale data:** 13F lag (up to 45 days) means the manager may have already exited by the time you see the filing.
- **Crypto whale manipulation:** large wallets sometimes make transfers to create a false signal and trade against followers. Distinguish organic accumulation from manufactured signals.
- **Legality boundary:** trading on *material non-public information* is illegal. 13F and on-chain data are public. Never act on information obtained through non-public channels.

**Friction adjustments:**
- For equities: 13F-based strategies have shrinking edge due to crowding; combine with other signals
- For crypto: on-chain data is real-time but noisy; apply smoothing and volume filters

**Backtester notes:**
> Not directly applicable at OHLCV resolution. The on-chain variant is theoretically applicable via Hyperliquid's public API (large liquidation events, open-interest spikes as flow proxies), but this would require streaming data infrastructure not currently in scope. Flag for later if the regime-filter family underperforms.

---

## 7. Cross-exchange / location arbitrage

**Category:** Arbitrage

**Applicable assets:** Crypto spot (same asset on multiple CEXes or CEX vs DEX), equities cross-listed on multiple exchanges (less accessible at retail)

**Core idea:**
The same asset trades at slightly different prices on different venues. Buy the cheaper venue, sell the dearer venue simultaneously, locking in a risk-free spread net of transfer/transaction costs.

**Fair value model:**
```
# Price discrepancy:
spread = price_venue_A - price_venue_B

# Net of costs:
net_spread = spread - fee_A - fee_B - transfer_cost - slippage_estimate

# Only trade if net_spread > min_edge
```

**Signal logic:**
```
if net_spread > min_edge:
    buy at venue_B (cheaper), sell at venue_A (dearer)
    # Execute as simultaneously as possible to avoid leg risk
```

**Exit / inventory rule:**
```
# Position is closed when transfer completes and both legs are settled
# Leg risk: if one leg fills and the other moves before you can fill,
# you are exposed. Set a stop on the unfilled leg.
```

**Key parameters:**
| Parameter | Description | Suggested search range |
|---|---|---|
| `min_edge` | Net spread required to trade | 0.05–0.2% |
| `max_transfer_time` | Max acceptable settlement delay | Asset/exchange dependent |
| `max_leg_size` | Order size per arb attempt | Liquidity-constrained |

**Known failure modes:**
- **Transfer time risk:** crypto transfers take minutes to hours. Price can converge before transfer settles, eliminating the profit. Use exchanges where you pre-fund both sides.
- **Simultaneous execution:** true simultaneity is impossible at retail. Use limit orders on both sides with a tight timeout.
- **Fee structure changes:** exchange fee tiers change; recalculate net edge regularly.
- **Withdrawal limits:** exchanges impose daily withdrawal limits that cap your arb capacity.

**Friction adjustments:**
- Pre-fund both venue accounts to avoid transfer delays (removes transfer time risk at the cost of tied-up capital)
- Include network gas fees for DEX-side legs
- For equities cross-listed arb: requires DMA on both markets; not accessible at retail in most jurisdictions

**Backtester notes:**
> Closest applicable variant: CEX→Hyperliquid funding-rate lead-lag (H6 in `wiki/learnings.md`). Zhivkov (2026) shows Granger causality runs CEX→DEX for funding rates, lag measured in minutes. At 1h data this lag may be collapsed. Requires Binance funding-rate data at 15m or 5m to test; not yet implemented. See `wiki/learnings.md` H6 for current state.

---

## Meta: failure modes common to all strategies

These apply universally and should be modelled explicitly in the backtester:

| Failure mode | Description | Mitigation | Project status |
|---|---|---|---|
| **Overfitting** | Parameters tuned to historical noise | Walk-forward validation; out-of-sample testing | Open — no walk-forward yet |
| **Transaction cost blindness** | Ignoring fees, spread, and slippage | Model fees explicitly; use conservative slippage estimates | **Active gap** — zero fees in all runs; see `wiki/learnings.md` Scoring section |
| **Lookahead bias** | Using future data in signal computation | Strict timestamp discipline in backtester | Managed by `startup_candle_count` in all strategies |
| **Survivorship bias** | Backtesting only assets that still exist | Include delisted assets in equity universe | Not applicable (single-asset perp on live exchange) |
| **Regime change** | Strategy trained in one vol/trend regime fails in another | Test across multiple historical regimes | Addressed by H7 requirement — see `wiki/learnings.md` H5 |
| **Capacity constraints** | Strategy is profitable at small size but not at scale | Test with realistic order sizes; model market impact | Deferred — single-asset, small size |
| **Correlation in live markets** | Multiple strategies with hidden shared risk factor | Monitor pairwise strategy correlation; cap shared exposure | Deferred — single strategy in live use |

---

## Suggested annotation protocol (adapted for this project)

1. **On first ingest (done 2026-04-30):** file moved to `wiki/reference/`, linked from `wiki/_index.md`. Backtester notes sections for #3, #4, #7 annotated with current project state.
2. **After each backtest:** if the result is relevant to an archetype, add a one-line pointer to the relevant `wiki/results/*.md` file in that archetype's Backtester notes. Do not restate metrics — they live in the results file.
3. **New archetypes:** when a new strategy type is identified from research, add it in the same schema format.
4. **Do not duplicate:** findings live in `wiki/results/` and `wiki/learnings.md`. This file stays as a stable reference.

---
*Generated from IMC Prosperity P1–P3 podium writeups. Generalised for equities and crypto spot. Not financial advice.*
