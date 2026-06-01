# Evaluating Structured Strategy Backtests: Peer Benchmarks, Regime Timing, and Live Performance

**Authors:** Chang Liu (University of Trento; Resonanz Capital GmbH, Frankfurt)
**Venue/Source:** arXiv q-fin.PM (submitted to Journal of Asset Management)
**arXiv/DOI:** https://arxiv.org/abs/2604.18821
**Date:** April 20, 2026

---

## Core Claim
Pro-forma (marketed backtest) performance of commercially distributed strategies has *limited portability* into the live trading period, and the degradation is sharper when a strategy launches after an unusually strong run in its dominant factor regime. Backtests predominantly capture the common factor regime that existed at construction time, not strategy-specific skill.

---

## Method
- Dataset: 1,726 commercially distributed structured strategies from 10 global institutions. Each strategy has a marketed backtest period and a subsequent live period.
- Portability is measured as: raw live Sharpe vs. live Sharpe measured *relative to peer and external benchmarks* (the benchmark adjustment removes common-factor carry-over).
- Regime timing: strategies are bucketed by whether their factor regime was above/below median at launch. The subsequent live deterioration is regressed on the regime percentile at launch.
- The factor decomposition isolates whether outperformance in the backtest came from strategy skill (alpha) or from loading on a factor that happened to be in a hot regime during the backtest window.

---

## Results
- Raw pro-forma Sharpe has weak correlation with live Sharpe; once benchmarks are used, the correlation weakens sharply.
- Strategies launched after the top quartile of factor-regime conditions experience materially worse live performance than strategies launched in neutral conditions.
- The effect is asymmetric: strong regime at launch predicts underperformance; weak regime at launch does not predict outperformance.
- Implication: the discount applied to backtests should increase when the backtest was constructed in an extreme regime.

Calmar ratios not reported (structured-product context; Sharpe is the dominant metric).

---

## Relevance to this project
This paper is about traditional structured financial products (institutional distributed strategies), not directly about crypto perp strategies. However, the **mechanism is identical** to our situation:

**Our bear-market backtest problem:** All strategies tested so far (LongOnlyStrategy, TrendFilter200) were backtested over the same 200-day window (Oct 2025 → Apr 2026) — a period of sustained BTC drawdown (−37.20% buy-and-hold). This is an extreme regime. The paper's warning translates directly:

> "A strategy that looks good in a sustained bear market because it avoided long exposure has likely *found the regime*, not *found the skill*. The live period will include bull regimes it was never tested in."

**Actionable for this project:**
1. **Out-of-regime test:** Before committing to any strategy with good bear-market Calmar, test it on a bull sub-window (e.g. early 2024 Hyperliquid data if available, or reconstruct via 4h candles which cover ~830 days = 2023–2026).
2. **Benchmark-relative Calmar:** Report strategy Calmar *relative to the buy-and-hold Calmar for the same period*. Our buy-and-hold Calmar is highly negative (−37.20% / large MDD); many strategies look good simply because they do nothing.
3. **Multi-regime validation:** Any strategy selected for live trading should be validated across at least one bull and one bear sub-period, not just the current test window.

This paper reinforces the wiki's existing caution ("Every strategy tested so far beats buy-and-hold by a lot, but none of them are actually *good* — the baseline is a bear market") with a formal empirical backing.

**Addresses priority:** Priority 3 — Backtest-realistic execution (specifically the "backtest-vs-live divergence analyses" sub-priority). The paper provides the theoretical and empirical basis for the regime-timing discount to apply to all backtests produced in extreme factor regimes.

---

## Concepts
→ [[backtest-overfitting]] | [[regime-timing]] | [[pro-forma-performance]] | [[live-performance]] | [[factor-regime]] | [[Sharpe]] | [[benchmark-relative]]
