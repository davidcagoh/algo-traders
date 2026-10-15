# Current-data TimesFM evaluation demo

## Decision

Use the existing pinned BTC/ETH snapshot and reviewed analysis artifacts. Do
not wait for future ClickHouse data or repeat the same model run. Present this
as a **statistically rigorous retrospective evaluation demo**, not a
confirmatory claim about TimesFM's zero-shot performance.

That distinction is necessary because the forecast results have already been
inspected, and the historical replay may overlap the model's pretraining. The
current data can demonstrate paired evaluation, dependence-aware uncertainty,
multiple-comparison control, provenance, and honest interpretation. It cannot
retroactively become confirmatory by choosing a primary endpoint now.

## Current evidence

- Frozen Binance spot snapshot: `f1c29fc3e938bfa7b208`, SHA-256
  `2b60d1bf63d96ba0098c9b04b84b13e396b1accd270c4439075d48f28e83167e`.
- 47,520 normalized hourly bars: 23,760 each for BTC and ETH, from 2024-01-01
  through 2026-09-16 23:00 UTC.
- Forecast run: [`runs/f0cb1164541408bc3056`](runs/f0cb1164541408bc3056).
- Statistical review bundle:
  [`analyses/f0cb1164541408bc3056/ac3c3ba51e0ce4a5d6f6`](analyses/f0cb1164541408bc3056/ac3c3ba51e0ce4a5d6f6).
- 1,400 paired comparisons were analyzed with a four-origin stationary
  bootstrap, 10,000 replicates, and Holm family-wise correction. None passed
  adjusted p < 0.05; the smallest adjusted p-value was 0.140.
- For BTC univariate 24-hour cumulative-return MAE versus zero return, TimesFM
  had MAE 0.02136 versus 0.02025 for the baseline (5.5% higher error). The raw
  two-sided p-value was 0.020, but the Holm-adjusted p-value was 1.0. This is a
  useful demonstration of why the full comparison family and correction must
  be shown instead of selecting a favorable raw result.

## How to present it

Lead with the finding that the evaluation provides no multiplicity-adjusted
evidence that TimesFM beats the simple baselines on this dataset. Show the
estimate, interval, raw p-value, adjusted p-value, number of origins, and
comparison family together. State that historical results may overlap
pretraining and the post-release segment contains only 15 daily origins per
asset. Keep all trading-performance claims out of scope.

The report remains a retrospective, post-hoc analysis. Do not relabel it as a
pre-registered confirmatory test. A future confirmatory study would need a
new untouched test set; it is not required for this current-data demo.

## Reproduction

The existing local environment and artifacts are sufficient. Validate the
frozen input without loading the model:

```bash
forecast-evaluation/.venv/bin/timesfm-eval validate \
  --workspace . --protocol forecast-evaluation/protocol.json
```

The verified run and analysis are already saved above. The ClickHouse source's
latest available bar is 2026-09-16; no data refresh is needed for this demo.
