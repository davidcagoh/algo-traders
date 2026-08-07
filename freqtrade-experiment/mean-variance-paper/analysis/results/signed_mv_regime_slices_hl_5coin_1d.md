# Signed Mean-Variance Regime Slices

Universe: `BTC, ETH, SOL, AVAX, DOGE`

Window: `2020-11-23 00:00:00+00:00` -> `2025-08-28 00:00:00+00:00`

Same deployed signed-MV parameters: 60d lookback, weekly rebalance, 20% per-token cap, 100% gross cap, 0.035% turnover fee, `mean_shrink=0.50`, `risk_aversion=1.0`, `turnover_penalty=0.05`.

Caveat: this uses Hyperliquid daily candles on the older 5-coin major proxy universe. Local Hyperliquid funding coverage starts in May 2023, so 2020-2022 funding is zero-filled.

| Period | Regime | Days | Signed MV Return | Sharpe | MDD | Calmar | BTC Return | Equal Weight Return | Funding Coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | bull | 39 | 31.94% | 5.47 | -10.59% | 116.89 | 57.05% | 13.74% | 0.0% |
| 2021 | bull | 365 | 1437.63% | 2.85 | -34.10% | 42.16 | 59.61% | 3656.81% | 0.0% |
| 2022 | bear | 365 | -25.71% | -0.41 | -56.35% | -0.46 | -64.21% | -77.85% | 0.0% |
| 2023 | bull | 365 | 16.80% | 0.58 | -44.36% | 0.38 | 155.87% | 222.80% | 64.1% |
| 2024 | bull | 366 | -23.98% | -0.32 | -44.81% | -0.53 | 121.25% | 98.79% | 100.0% |
| 2025 | recovery | 240 | -22.19% | -0.65 | -43.12% | -0.74 | 20.28% | 2.70% | 100.0% |
