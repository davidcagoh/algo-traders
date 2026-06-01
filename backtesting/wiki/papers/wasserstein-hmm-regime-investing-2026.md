# Explainable Regime Aware Investing

**Authors:** (see arXiv:2603.04441 for full author list)
**Venue/Source:** arXiv q-fin
**arXiv/DOI:** https://arxiv.org/abs/2603.04441
**Date:** March 2026

---

## Core Claim
A strictly causal Wasserstein Hidden Markov Model (W-HMM) that allows the number of regimes to adapt dynamically — while preserving stable economic interpretation via Wasserstein-distance template matching — yields materially better risk-adjusted returns than equal-weight and SPX benchmarks when its regime probabilities are embedded in a transaction-cost-aware mean-variance optimiser.

---

## Method
- **Inference:** Rolling Gaussian HMM estimated by Expectation-Maximisation on daily returns. Model order (number of regimes) is selected at each step by a predictive BIC-like criterion, so the model can shrink from 4 regimes to 2 and back.
- **Identity tracking:** At each roll, Gaussian components are matched to their nearest predecessor by the 2-Wasserstein distance between Gaussian distributions, preserving the economic labels (bull / bear / vol-spike) across re-estimations. This is the key contribution — previous rolling-HMM approaches suffered from label switching.
- **Portfolio construction:** Regime posterior probabilities are soft-weighted inputs to a mean-variance optimiser with explicit transaction-cost penalty (quadratic in turnover), applied to a diversified daily cross-asset universe.

---

## Results
| Metric | W-HMM | Equal-Weight | SPX Buy-and-Hold |
|--------|------:|-------------:|-----------------:|
| Sharpe | 2.18 | 1.59 | 1.18 |
| Max Drawdown | −5.43% | ~−11% | −14.62% |

Calmar not directly reported but computable: if CAGR ≈ 12% (implied by Sharpe 2.18 on a diversified multi-asset book at typical vol ~5–8%), Calmar ≈ 2.2. The low MDD is the headline result — the regime filter materially cuts drawdowns versus passive.

Sample: Diversified daily cross-asset universe (exact assets not retrieved). Not crypto-only.

---

## Relevance to this project
The Wasserstein identity-tracking technique solves the label-switching problem that plagues rolling HMMs in crypto — the one reason rolling HMMs are dismissed as impractical in continuous 24/7 markets where weekend closes don't anchor re-estimations. Concretely:

1. **Drop-in improvement over TrendFilter200:** Instead of a fixed SMA200 cross-up rule (which whipsawed in a sustained bear), use a 2-state Gaussian HMM on 1h returns. When the posterior P(bull state) > 0.6 → enter; otherwise flat. The Wasserstein tracker keeps the state labels consistent across daily re-fits.

2. **Crypto adaptation note:** The paper uses daily data on a cross-asset universe, so the 24/7 no-weekends issue doesn't arise explicitly. However, since we sample at 1h and fit on rolling windows, there are no overnight gaps to worry about — the continuous-time concern (Priority 2) applies more to intraday calendars. The W-HMM framework ports cleanly to 1h crypto data.

3. **Code sketch:**
```python
from hmmlearn.hmm import GaussianHMM
import numpy as np

# On each candle close (or every 24 candles), re-fit a 2-state HMM
returns = df['close'].pct_change().dropna().values[-500:]
model = GaussianHMM(n_components=2, covariance_type='full', n_iter=100)
model.fit(returns.reshape(-1, 1))
# Map state with lower mean return → bear, higher → bull
# Use Wasserstein distance to stable-match labels across re-fits
posterior = model.predict_proba(returns.reshape(-1, 1))
bull_state = np.argmax([m[0] for m in model.means_])
df['hmm_bull_prob'] = posterior[:, bull_state]
# Enter long when hmm_bull_prob > 0.6
```

**Addresses priority:** Priority 2 — Regime detection for 24/7 markets.

---

## Concepts
→ [[hidden-markov-model]] | [[Wasserstein-distance]] | [[regime-detection]] | [[mean-variance-optimisation]] | [[label-switching]]
