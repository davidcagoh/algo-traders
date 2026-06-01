# Markov and Hidden Markov Models for Regime Detection in Cryptocurrency Markets: Evidence from Bitcoin (2024–2026)

**Authors:** Not retrieved (Preprints.org access restricted)
**Venue/Source:** Preprints.org (preprint, not yet peer-reviewed)
**arXiv/DOI:** https://www.preprints.org/manuscript/202603.0831
**Date:** March 11, 2026

---

## Core Claim
Non-homogeneous Hidden Markov Models (NH-HMMs) with Bayesian estimation outperform standard homogeneous HMMs at identifying latent regime transitions in Bitcoin price data over 2024–2026, and a four-state model achieves the best one-step-ahead forecasting performance, distinguishing bull, bear, and calm regimes.

---

## Method
- Standard homogeneous HMM baseline (Gaussian emissions on daily returns).
- Non-homogeneous extension: transition probabilities are allowed to vary over time as a function of covariates (trading volume, social-media sentiment, global macro indices, on-chain metrics).
- Bayesian estimation (MCMC): provides posterior distributions over regime labels and transition matrices, enabling probability-weighted entry signals rather than hard regime classifications.
- Model selection via BIC across 2-, 3-, and 4-state models.
- Evaluation: one-step-ahead forecasting accuracy; log-likelihood comparison. Sharpe ratio and Calmar ratio mentioned as performance metrics for regime-aware strategies.

---

## Results
- 4-state NH-HMM wins on BIC and one-step-ahead accuracy across the 2024–2026 Bitcoin sample.
- Regime-aware strategies (enter only in identified bull/calm regimes) show "superior risk-adjusted returns" vs. static single-regime baselines — but specific Sharpe/Calmar numbers were not retrievable from the abstract alone.
- The NH-HMM better captures the rapid volatility spikes characteristic of 24/7 crypto markets that break fixed-transition homogeneous models.
- Adding macro covariates (VIX, DXY, on-chain flow) to the transition equation materially improves regime forecasting during crisis periods.

---

## Relevance to this project
This paper gives us crypto-specific empirical validation for the HMM approach we're already considering (the wiki's open hypothesis H5 asks whether any HMM specification fixes the `TrendFilter200` whipsaw problem). Key takeaways:

1. **Use 4 states, not 2.** The wiki considered a 2-state Gaussian HMM (bull/bear); the paper finds 4 states is optimal on Bitcoin — likely low-vol bull, high-vol bull, low-vol bear, high-vol bear (or calm). This extra granularity lets you be flat in high-volatility bear (whipsaw zone) while staying long in calm bull.

2. **Non-homogeneous transitions matter.** Static transition matrices miss the clustering of regime shifts. Incorporating even one covariate (e.g. 24h realised volatility as a covariate to the transition equation) would let the model adjust how "sticky" regimes are based on current market conditions.

3. **Bayesian posteriors → probabilistic entry.** Rather than hard `if state == 'bull': enter`, use posterior probability: `if P(bull | data) > 0.65: enter`. This directly addresses the whipsaw by requiring high-confidence regime labelling before committing.

4. **Continuous 24/7 market advantage.** The paper validates HMM on a continuous (no-weekend) market — equity-derived HMM specs do not transfer without retraining on crypto data. This confirms we should not borrow fitted parameters from equity literature.

Freqtrade implementation sketch (replacing `TrendFilter200`):
```python
from hmmlearn import hmm
import numpy as np

# Fit NH-HMM on rolling 500 bars of returns + volume
model = hmm.GaussianHMM(n_components=4, covariance_type='full', n_iter=100)
obs = np.column_stack([returns_window, log_volume_window])
model.fit(obs)

# Predict regime probability for last bar
hidden_states = model.predict_proba(obs)
p_bull = hidden_states[-1, bull_state_idx]   # identify by sorting by mean return
dataframe['regime_bull_prob'] = p_bull
dataframe.loc[dataframe['regime_bull_prob'] > 0.65, 'enter_long'] = 1
```

**Addresses priority:** Priority 2 — Regime detection for 24/7 markets (OPEN). Specifically: (a) applies HMM directly to crypto data and reports regime-conditional performance; (b) confirms non-homogeneous transitions are needed (static specs fail); (c) validates on the 2024–2026 Bitcoin period that overlaps our test window.

---

## Concepts
→ [[HMM]] | [[regime-detection]] | [[non-homogeneous-HMM]] | [[Bayesian-estimation]] | [[bitcoin]] | [[bull-bear-regime]] | [[whipsaw]]
