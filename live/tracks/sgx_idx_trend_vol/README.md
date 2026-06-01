# Track A — SGX + IDX trend_vol mechanism port

**Status:** modules written, backtest harness pending review (2026-05-20).

## What this is

A venue-agnostic port of feishu's `trend_vol_v4` mechanism, run on SGX +
IDX daily equities to test cross-venue generalisation of the methodology.

See `../../wiki/decisions/001-track-a-gate.md` for the pre-registered
gate (binding on held-out 2023-2026 window; must be applied without
modification after tuning).

## Files

| File | Purpose |
|---|---|
| `universe.py` | STI 30 + SGX mid-caps (`.SI`) and LQ45 (`.JK`) ticker lists |
| `fetch.py` | yfinance pull + per-ticker parquet cache + panel builder |
| `strategy.py` | The five-ingredient mechanism: low-vol rank → liq filter → regime gate → trend filter → inverse-vol weights |
| `backtest.py` | (not yet written) panel rebalance simulator |
| `data/<market>/*.parquet` | Cached per-ticker OHLC (gitignored via root `.gitignore`) |

## Mechanism (port fidelity)

Defaults in `TrendVolParams` match feishu's `trend_vol_v4` exactly:

| Param | Default | Source |
|---|---:|---|
| `vol_window` | 60 | `low_vol.py` |
| `liq_window` | 20 | `low_vol.py` |
| `liq_exclude` | 0.05 | `low_vol.py` |
| `regime_window` | 30 | `vol_managed_v2.py` |
| `sigma_threshold` | 2.0 | `vol_managed_v2.py` |
| `trend_window` | 35 | `trend_vol_v4.py` |
| `trend_threshold` | -0.025 | `trend_vol_v4.py` |
| `top_n` | 20 | `vol_managed_v2.py` |
| `weight_window` | 60 | `erc_vol_managed.py` |

These are the mechanism's defaults. Per the gate doc, tuning happens on
SGX/IDX data using CPCV — the feishu params are the *starting point* for
the search, not a transplant.

## Next steps

1. Write `backtest.py` — panel rebalance simulator that consumes the
   `weights` DataFrame and produces per-day wallet curves per market.
2. Pull data: `python -c "from live.tracks.sgx_idx_trend_vol.fetch import build_panels; build_panels('sgx'); build_panels('idx')"`.
3. Sanity-check the mechanism on default params before any tuning. If it
   produces patently broken curves (e.g. all-NaN selection, no trades),
   debug before opening the CPCV harness.
4. CPCV tuning on 2014-2022 — write a separate `tune.py` once 1–3 work.
5. **Held-out 2023-2026 stays sealed** until tuning is locked.

## Acceptance criteria for the mechanism port

Before any tuning runs:
- [ ] Data fetches for ≥80% of universe tickers per market
- [ ] `selection()` produces non-empty rows on at least 70% of trading days
- [ ] Regime gate fires on a non-trivial fraction (5–25%) of days in 2014-2022
- [ ] Trend filter excludes more stocks in 2015 (SGX correction) and 2020 (COVID) than in 2017 (calm)
- [ ] `weights()` rows sum to 1.0 (or are all-NaN) within float tolerance
