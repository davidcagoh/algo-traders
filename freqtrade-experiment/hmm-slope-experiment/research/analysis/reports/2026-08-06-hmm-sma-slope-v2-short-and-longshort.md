# HmmSmaSlopeV2Short / HmmSmaSlopeV2LongShort — short-side backtest — 2026-08-06

**Strategy files:** `strategies/HmmSmaSlopeV2Short.py`, `strategies/HmmSmaSlopeV2LongShort.py`
**Data:** Binance USDT-perp 6-coin (bull) + Hyperliquid USDC 7-coin (bear), 4h, fee 0.00035
**Configs:** `configs/config_binance_multi.json`, `configs/config_hl_multi.json`

---

## Thesis

Following up on the parked V2 Hyperliquid paper run (21 trades, -3.54%, 4.8% win rate,
11-loss streak — see `execution/records/results/2026-08-05-hl-paper-evaluation.md`):
is a short-side variant of the HMM/slope signal viable, either alone or combined with
V2's proven long side?

`HmmSmaSlopeV2Short` mirrors V2's structure onto shorts: `bear_prob = 1 - bull_prob`
(the complementary HMM posterior mass, since bull/bear states partition all 4
components), entry on `bear_prob` crossing up through 0.65, size by negative slope
magnitude, exit on `bear_prob` dropping below 0.45 or slope flipping positive.

`HmmSmaSlopeV2LongShort` runs V2's long entries and V2Short's short entries in the
same strategy, sharing `max_open_trades` capital across both books.

## Metrics

### Bull window (Binance 6 coins, 2022-11-01 → 2025-01-01, market +190.83%)

| Metric | V2 (long-only) | V2Short (short-only) | V2LongShort (combined) |
|---|---:|---:|---:|
| **Total return** | +33.44% | -4.07% | +26.79% |
| **MDD** | 5.89% | 12.03% | 13.52% |
| **Sharpe** | — | -0.20 | — |
| **Trades** | 254 | 227 | 527 (300 long / 227 short) |
| Long / short profit | — | — | +30.92% / -4.14% |

### Bear window (Hyperliquid 7 coins, 2025-10-15 → 2026-05-09, market -38.61%)

| Metric | V2 (long-only) | V2Short (short-only) | V2LongShort (combined) |
|---|---:|---:|---:|
| **Total return** | -1.58% | -13.12% | -14.70% |
| **MDD** | 4.44% | 16.07% | 20.01% |
| **Sharpe** | — | -2.61 | — |
| **Calmar** | — | -7.57 | — |
| **SQN** | — | -2.46 | — |
| **Win rate** | — | 30.8% | 30.5% (53/174) |
| **Max consecutive losses** | — | 15 | 12 |
| **Trades** | 44 | 130 | 174 (44 long / 130 short) |
| Long / short profit | — | — | -1.58% / -13.12% |

---

## The decisive finding

