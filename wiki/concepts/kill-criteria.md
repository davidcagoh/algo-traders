# Kill Criteria

**Status:** Cross-project methodology. Last updated 2026-05-16.

Pre-registered retirement rules for any strategy that graduates from a backtest leaderboard to paper-trading or live capital. Applies equally to the Hyperliquid backtesting subproject and the feishu Chinese A-share subproject — venue-specific thresholds differ, but the structure is the same.

---

## Why pre-register

The actual edge in long-running quant operations is **not signal quality** — it is the discipline to turn a strategy off when it is breaking down. Dan Davies (ex-quant, paraphrased from Leek 2025):

> *"Quant funds survive in the long term because of fundamentally non-quantitative attributes of their managers; it is a very rare person indeed who combines the common sense to turn the model off when it is breaking down, with self-discipline to resist the temptation to tinker."*

Without a written retirement rule, two failure modes dominate:

1. **Regime-decay invisibility.** A strategy degrades smoothly. No single day looks like the day to stop. You keep trading.
2. **Backfit defence.** When live results disappoint, you rationalise (small sample, noise, regime, costs) instead of retiring. The longer the rationalisation goes on, the more capital it costs.

Pre-registration eliminates both. The rule is written *before* the first dollar of paper-trade or live capital is allocated. Deviation requires a new dated decision doc that explicitly supersedes the old one — not a verbal reinterpretation.

This makes kill criteria a **mechanism**, not a metric. The mechanism is "this written threshold triggers this written action". The metric (MDD, Calmar, cointegration p-value, OU half-life) is only the input to the mechanism. Confusing the two is the source of most discretionary retirement-paralysis.

See `learnings.md` open hypothesis #2 for the cross-project hypothesis this methodology emerged from.

---

## Pre-registration discipline (the hard rule)

Every new strategy that graduates from research to evaluation gets a kill-criteria decision doc *before* its first backtest. This is the pre-registration discipline established by decision 005: write the dated decision record before seeing the candidate's backtest.

Lift this as a cross-project methodology rule:

- **Freqtrade experiment:** decision docs live at `freqtrade-experiment/research/analysis/reports/YYYY-MM-DD-decision-00N-kill-criteria-<strategy>.md`.
- **Feishu competition:** decision docs live with that project's dated reports under `feishu-competition/analysis/reports/`.
- **Naming:** the strategy name in the filename must match the strategy file in code exactly.
- **Timing:** the doc is committed before any backtest result that would inform threshold-setting is logged. This is the only way to keep thresholds from being silently moved after seeing the result.

Worked examples (backtesting subproject):

- [`004-kill-criteria-sma-regime-180.md`](../../freqtrade-experiment/research/analysis/reports/2026-05-10-decision-004-kill-criteria-sma-regime-180.md) — T3 (SmaRegime180), the template for the four canonical axes plus continuous shrinkage.
- [`006-kill-criteria-pairs.md`](../../freqtrade-experiment/research/analysis/reports/2026-05-16-decision-006-kill-criteria-pairs.md) — pairs / cointegration-conditional family.
- [`007-kill-criteria-cross-sectional.md`](../../freqtrade-experiment/research/analysis/reports/2026-05-16-decision-007-kill-criteria-cross-sectional.md) — cross-sectional momentum.
- [`008-kill-criteria-funding-mr.md`](../../freqtrade-experiment/research/analysis/reports/2026-05-16-decision-008-kill-criteria-funding-mr.md) — funding-rate mean-reversion.

---

## The four canonical hard-kill axes

Every kill rule, regardless of strategy family or subproject, must specify thresholds on at least these four axes. They are the **floor** — family-specific axes (see next section) layer on top.

| Axis | What it catches | Typical metric |
|------|-----------------|----------------|
| **(i) Drawdown ceiling** | Catastrophic capital impairment | Max drawdown, or Ulcer index for chronic-underwater curves |
| **(ii) Consecutive losing trades / stops** | Signal degradation faster than equity-curve smoothing reveals | N consecutive full-stop closes |
| **(iii) Rolling-window return-flat** | Slow death by zero alpha | Rolling 365d (or venue-appropriate) net return ≤ 0 for N days |
| **(iv) Walk-forward risk-adjusted metric** | Out-of-sample structural decay | Calmar / Sharpe / SQN on the most-recent rolling window below threshold |

