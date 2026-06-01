# Algo Traders

Hyperliquid BTC/majors perps strategy research, from backtesting to live deployment.

**Live paper-trading tape:** [algo-traders-dashboard.vercel.app](https://algo-traders-dashboard.vercel.app) — read-only, no real capital.

---

## Navigate to

### 1. Evaluation methodology
The project uses a six-layer evaluation stack with pre-registered kill criteria. No strategy advances without clearing every layer.

- **Stack design:** [`wiki/methodology/cv-and-deflation.md`](wiki/methodology/cv-and-deflation.md) — CPCV protocol, DSR/PBO gates, pre-registration template
- **Kill criteria:** [`wiki/methodology/kill-criteria.md`](wiki/methodology/kill-criteria.md) — four canonical axes, continuous shrinkage, calibration discipline
- **Per-strategy gates (binding):** [`backtesting/wiki/decisions/`](backtesting/wiki/decisions/) — one decision file per gate, written before results are looked at
- **Paper (14pp):** [`paper/`](paper/) — *A Six-Layer Evaluation Stack and a Portfolio-Aware Kill Criterion*. Build: `cd paper && make`.
- **Practitioner essay (~5000w):** [`essays/principled-strategy-evaluation-at-laptop-scale.md`](essays/principled-strategy-evaluation-at-laptop-scale.md)

### 2. Strategy catalog
Five strategies evaluated on Binance perp history 2020-09 → 2026-05 (5.5 years, 2 bull + 2 bear cycles, BTC/ETH/SOL/AVAX/DOGE).

- **Leaderboard + Pareto frontier:** [`backtesting/wiki/_index.md`](backtesting/wiki/_index.md)
- **Per-strategy report cards:** [`backtesting/wiki/results/`](backtesting/wiki/results/)
- **Candidate book:** {T3, R∧T2} = `SmaRegime180` (BTC, conservative) + `HmmSmaSlopeV2` (5-coin, high-return). Correlation 0.07, MDB-rp +0.55.
- **Strategy taxonomy:** [`backtesting/wiki/reference/strategy-taxonomy.md`](backtesting/wiki/reference/strategy-taxonomy.md) — every family built, with status tags (★/▲/~/✗)
- **Writeup (2026-05-16):** [`articles/principled-evaluation-worked-example.md`](articles/principled-evaluation-worked-example.md) — Pareto frontier + layered evaluation, narrative form

### 3. Deployment code
`HmmSmaSlopeV2` running as a Freqtrade dry-run against live Hyperliquid prices.

- **Strategy file:** [`backtesting/user_data/strategies/HmmSmaSlopeV2.py`](backtesting/user_data/strategies/HmmSmaSlopeV2.py)
- **Ops (Docker, VPS, systemd):** [`live/ops/`](live/ops/)
- **Dashboard (Next.js + Supabase → Vercel):** [`live/dashboard/`](live/dashboard/)
- **Sync sidecar (SQLite → Supabase, 30s):** [`live/dashboard/sync/`](live/dashboard/sync/)
- **Pre-registered gate:** [`wiki/live/decisions/002-track-b-gate.md`](wiki/live/decisions/002-track-b-gate.md) — binding pass/fail criteria, written before the clock started

---

## Status

| Track | What | Status |
|---|---|---|
| **B — Hyperliquid dry-run** | `HmmSmaSlopeV2`, 5-coin perps | **IN PROGRESS** — 30d clock started 2026-05-21, ends 2026-06-20 |
| A — SGX/IDX equities | `trend_vol_v4` mechanism port | **PARKED** — falsified by cross-cycle stress gate (HSI 2014-2024) |

Day 11/30. 2 closed trades (both BTC). MDD 0.089%. Trade count gate (≥5) not yet met.

---

## Layout

```
algo-traders/
├── backtesting/          ← Freqtrade strategy research (5 strategies, full eval stack)
│   ├── wiki/             ← decisions (pre-registered gates), results, leaderboard
│   └── user_data/        ← strategy files, data, backtest configs
├── live/                 ← production deployment
│   ├── dashboard/        ← Next.js frontend + Supabase sync sidecar
│   ├── ops/              ← Dockerfile, docker-compose, systemd units
│   └── tracks/           ← Track A (parked), Track B (active)
├── wiki/                 ← top-level wiki (methodology + cross-cutting + live track)
│   ├── methodology/      ← 6-layer eval stack, CPCV protocol, kill criteria design
│   └── live/             ← pre-registered gates + dry-run results for live/
├── articles/             ← narrative and technical writeups
├── paper/                ← arXiv preprint (LaTeX, 14pp)
├── essays/               ← long-form practitioner essay
└── literature/           ← shared paper library
```

---

## What's not here

`feishu/` — Chinese A-shares quant competition. Different market, different competition context, lives in its own repo. The `trend_vol_v4` mechanism that originated there is documented in `backtesting/wiki/` where it was evaluated.
