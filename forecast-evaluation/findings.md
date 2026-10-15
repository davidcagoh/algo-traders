# TimesFM 3.0 evaluation findings

## Run

- Run: `f0cb1164541408bc3056`
- Report: [`runs/f0cb1164541408bc3056/report.html`](runs/f0cb1164541408bc3056/report.html)
- Model: TimesFM 3.0.2, checkpoint `google/timesfm-3.0-pytorch` at revision `43046b85ec22d584a13f8098c2ed39c889e129c2`, CPU inference
- Data: BTC and ETH hourly close-to-close log returns derived from 47,520 rows in pinned snapshot `f1c29fc3e938bfa7b208` (`binance.candles_1m`), SHA-256 `2b60d1bf63d96ba0098c9b04b84b13e396b1accd270c4439075d48f28e83167e`
- Protocol SHA-256: `9d79a2e058aa6f58998503e7009ecc67d6ba9d13f782a9c615a68412ca329270`
- Historical replay: 135 origins per asset and mode, scored at leads 1–168 hours. Post-release freshness: 15 origins per asset and mode, scored at 1, 6, and 24 hours.

## Results

Across historical per-lead scores, mean MAE skill versus zero-return was **−0.20%** for univariate and **−0.16%** for multivariate TimesFM. Versus last-return persistence, mean MAE skill was **+34.04%** and **+34.07%**, respectively. Mean directional accuracy was approximately **50%** in both modes. These averages weight each asset and lead equally.

On the post-release freshness slice, mean per-lead MAE skill versus zero-return was **−3.48%** univariate and **−3.34%** multivariate; versus last-return persistence it was **+26.59%** and **+26.61%**. Mean directional accuracy was **36.7%** univariate and **42.2%** multivariate. Each estimate uses only 15 origins per asset, so treat it as exploratory.

At the 168-hour cumulative-return horizon in historical replay, TimesFM MAE was **10.4%** and **16.1%** worse than zero-return for univariate BTC and ETH, and **7.1%** and **13.2%** worse for multivariate BTC and ETH. Compared with last-return persistence, MAE skill was **88.7%–89.2%** across the four asset/mode pairs. This difference reflects a weak long-horizon persistence baseline; it does not establish useful trading forecasts.

Across per-lead historical quantile forecasts, observed q10–q90 coverage ranged **38.5%–97.8%**; in freshness it ranged **73.3%–93.3%**. The intervals are nominal and uncalibrated, with coverage varying substantially by horizon.

## Interpretation and limits

In this experiment TimesFM usually beat last-return persistence on point MAE, but did not consistently beat the zero-return baseline. Directional accuracy was near chance in historical replay and weaker in the small freshness sample. The results do not support a claim of trading edge, profitability, or statistical significance; this evaluation did not test a strategy, transaction costs, or execution.

Historical replay targets may overlap TimesFM pretraining. Freshness contains only 15 origins per asset and is low-power. Nominal q10–q90 intervals were not calibrated. The checkpoint weights are restricted to **non-commercial, non-production use**; this restriction applies regardless of the package's Apache license. Review the checkpoint terms before any use beyond this experiment.

## Reproducibility

The run metadata pins the snapshot, protocol, evaluator source, model package, checkpoint revision, and inference settings. Repeated evaluation with the same inputs reused run ID `f0cb1164541408bc3056`. Forecasted return rows matched the realized snapshot returns exactly during verification. The report is standalone and uses saved run artifacts; it needs no ClickHouse connection or model checkpoint to view.

## Statistical review (exploratory, post hoc)

Analysis bundle: [`analyses/f0cb1164541408bc3056/ac3c3ba51e0ce4a5d6f6/analysis.json`](analyses/f0cb1164541408bc3056/ac3c3ba51e0ce4a5d6f6/analysis.json). The separately generated review viewer is in the same directory.

- Compared paired per-origin absolute loss differences (TimesFM minus baseline), using a stationary bootstrap with four origins per mean block, 10,000 resamples, and a fixed seed. Shared resampled origin indices preserve BTC/ETH and univariate/multivariate dependence within each segment.
- Holm correction covers all **1,400** unique saved MAE comparisons across leads, cumulative horizons, segments, assets, modes, and baselines. **None** passes the family-wise 5% threshold; the smallest adjusted p-value is **0.140**. The most favorable raw p-values do not survive the broad family correction.
- The 24-hour cumulative comparison is available for historical replay. Freshness inference is available at saved leads 1, 6, and 24; the frozen artifact did not retain the intervening hourly forecast path, so 6-hour and 24-hour cumulative freshness scores cannot be reconstructed.
- This inferential plan was specified after inspecting the run. It demonstrates paired uncertainty and multiplicity handling, but is exploratory rather than confirmatory. Historical results may overlap pretraining, and 15 freshness origins are too few for strong claims. The findings do not demonstrate TimesFM's superiority or equivalence.
