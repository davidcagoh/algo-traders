# live/

Productionization subproject. Two parallel tracks that share the same evaluation methodology but target different venues.

**Status:** scaffolding (2026-05-20). Pre-registration phase. No live capital, no signal generation yet.

> 🔴 **Live paper-trading tape:** watch Track B in real time at the deployed dashboard (see [`dashboard/`](dashboard/) for the URL once deployed). Read-only — no real capital, no auth.

## Why this exists

The `backtesting/` and `feishu/` subprojects produced two candidates that survive the project's own gates:

| Candidate | Origin | Gate passed | Gate failed |
|---|---|---|---|
| `trend_vol_v4` | feishu (A-shares) | DSR (signal, N=484, bounded kurt) | not yet held-out 2026-06→12 |
| `HmmSmaSlopeV2` | backtesting (HL BTC perps) | pre-registered kill criteria (bear MDD 4.44% < 5.5%) | DSR (kurtosis-dominated denominator) |

`trend_vol_v4` passed the stricter methodological gate but lives on a venue (Chinese A-shares) that's effectively inaccessible to retail outside mainland China. `HmmSmaSlopeV2` is on a venue (Hyperliquid) that anyone with a wallet can reach, but it hasn't cleared DSR.

This subproject pushes both forward:

- **Track A — `sgx_idx_trend_vol/`:** Port the `trend_vol_v4` *mechanism* (not its tuned params) to SGX + IDX equities. Question: does the methodology produce real alpha on a market we didn't tune on? Tests cross-venue generalisation, which is the strongest result the project can produce.
- **Track B — `hl_paper/`:** Run `HmmSmaSlopeV2` as a 30-day Freqtrade dry-run against live Hyperliquid prices. Question: does the strategy behave in deployment the way the backtest predicted? Tests execution realism, not alpha.

The two tracks are independent. Both must pre-register pass/fail criteria before any signal is generated.

## Layout

```
live/
├── eval/                       # 6-layer eval stack (ported from feishu/eval/)
├── tracks/
│   ├── sgx_idx_trend_vol/      # Track A
│   └── hl_paper/               # Track B
├── ops/                        # hosting, monitoring, Docker, GH Actions
└── dashboard/                  # public live-tape (Supabase + Vercel + sync sidecar)

wiki/live/                      # gates + results (lives in repo wiki/, not here)
├── decisions/                  # pre-registered gates (write before code)
└── results/                    # dated, immutable result files
```

## Promotion rule

Same as the root meta wiki. Facts that apply to **both** tracks get promoted to `wiki/live/learnings.md`. Track-specific findings stay in `tracks/<name>/notes.md`. Cross-project findings (applying to feishu and backtesting too) get promoted further to `../wiki/learnings.md`.

## Pre-registration discipline

Both tracks follow the methodology from `../wiki/methodology/kill-criteria.md` and `../wiki/methodology/cv-and-deflation.md`. Concretely:

1. Write the gate file in `wiki/live/decisions/` first.
2. Implement the strategy.
3. Run on tuning window.
4. Run on pre-registered held-out window without modification.
5. Apply gate. Result is binding regardless of whether it's the answer we wanted.

No iterating on the gate after seeing OOS results. If a gate retires a candidate, that's the gate working as designed.
