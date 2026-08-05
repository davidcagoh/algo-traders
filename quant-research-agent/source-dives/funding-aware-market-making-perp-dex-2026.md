# Funding-Aware Optimal Market Making for Perpetual DEXs

**Authors:** Nam Anh Le (National Economics University, Vietnam)
**Venue/Source:** arXiv q-fin
**arXiv/DOI:** arXiv 2605.06405
**Date:** May 7, 2026

---

## Core Claim

Classical Avellaneda–Stoikov market-making ignores funding-rate cash flows, causing liquidity providers to systematically mis-size inventory around funding payment windows. Adding an OU funding-rate state variable to the HJB control problem reduces inventory RMS and improves PnL for ETH and BTC perpetuals on Hyperliquid.

---

## Method

Funding rate is modelled as an Ornstein-Uhlenbeck process (Gaussian OU baseline) with optional jump augmentation for heavy-tailed innovations. The joint inventory–funding HJB quasi-variational inequality is solved via a monotone finite-difference scheme. Bid/ask quote offsets are recovered from discrete inventory value differences. Calibration is done on **Hyperliquid ETH, BTC, and SOL perpetual data**; cross-venue check uses Binance ETHUSDT, November 4 2025 – May 3 2026.

Key calibrated parameter: **OU half-life ≈ 7.96 hours** (Binance ETHUSDT; Hyperliquid values are also fitted but not reported in secondary sources).

OU-plus-jump diagnostics confirm heavy-tailed funding innovations — spikes occur and revert faster than the baseline OU predicts.

---

## Results

100-seed holdout simulations under two official-fill proxy calibrations:
- Funding-aware HJB **improves mean ETH/BTC PnL** vs. classical Avellaneda–Stoikov.
- **Lowers inventory RMS** relative to the classical baseline.
- SOL gains are positive vs. unscaled AS but not a Pareto improvement once risk-scaled AS is included.

No Calmar or Sharpe ratios are reported (market-making PnL, not a directional strategy). The contribution is the calibrated OU dynamics, not a carry strategy backtest.

---

## Relevance to this project

This paper is not about directional carry trading, but its **Hyperliquid-specific funding calibration** fills a concrete gap in our carry strategy design:

**1. Carry window duration.** The OU half-life of ~8h (on a liquid perp — Hyperliquid should be similar) means that once funding is elevated, it decays to its mean in roughly one day. Implication for the Freqtrade carry strategy:
- At 4h candles: a carry position entered at bar 0 should be **exited at bar 2–4** (8–16h), not held indefinitely.
- Time-exit: add `minimal_roi = {"0": 0.005, "8": 0.003, "16": 0}` style forced-exit config, or a `hold_bars ≤ 4` sell signal.

**2. Spike-exclusion filter.** The jump component (heavy tails) means that extreme funding spikes (>3σ above OU mean) revert *faster* than the OU model predicts and carry more adverse-selection risk. Implication:
- Do NOT enter carry when funding rate is a multi-standard-deviation outlier (spike). These are the events most likely to reverse within the first 8h.
- Add filter: `entry_rate < OU_mean + 2 * OU_sigma` (only enter in "persistent high" regime, not spike regime).

**3. Carry signal construction.** The OU steady-state mean (long-run average funding) is the right threshold reference, not an absolute rate. If OU mean is near zero (low-volatility regime), a 20-bps current rate is still a meaningful carry; if OU mean is 15 bps, a 20-bps rate provides almost no edge.

**Code sketch for carry timer (Freqtrade sell signal):**
```python
# In populate_exit_trend — exit after 4h bars if funding has normalised
entry_bar = dataframe['entry_bar'].fillna(0)
current_bar = dataframe.index
hold_duration = current_bar - entry_bar
dataframe.loc[hold_duration >= 4, 'exit_long'] = 1  # approx 2x OU half-life
```

**Dependency:** requires the OU parameter (θ, μ, σ) to be calibrated on Hyperliquid BTC data specifically — the paper fits ETH/BTC/SOL on Hyperliquid but doesn't publish the numeric values in accessible sources. Estimate via scipy.optimize fitting `ou_fit()` on the existing funding parquet file.

**Addresses priority:** P1 — Funding-rate carry on DEX perps: Hyperliquid-specific threshold. Specifically, quantifies the carry window duration (OU half-life ~8h → 2 bars at 4h) and identifies the spike-exclusion condition.

---

## Concepts
→ [[funding-rate-carry]] | [[Ornstein-Uhlenbeck]] | [[Hyperliquid-perps]] | [[carry-window-timing]] | [[market-making]]
