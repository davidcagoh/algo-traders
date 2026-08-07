# Signed Mean-Variance Regime Slices

Universe: `BTC, ETH, SOL, AVAX, DOGE`

Window: `2020-11-23 00:00:00+00:00` -> `2026-06-10 00:00:00+00:00`

Same deployed signed-MV parameters: 60d lookback, weekly rebalance, 20% per-token cap, 100% gross cap, 0.035% turnover fee, `mean_shrink=0.50`, `risk_aversion=1.0`, `turnover_penalty=0.05`.

Data note: Uses Binance USDT-margined perp daily candles and funding on the older 5-coin major proxy universe.

| Period | Regime | Days | Signed MV Return | Sharpe | MDD | Calmar | BTC Return | Equal Weight Return | Funding Coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | bull | 39 | 28.71% | 4.96 | -10.96% | 87.69 | 57.05% | 13.74% | 100.0% |
| 2021 | bull | 365 | 810.89% | 2.44 | -28.20% | 28.75 | 59.61% | 3656.81% | 100.0% |
| 2022 | bear | 365 | -30.00% | -0.53 | -56.95% | -0.53 | -64.21% | -77.85% | 100.0% |
| 2023 | bull | 365 | 36.72% | 0.98 | -42.86% | 0.86 | 155.87% | 222.74% | 100.0% |
| 2024 | bull | 366 | -14.13% | -0.06 | -40.79% | -0.35 | 121.08% | 98.50% | 100.0% |
| 2025 | chop | 365 | -9.60% | -0.00 | -43.05% | -0.22 | -6.35% | -37.34% | 100.0% |
| 2026 | drawdown | 161 | -15.32% | -0.68 | -22.97% | -1.37 | -29.82% | -40.39% | 100.0% |
