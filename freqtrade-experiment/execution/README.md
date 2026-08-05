# execution/ — paper execution

Paper-execution layer for the repository's single crypto-trading experiment.
Monitoring is in `../monitoring/`; research is in `../research/`.

**Status:** Hyperliquid paper execution stopped on 2026-08-05. No live capital
was used.

> 🔴 **Live paper-trading tape:** watch the Hyperliquid run at the deployed dashboard (see [`../monitoring/`](../monitoring/)). Read-only — no real capital, no auth.

## Why this exists

The active crypto candidate is produced by `../research/`:

| Candidate | Origin | Research status | Execution status |
|---|---|---|---|
| `HmmSmaSlopeV2` | `research/` (Hyperliquid perps) | Selected candidate; DSR remains inconclusive | Extended paper run stopped |

`HmmSmaSlopeV2` is on a venue (Hyperliquid) that anyone with a wallet can
reach, but it has not cleared DSR. The parked SGX/IDX/HSI implementation was
removed during cleanup; only its dated result records remain in
`../../wiki/artifacts/equity-trend-vol/results/`. New crypto candidates must still pre-register
pass/fail criteria before execution.

## Layout

```
execution/
├── config.json                 # Freqtrade runtime config
├── config.private.example.json # secret template; private file is ignored
├── ops/                        # hosting, Docker, healthchecks, snapshots
└── records/                    # pre-registered gates and dated results
```

## Promotion rule

Execution evidence stays in `records/`. Reusable operational patterns are
distilled into `../../wiki/`; cross-project findings go to
`../../wiki/learnings-archive.md`.

## Pre-registration discipline

The crypto experiment follows the methodology from `../../wiki/concepts/kill-criteria.md` and `../../wiki/concepts/cv-and-deflation.md`. Concretely:

1. Write the dated gate file in `records/decisions/` first.
2. Implement the strategy.
3. Run on tuning window.
4. Run on pre-registered held-out window without modification.
5. Apply gate. Result is binding regardless of whether it's the answer we wanted.

No iterating on the gate after seeing OOS results. If a gate retires a candidate, that's the gate working as designed.
