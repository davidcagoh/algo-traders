# Forecast inference method map

## Recommended estimand

For each saved origin, compare TimesFM's absolute forecast error with the same
origin's baseline absolute forecast error. The primary paired quantity is
`abs(TimesFM - actual) - abs(baseline - actual)`; negative values favor TimesFM.
The unit is one eligible forecast origin, not each minute bar, each lead, or
each model output row. Cumulative-return endpoints sum the hourly point
forecasts and targets first, then compare absolute cumulative errors.

## Reusable code and fit

| Existing API | Reusable part | Semantic mismatch / decision |
|---|---|---|
| `evaluation/bootstrap.py::stationary_bootstrap_indices` | Politis–Romano stationary-bootstrap indices; shared index vectors preserve pairing and cross-series dependence. | The strategy-oriented `bootstrap_ci` default estimates a statistic of one return series, not paired forecast-loss differences. Reuse the index generator only. |
| `evaluation/bootstrap.py::optimal_block_length` | A lag-1 based block-size heuristic is available. | It is explicitly heuristic and was designed around a single return series. Do not describe it as a validated selector for overlapping forecast losses. Use a declared four-origin mean block length, with origin cadence reported, and treat this choice as a sensitivity/limitation. |
| `evaluation/spa.py::spa_test` | Hansen SPA and White Reality Check over a candidate family. | It accepts candidate-versus-benchmark returns with higher-is-better semantics. This report compares a fixed TimesFM model against two named baselines; paired loss differences plus Holm correction are a more direct fit. SPA is appropriate if a searched family of forecasting models/configurations becomes the claim. |
| `evaluation/intervals.py::metrics_with_ci` | None for forecast loss as written. | Its Sharpe/CAGR/Calmar wallet estimands are strategy metrics; they do not answer forecast accuracy uncertainty. |
| `forecast_evaluation/metrics.py` | MAE, RMSE, direction, pinball loss, marginal interval coverage, and cumulative-return point scores. | These tables contain aggregates and lose the per-origin pairing needed for uncertainty. Inferential analysis reads the saved forecast rows before aggregation. |

## Analysis protocol applied to the frozen run

- Score the paired per-origin MAE loss difference for each lead and each
  cumulative horizon already present in the frozen protocol, asset, mode, and
  baseline. Keep historical replay and post-release freshness as separate
  segments. Omit cumulative horizon 1 because it duplicates the lead-1
  marginal-return comparison.
- Use a stationary bootstrap with mean block length four origins. The same
  resampled origin indices are applied to every BTC/ETH and uni-/multivariate
  comparison in a segment. Historical origins are one week apart; freshness
  origins are one day apart. Return the 2.5th and 97.5th percentiles as a
  two-sided 95% interval.
- Compute a two-sided centered-bootstrap p-value for mean paired loss
  difference. Apply Holm step-down correction across the complete family of
  saved lead and cumulative-horizon MAE comparisons, including both assets,
  modes, segments, and baselines. The report also exposes raw p-values.
- Lock the resampling seed, block length, source-run hashes, and replicate
  count in a separate analysis bundle. Never overwrite forecasts or the
  frozen run metadata.
- Freshness forecasts persisted only leads 1, 6, and 24. Those support
  per-lead uncertainty, but do not support 6h/24h cumulative-return scoring:
  the intervening hourly forecast path is absent. The report marks this as
  unavailable instead of summing sparse points.

## Interpretation boundary

This analysis protocol was written after the frozen model outputs were
available. It is therefore a transparent exploratory analysis, not a
preregistered confirmatory test. The 135 weekly historical origins are
potentially contaminated by TimesFM pretraining. The 15 post-release origins
are too few for strong claims; a wide interval or non-significant result is
not evidence that methods are equivalent. A prospective confirmatory claim
needs a protocol frozen before new, genuinely post-release outcomes are
observed.

Forecast accuracy is separate from strategy returns. DSR, PBO, Sharpe,
transaction costs, execution, and SPA over a searched strategy/model family
remain outside this raw forecast comparison.

## Method references

- Politis and Romano (1994), *The Stationary Bootstrap*,
  <https://doi.org/10.1080/01621459.1994.10476870>.
- Hansen (2005), *A Test for Superior Predictive Ability*,
  <https://doi.org/10.1002/jae.800>.
- Holm (1979), *A Simple Sequentially Rejective Multiple Test Procedure*,
  <https://doi.org/10.2307/4615733>.
- Salesforce GIFT-Eval, benchmark design, baseline comparisons, reproducible
  evaluation code, and leakage metadata: <https://arxiv.org/abs/2410.10393> and
  <https://github.com/SalesforceAIResearch/gift-eval>.
- Google Research's TimesFM 3.0 post shows a readable public forecast-model
  comparison format; its reported benchmark results are not evidence for this
  BTC/ETH experiment:
  <https://research.google/blog/timesfm-3-a-zero-shot-foundation-model-for-multivariate-forecasting/>.
- Nixtla's rolling-window cross-validation example:
  <https://nixtla.github.io/nixtlar/articles/cross-validation.html>.
