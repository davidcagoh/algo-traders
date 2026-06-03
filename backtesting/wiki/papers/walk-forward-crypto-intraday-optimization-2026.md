# A Novel Approach to Trading Strategy Parameter Optimization Using Double Out-of-Sample Data and Walk-Forward Techniques

**Authors:** Anonymous (GitHub: tmr-crypto)
**Venue/Source:** arXiv q-fin
**arXiv/DOI:** arXiv:2602.10785
**Date:** February 18, 2026

---

## Core Claim

Walk-forward window length is a critical but under-optimized hyperparameter for intraday crypto strategies. Counterintuitively, the highest Robust Sharpe Ratios are achieved with **long training + long testing windows** (Quadrant 4), not with short windows that update more frequently. Parameters trained on Bitcoin transfer across assets (Ethereum, Binance Coin) without re-tuning.

---

## Method

Tests EMA crossover on Bitcoin, Ethereum, and Binance Coin at six intraday frequencies (1-min, 5-min, 15-min, 30-min, 45-min, 60-min). Walk-forward process parameterizes both training-window length and testing-window length (81 combinations: 1-day to 28-day each). Optimization metric: Robust Sharpe Ratio (Sharpe winsorized at 5th/95th percentile to reduce outlier sensitivity). Double out-of-sample design: walk-forward window lengths are optimized on a 19-month global training period, then the two best parameter sets are applied without refitting to a 21-month hold-out. Cross-asset transfer tested by applying Bitcoin-derived parameters directly to ETH and BNB.

---

## Results

- **Quadrant 4 (long training, long testing) achieves highest Robust Sharpe.** This is counterintuitive: infrequently retrained strategies outperform frequently retrained ones on these crypto datasets.
- EMA + walk-forward reduces volatility and MDD relative to buy-and-hold.
- Bitcoin-derived parameters generalise to Ethereum and Binance Coin, suggesting regime structure is correlated across majors (consistent with our BTC-dominant HMM finding: see wiki leaderboard footnote 4).
- No Calmar ratio reported; Robust Sharpe is the primary metric.
- 60-min (1h) frequency included in study; the 60-min bucket is within the tested range.

Training: Nov 2022 – Jun 2024 (~19 months). Test: Jul 2024 – Mar 2026 (~21 months).

Code: https://github.com/tmr-crypto/wf_optim_crypto_analysis

---

## Relevance to this project

**Actionable idea 1 — Refit cadence for HmmSmaSlopeV2.** Our candidate walk-forward HMM (R∧T2 family) needs a refit schedule. The paper's counterintuitive Quadrant 4 finding suggests: do NOT refit the HMM every 30 bars. Instead, use a long lookback window (e.g. 500h training, 168h out-of-sample test per walk-forward cycle) and accept that infrequent retraining is better-calibrated for crypto regimes. This directly addresses the open question in wiki/learnings.md H5 (item 1: rolling HMM refit cadence).

**Actionable idea 2 — Validate refit on 1h frequency specifically.** The paper tests 1h (60-min) as the longest timeframe, which matches our R∧T2 4h candidate. If their Quadrant 4 insight holds at 4h (requires even longer windows), the HmmSmaSlopeV2 walk-forward window should be calibrated at roughly 1000-2000 4h bars for training (4–8 months) with a 3–4 week out-of-sample window.

**Actionable idea 3 — Cross-asset parameter transfer.** Bitcoin-derived walk-forward parameters generalise to ETH and BNB without re-tuning. Suggests our 5-coin HmmSmaSlopeV2 might not need per-coin HMM hyperparameter sweeps — BTC-calibrated HMM transitions may transfer to ETH/SOL/AVAX/DOGE.

**Addresses priority:** P2 — Walk-forward refit cadence for regime-detection strategies on crypto intraday. Quantifies the Quadrant 4 effect that directly informs how we schedule HmmSmaSlopeV2 rolling refits.

---

## Concepts
→ [[walk-forward-optimization]] | [[regime-refit-cadence]] | [[robust-sharpe]] | [[cross-asset-transfer]] | [[EMA-crossover]]