Why all four. Each catches a failure mode the others miss:

- (i) alone misses the strategy that bleeds 30 small losses without a single big one.
- (ii) alone misses the strategy whose signal still wins occasionally but at terrible risk/reward.
- (iii) alone misses the fast-blowup case.
- (iv) alone is the most principled but requires enough OOS data to be meaningful — typically the last to come online.

**Calibration is venue/horizon-specific.** Backtesting's T3 calibrated MDD ≤ 5.5% from a BTC bear-window backtest with IS MDD of 1.74% (3.2× rule, see below). Feishu's equivalent strategy must calibrate from an A-share bear-window backtest with its own IS MDD — the *structure* is portable, the *number* is not. Same for the rolling-window length (365d for crypto; A-share equivalent depends on what "one full regime cycle" looks like in the venue), the consecutive-stops count, and the walk-forward Calmar threshold.

---

## Family-specific kill rules

The four canonical axes are necessary but not sufficient. Every strategy family has a **primary failure mode** that breaks the strategy's premise before equity-curve metrics notice. The kill rule must include an axis that watches that mode directly.

| Family | Primary kill axis (in addition to the four canonical) | Why MDD alone misses it |
|--------|------|----|
| Trend / regime | (none — MDD-based axes are the primary) | The premise *is* "ride the equity curve when on, stay flat when off" |
| Pairs / cointegration | Cointegration p-value > threshold for N consecutive windows | Cointegration can decay while a stale spread still mean-reverts on a few last trades; MDD is a lagging confirmation |
| Cross-sectional momentum | Cross-sectional dispersion collapse (basket-return std → 0) | When the basket moves in lockstep, there is no rank-spread to harvest, but MDD only fires after the no-spread trades lose |
| Funding / carry mean-reversion | OU half-life drift > threshold | If the mean-reversion horizon drifts outside the strategy's time-stop, every trade structurally mismatches; MDD shows this only after several mismatched losses |

The principle: **for any strategy whose premise depends on a measurable structural property of the market** (cointegration, dispersion, OU half-life, funding sign, regime persistence), the kill rule monitors that property directly. The four canonical axes catch the equity-curve consequences; the family axis catches the mechanism breaking.

Worked examples in the backtesting subproject ([`006`](../../freqtrade-experiment/research/analysis/reports/2026-05-16-decision-006-kill-criteria-pairs.md), [`007`](../../freqtrade-experiment/research/analysis/reports/2026-05-16-decision-007-kill-criteria-cross-sectional.md), [`008`](../../freqtrade-experiment/research/analysis/reports/2026-05-16-decision-008-kill-criteria-funding-mr.md)). The same template applies to feishu: an A-share pairs strategy would still monitor cointegration p-value; an A-share factor-rotation strategy would still monitor factor-return dispersion.

---

## Continuous shrinkage (Davies–Ravagnani style)

Binary kill switches leave signal on the table when a strategy is **regime-conditional** rather than broken. A pure trend-following strategy in a chop regime is not dead — it is in its dormant phase. Hard-killing it forfeits the next bull. The fix is a **continuous shrinkage factor** that scales position size smoothly between healthy and dead.

This is the structural form Ravagnani et al. 2026 give for robust forecast combination:

```
h_robust = h_standard × (1 − δ/σ²)
```

— shrink the hedge ratio continuously as forecast error grows relative to volatility, rather than switching off above a threshold. The same shape works for strategy position sizing:

```
size_factor = f(rolling-PF, rolling-Calmar, regime-ratio, family-specific-quality)
size_factor ∈ [0, 1]
realised_size = base_capital × size_factor
```

Worked example from T3 ([`004-kill-criteria-sma-regime-180.md`](../../freqtrade-experiment/research/analysis/reports/2026-05-10-decision-004-kill-criteria-sma-regime-180.md)):

```
size_multiplier = min(1.0,
                      pf_factor      ×
                      calmar_factor  ×
                      regime_factor)

pf_factor     = clip( (rolling_180d_PF - 1.0) / 1.0,             0.0, 1.0 )
calmar_factor = clip(  rolling_180d_Calmar / 4.0,                0.0, 1.0 )
regime_factor = clip( 1.0 - abs(log(bull_calmar / bear_calmar)) / log(3),
                                                                  0.25, 1.0 )
```

