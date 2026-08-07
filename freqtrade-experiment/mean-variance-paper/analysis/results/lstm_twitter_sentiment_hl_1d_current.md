# LSTM Twitter Sentiment Probe

Daily Hyperliquid OHLCV plus Santiment `sentiment_weighted_twitter_1d`.

Charts: [diagnostics](../assets/lstm_twitter_sentiment_diagnostics_current.png), [per-coin returns](../assets/lstm_twitter_sentiment_per_coin_current.png), [VVV/XPL focus](../assets/lstm_twitter_sentiment_vvv_xpl_current.png).

## Aggregate

| Universe | Strategy | Days | Return | Sharpe | MDD | Calmar | Avg Exposure | Turnover |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| MV | lstm_only | 64 | 31.05% | 4.43 | -9.51% | 38.64 | 1.00 | 0.77 |
| MV | lstm_twitter | 64 | 37.02% | 4.90 | -6.54% | 76.91 | 1.00 | 0.83 |
| Lower-cap | lstm_only | 64 | -10.09% | -1.18 | -20.40% | -2.23 | 1.00 | 0.97 |
| Lower-cap | lstm_twitter | 64 | -5.81% | -0.60 | -19.79% | -1.46 | 1.00 | 1.02 |
| VVV/XPL | lstm_only | 64 | 290.10% | 8.16 | -12.55% | 18740.22 | 1.00 | 0.75 |
| VVV/XPL | lstm_twitter | 64 | 261.25% | 7.94 | -11.94% | 12709.83 | 0.98 | 0.72 |

## Per Coin

| Coin | Status | Coverage | Test | LSTM Return | LSTM Sharpe | LSTM+Twitter Return | LSTM+Twitter Sharpe | Reason |
|---|---|---:|---:|---:|---:|---:|---:|---|
| BTC | ok | 97.6% | 64 | -10.98% | -1.84 | 6.65% | 1.18 | |
| HYPE | ok | 97.6% | 64 | 12.21% | 1.17 | 34.61% | 2.40 | |
| PAXG | ok | 97.6% | 64 | -5.07% | -1.27 | -0.51% | -0.05 | |
| TRX | ok | 97.6% | 64 | -14.53% | -4.12 | -8.93% | -2.53 | |
| WLFI | ok | 97.6% | 64 | -20.65% | -1.27 | -6.64% | -0.06 | |
| VVV | ok | 97.6% | 64 | 418.31% | 7.58 | 372.11% | 7.16 | |
| TON | ok | 97.6% | 64 | -3.97% | 0.46 | -1.75% | 0.53 | |
| ZRO | ok | 97.6% | 64 | -35.61% | -2.38 | -44.75% | -3.16 | |
| XPL | ok | 97.6% | 64 | 111.25% | 4.50 | 152.18% | 5.74 | |
| FARTCOIN | ok | 100.0% | 64 | -34.22% | -1.71 | -30.54% | -1.58 | |
| WIF | ok | 100.0% | 64 | 6.39% | 0.90 | -23.49% | -2.04 | |
| POPCAT | ok | 100.0% | 64 | -22.35% | -1.66 | 15.99% | 1.56 | |
| KPEPE | skip | | | | | | | missing or short OHLCV |
| KBONK | skip | | | | | | | missing or short OHLCV |
| KSHIB | skip | | | | | | | missing or short OHLCV |
| KFLOKI | skip | | | | | | | missing or short OHLCV |
| SPX | ok | 100.0% | 64 | 6.02% | 0.80 | -6.38% | 0.04 | |
| PENGU | ok | 100.0% | 64 | 34.02% | 2.49 | 63.63% | 3.64 | |
| PNUT | ok | 100.0% | 64 | -51.62% | -2.20 | -49.54% | -2.06 | |
| BRETT | ok | 100.0% | 64 | 7.03% | 0.88 | 22.96% | 1.77 | |
| MELANIA | ok | 100.0% | 64 | -26.45% | -3.06 | -30.51% | -3.62 | |