**The short side has no edge, even in the regime that should favor it.** The bear
window (2025-10-15 → 2026-05-09) had the market down 38.61% — about as clean a
directional tailwind as a short thesis could ask for — and `HmmSmaSlopeV2Short` still
lost 13.12% with a 16.07% MDD, more than 3x the project's 5.5% hard-kill threshold.
This isn't "needs more data" or "wrong regime tested" — it's a signal that's
directionally wrong even when direction should have helped, which points at the
signal construction itself (see What didn't, below) rather than bad luck.

**Combining long and short is strictly worse than either alone, in both windows.**
`HmmSmaSlopeV2LongShort` never beats V2 long-only and never beats V2Short short-only
on any window:
- Bull: long side alone contributed +30.92% (in line with V2), but the short side's
  -4.14% drag brought the total to +26.79% — *and* more than doubled MDD (5.89% →
  13.52%), because both books draw from the same `max_open_trades` capital pool and
  the short losses widen the combined equity curve's troughs independent of the long
  side's health.
- Bear: both books lost simultaneously (long -1.58%, short -13.12%), stacking to
  -14.70% total with MDD 20.01% — worse than short-only's 16.07%, since capital that
  would otherwise sit idle (V2 long-only skips bear entries via slope gating) now goes
  into short trades that also lose.

## What didn't

- **`bear_states = mean return ≤ 0`** is the complement of V2's `bull_states = mean
  return > 0` by construction, but that complement is too permissive — it fires on
  flat/choppy states, not just clean downtrends. The HMM's 4-state fit likely has an
  inherent bull-side bias from how it was originally validated (trained mostly on
  bull-skewed data), so "not bull" isn't the same signal quality as "bull" mirrored.
- **Capital sharing compounds losses, it doesn't diversify them.** The combined
  strategy's `max_open_trades=6/7` is shared across long and short signals; when both
  sides lose in the same window (the bear case), the shared pool means there's no
  "the winning side offsets the losing side" effect — there's no winning side.

## Next test

None planned. This is a kill, not a "needs iteration" result — the short signal would
need a redesigned entry condition (not the complement of the bull-state definition)
before it's worth backtesting again, and there's no standing hypothesis for what that
redesign should be.

---

## Reproducibility

```shell
# Short-only, bull
docker run --rm -v "$(pwd)":/freqtrade/user_data algo-traders/freqtrade:hmmlearn-backtest3 \
  backtesting --datadir /freqtrade/user_data/data/binance \
  --strategy-path /freqtrade/user_data/strategies -c /freqtrade/user_data/configs/config_binance_multi.json \
  --data-format-ohlcv feather -s HmmSmaSlopeV2Short -i 4h \
  --fee 0.00035 --eps --max-open-trades 6 --timerange 20221101-20250101 --export trades

# Short-only, bear
docker run --rm -v "$(pwd)":/freqtrade/user_data algo-traders/freqtrade:hmmlearn-backtest3 \
  backtesting --datadir /freqtrade/user_data/data/hyperliquid \
  --strategy-path /freqtrade/user_data/strategies -c /freqtrade/user_data/configs/config_hl_multi.json \
  --data-format-ohlcv feather -s HmmSmaSlopeV2Short -i 4h \
  --fee 0.00035 --eps --max-open-trades 7 --timerange 20251015-20260509 --export trades

# Combined, bull
docker run --rm -v "$(pwd)":/freqtrade/user_data algo-traders/freqtrade:hmmlearn-backtest3 \
  backtesting --datadir /freqtrade/user_data/data/binance \
  --strategy-path /freqtrade/user_data/strategies -c /freqtrade/user_data/configs/config_binance_multi.json \
  --data-format-ohlcv feather -s HmmSmaSlopeV2LongShort -i 4h \
  --fee 0.00035 --eps --max-open-trades 6 --timerange 20221101-20250101 --export trades

# Combined, bear
docker run --rm -v "$(pwd)":/freqtrade/user_data algo-traders/freqtrade:hmmlearn-backtest3 \
  backtesting --datadir /freqtrade/user_data/data/hyperliquid \
  --strategy-path /freqtrade/user_data/strategies -c /freqtrade/user_data/configs/config_hl_multi.json \
  --data-format-ohlcv feather -s HmmSmaSlopeV2LongShort -i 4h \
  --fee 0.00035 --eps --max-open-trades 7 --timerange 20251015-20260509 --export trades
```

`algo-traders/freqtrade:hmmlearn-backtest3` is a local scratch image
(`freqtradeorg/freqtrade:2025.9` + hmmlearn + upgraded ccxt), built to work around
the infra issue documented below. It was not committed to the repo; rebuild via the
Dockerfile pattern in `execution/ops/Dockerfile.ext` if reproducing.

Archives: `analysis/backtests/hmm_sma_slope_v2short_binance_bull.zip`,
`…_v2short_hl_bear.zip`, `…_v2longshort_binance_bull.zip`, `…_v2longshort_hl_bear.zip`.

---

## Infra finding: `execution/ops/Dockerfile.ext` base image drift

Building the backtest image against `freqtradeorg/freqtrade:stable` failed: the tag
has drifted to Python 3.14, which has no prebuilt `hmmlearn` wheel. The from-source
build compiles without error but produces a `.so` with an undefined C++ ABI symbol,
which only surfaces at runtime as a silent `_HMM_AVAILABLE = False` inside the
strategy — not as a build failure. This affects the live deploy image too, since it
uses the same `FROM freqtradeorg/freqtrade:stable` line.

Fixed in `execution/ops/Dockerfile.ext`: pinned to
`freqtradeorg/freqtrade@sha256:55ed7118ab09fe1732bfb45f57ad19d1cd64f02180d53339324bbfe31982d1dd`
(the `2025.9` tag, Python 3.13, has a prebuilt hmmlearn wheel), upgraded `ccxt`
(2025.9's bundled version fails to load Hyperliquid markets — a spot-market entry
with a null base/quote crashes the parser), and added a build-time assertion
(`python -c "from hmmlearn.hmm import GaussianHMM"`) so any future base-image drift
fails `docker build` loudly instead of failing silently at deploy time. Verified the
updated Dockerfile builds clean.