Reading:
- PF below 1.0 → zero size. PF at backtest level → full size. PF at 2.0 → full size (clipped).
- Rolling Calmar at 4.0+ → full size. At 2.0 → half size. Below zero → zero size.
- Bull-vs-bear Calmar divergence > 3× → quarter size. Captures regime-asymmetry breaking out of historical bounds.

Family-specific multipliers replace the `regime_factor` term:

- **Pairs:** `cointegration_factor = clip((p_threshold − rolling_30d_p) / p_threshold, 0, 1)` — shrinks to zero as p approaches the kill threshold from below.
- **Cross-sectional momentum:** `dispersion_factor = clip(rolling_30d_basket_return_std / σ_floor, 0, 1)` — shrinks when the basket moves in lockstep.
- **Funding MR:** `hl_factor = clip(2.0 − rolling_30d_half_life / hl_target, 0, 1)` — shrinks as half-life drifts above the time-stop horizon.

The **realised size is computed weekly** from a trailing window (180 calendar days in the T3 example). The window length and recompute cadence are calibrated to the strategy's average trade duration and signal half-life — too short and noise dominates the multiplier; too long and decay is slow to register.

The factor is reset only by a fresh full window of new data, never by a single good week. This is the same anti-tinker discipline that motivates pre-registration: the rule's behaviour must be robust to the operator's mood.

---

## Calibration discipline

**Default rule for the hard MDD ceiling:** 3× the backtest's observed in-sample MDD.

T3 example: IS MDD 1.74%, ceiling 5.5% ≈ 3.2× IS. The 3× rule reflects the consistent empirical finding that backtests systematically understate live drawdowns — execution slippage, missing fills, regime carry-over, and the survivorship bias of the backtest universe all bias IS MDD downward.

**Where the 3× default breaks:**

- **Out-of-sample regime outside the backtest.** If the backtest window does not contain at least one full bull-and-bear cycle for the venue, IS MDD is missing the actual drawdown the strategy will experience. Calibrate from a wider validation set (e.g. CEX cross-cycle validation for the backtesting subproject; multi-cycle A-share validation for feishu) before applying the 3× multiplier.
- **Family-specific shape.** Pairs strategies inherently have larger MDD shape (both sides of the spread can blow up) than single-asset trend. T3's 5.5% became 8% for X1 — calibrated from the bear-cycle empirical reference, not from the IS MDD. Same for cross-sectional momentum (12% in X2), where synchronised basket drawdowns dominate.
- **Short-horizon MR strategies.** A tight mean-reversion strategy should have *small* MDD by construction (each trade is bounded by a time-stop on the half-life). F1 set its ceiling at 5% — *lower* than T3, not higher — because a large MDD means the half-life estimate is stale or the threshold is wrong, not that the strategy is enduring a hard regime.

**Same logic for the other three canonical axes:**

- **Consecutive stops:** anchor to the backtest's worst observed streak × 2 (or × 3 for tight stops). T3 saw one single −10% stop in backtest; threshold of six consecutive implies the regime filter has stopped suppressing whipsaw.
- **Rolling-window return-flat:** anchor to roughly one full cycle of the venue's typical regime length. 365 days for crypto majors; venue-equivalent for A-shares.
- **Walk-forward risk-adjusted threshold:** anchor to the project's documented "minimum viable" risk-adjusted return (the leaderboard's bottom-quartile threshold). T3 used Calmar < 2.0.

State the calibration source explicitly in the decision doc. "5.5% because 3× IS MDD" is a complete justification; "5.5% because it felt right" is a future tinker waiting to happen.

---

## Hard kill vs revise

A threshold breach **triggers a review, not an automatic kill**, when *any* of:

1. **Within 1σ of the threshold.** A breach by 0.1pp on a metric whose monthly noise is 0.3pp is not a structural break; it is sampling variance. The review re-evaluates with one more window of data before acting.
2. **Single-event breach.** One catastrophic day vs sustained underperformance. The review identifies whether the day was a tail event (slippage spike, exchange outage, untracked news) or the start of a regime change.
3. **Portfolio-justified.** The strategy is breaching its standalone threshold but the portfolio combining it with other live strategies still has positive marginal contribution under all weighting schemes (MDB > 0 robust). The cross-reference is the upcoming `freqtrade-experiment/research/analysis/reports/2026-05-16-decision-009-portfolio-aware-k1.md` (being written in parallel) as the worked example.

