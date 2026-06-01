# live/ wiki

**Last updated:** 2026-05-29

Track A: cross-cycle falsification complete. Mechanism family parked. Track B: **30d dry-run IN PROGRESS** (day 8/30). Bot running on Hetzner VPS, 2 closed trades (both BTC, both losses), MDD 0.09%, trade count gate not yet met.

## Tracks

| Track | Venue | Strategy origin | Status |
|---|---|---|---|
| A | SGX + IDX + HSI equities | `trend_vol_v4` mechanism port | **PARKED — falsified by gate 006 cross-cycle** |
| B | Hyperliquid BTC + majors perps | `HmmSmaSlopeV2` from backtesting/ | **IN PROGRESS** — 30d dry-run started 2026-05-21, ends 2026-06-20 |

## Contents

- [learnings.md](learnings.md) — cross-track facts + promotions up
- `decisions/` — pre-registered gates, BINDING once written
  - [001-track-a-gate.md](decisions/001-track-a-gate.md) — Track A v1 (default trend_vol on SGX+IDX). Failed.
  - [002-track-b-gate.md](decisions/002-track-b-gate.md) — Track B 30d HL dry-run. **BINDING 2026-05-20.**
  - [004-track-a-hedged-mechanism.md](decisions/004-track-a-hedged-mechanism.md) — hedged variant. Passed on SGX held-out.
  - [006-cross-cycle-stress-test.md](decisions/006-cross-cycle-stress-test.md) — HSI cross-cycle stress. Falsified the SGX pass.
- `results/`
  - [2026-05-20-sgx-idx-baseline.md](results/2026-05-20-sgx-idx-baseline.md) — default params, gate 001 fail.
  - [2026-05-20-sanity-sweep.md](results/2026-05-20-sanity-sweep.md) — top_n × rebalance period sweep; turnover is the lever.
  - [2026-05-20-hedged-mechanism-tuning.md](results/2026-05-20-hedged-mechanism-tuning.md) — gate 004 tuning-window pass on SGX.
  - [2026-05-20-hedged-mechanism-heldout-BINDING.md](results/2026-05-20-hedged-mechanism-heldout-BINDING.md) — gate 004 held-out pass on SGX (bull regime).
  - [2026-05-20-cross-cycle-hsi-BINDING.md](results/2026-05-20-cross-cycle-hsi-BINDING.md) — gate 006 HSI cross-cycle **FAIL**. Parks the mechanism.
  - [2026-05-21-hl-paper-start.md](results/2026-05-21-hl-paper-start.md) — Track B 30d dry-run start. Clock starts 2026-05-21T04:44:24Z.
  - [2026-05-29-hl-paper-day8.md](results/2026-05-29-hl-paper-day8.md) — Day 8 snapshot. 2 closed trades, MDD 0.089%, trade count gate pending.

## Session 2026-05-20 net finding

No tradeable trend_vol-family equity strategy on SGX, IDX, or HSI. The 6-layer + pre-reg + cross-cycle protocol caught the regime-lucky SGX held-out pass that single-metric eyeballing would have graduated to paper-trade. Three cross-project methodology rules promoted up.

## Next actions

1. **[DONE] Track B 30d clock running.** Started 2026-05-21T04:44:24Z on Hetzner VPS (178.105.11.125). Bot healthy, 8 days in.
2. **[DONE] Live-tape dashboard deployed.** Sync sidecar installed on VPS (systemd timer, 30s), confirmed pushing to Supabase. Dashboard live at https://algo-traders-dashboard.vercel.app.
3. **Day 15 wiki update** (2026-06-05) — check trade count progress toward ≥5 gate minimum.
4. **Or: new equity mechanism family**, with same protocol. Park trend_vol; pull a different signal (e.g. residual reversal, short-term momentum, OFI-OU) from feishu/signals/, write its own pre-reg gate chain.

## References upward

- Parent meta wiki: [`../../wiki/_index.md`](../../wiki/_index.md)
- Cross-project learnings: [`../../wiki/learnings.md`](../../wiki/learnings.md)
- Kill criteria methodology: [`../../wiki/methodology/kill-criteria.md`](../../wiki/methodology/kill-criteria.md)
- CV and deflation methodology: [`../../wiki/methodology/cv-and-deflation.md`](../../wiki/methodology/cv-and-deflation.md)