All three are **review triggers**, not auto-overrides. The review's output is one of:

- **Continue at current size** (the breach was noise or single-event)
- **Force-shrink** (binding override of the continuous-shrinkage factor downward, with a written reason)
- **Hard-kill** (the breach was structural)

The review must happen within a fixed window (e.g. 5 trading days) — avoiding the review is itself a violation. Discretion enters only at the review; it does not enter at the breach.

Outside these three cases, a hard-kill breach is **a hard kill**. The strategy retires. Re-listing requires a new strategy file with a new pre-registered specification — not a modified version of the retired one. This eliminates the "tinker until it passes" path entirely.

---

## Quarterly walk-forward review (mandatory cadence)

Independent of any breach, every live strategy gets a quarterly walk-forward review.

**Re-fit (against the most recent 90 days of fresh data):**

- Strategy-internal parameters that depend on recent regime (regime filter lookback, slope-gate threshold, OU calibration window, β for pairs).
- Continuous-shrinkage factor inputs (rolling PF, rolling Calmar).

**Re-evaluate (no parameter changes — pure OOS check):**

- The four canonical hard-kill axes against the new walk-forward fold.
- The family-specific kill axis against the new fold.
- The continuous-shrinkage size factor's recent trajectory.
- Cross-strategy correlation and MDB (does this strategy still contribute to the book?).

**Retire if:**

- Any hard-kill axis breaches and survives the revise-vs-kill review.
- Walk-forward Calmar < documented minimum for two consecutive quarters.
- MDB-rp < 0 robust across all three weighting schemes for two consecutive quarters.

The cadence is **quarterly** because shorter windows are noise-dominated at typical strategy trade frequencies (the backtesting subproject's strategies trade once every 25 days on average; a monthly review would have ~1 trade of new evidence). Subprojects with higher trade frequency can run a tighter cadence, but never tighter than the strategy's average-trade-duration × ~20 (the rough sample size for any metric to stabilise).

---

## What this methodology does not cover

- **Allocation across strategies.** The kill rule governs one strategy's own size multiplier. Cross-strategy capital allocation is a separate methodology, to be written when ≥2 strategies are live in either subproject.
- **Entry/exit logic changes.** Tweaking the strategy is *not* an alternative to a kill rule. If kill criteria fire, the strategy retires. A modified version is a new strategy with its own pre-registered criteria.
- **Discretionary pauses.** "Let me think about this" is forbidden between reviews. Either the rules say continue, shrink, or stop. Discretion enters only at the quarterly walk-forward review or at a written revise-vs-kill review triggered by a breach.

---

## Cross-references

- `learnings.md` open hypothesis #2 — original cross-project hypothesis on kill criteria, plus the Davies/Ravagnani references that motivate continuous shrinkage.
- `learnings.md` "Six-layer evaluation stack" entry (2026-05-16) — L1–L6 layered evaluation. Kill criteria operate at L1–L3 (hard thresholds) and L6 (portfolio-additive review), with L4–L5 informing calibration of the underlying metrics.
- [`methodology/cv-and-deflation.md`](cv-and-deflation.md) — pre-registration discipline applied to sweep gating; same anti-tinker principle.
- [`methodology/multi-objective-search.md`](multi-objective-search.md) — Pareto-front frame; kill criteria are how a Pareto-frontier strategy gets demoted off the frontier.
- Backtesting decision docs [`004`](../../freqtrade-experiment/research/analysis/reports/2026-05-10-decision-004-kill-criteria-sma-regime-180.md), [`006`](../../freqtrade-experiment/research/analysis/reports/2026-05-16-decision-006-kill-criteria-pairs.md), [`007`](../../freqtrade-experiment/research/analysis/reports/2026-05-16-decision-007-kill-criteria-cross-sectional.md), [`008`](../../freqtrade-experiment/research/analysis/reports/2026-05-16-decision-008-kill-criteria-funding-mr.md) — concrete worked examples of the four canonical axes + family axis + continuous shrinkage.
