# Crypto Trading Experiment

This repository is one Hyperliquid crypto-perpetuals experiment. The code is
organised by function rather than by separate projects:

| Area | Path | Role |
|---|---|---|
| Research | `research/` | Data, strategy variants, backtests, validation, selection |
| Execution | `execution/` and `execution/ops/` | Freqtrade configuration, Docker, and VPS deployment |
| Monitoring | `monitoring/` and `execution/ops/healthcheck.sh` | Read-only tape, liveness, and operator alerts |
| Collaborator paper project | `mean-variance-paper/` | Signed mean-variance local/Vercel paper monitor; separate from the live-deployment monitor |
| Evaluation | `../evaluation/`, `research/analysis/`, `../wiki/` | Shared metrics, experiment adapters, reports, and cross-cutting records |

The active strategy is `HmmSmaSlopeV2`, a long-only Hyperliquid perpetuals
strategy imported from `research/strategies/`.

## Run status

The pre-registered 30-day dry-run began at `2026-05-21T04:44:24Z` and ended at
`2026-06-20T04:44:24Z`. The bot continued running after that deadline, so the
post-day-30 observations were an extension of the experiment, not part of the
original 30-day gate. It was stopped on 2026-08-05.

Last verified from the Hetzner deployment on `2026-08-05T02:52Z`:

- Freqtrade and the healthcheck container were running and emitting heartbeats
  at the final pre-shutdown check.
- The trade database covered `2026-05-21` through `2026-08-05`.
- There were 22 trades: 21 closed and 1 open.
- Realized closed P/L was approximately `-35.40 USDC`.

## Final evaluation

The original 30-day gate was **incomplete**: only two round trips closed versus
the required five. The bot then continued without a pre-registered extension.
Across the full observed run, 21 trades closed for **-35.40 USDC (-3.54%)**, the
win rate was **4.8%**, and the maximum losing streak was **11 trades**. That
breaches the strategy's existing six-consecutive-loss kill rule.

The shared evaluation stack measured full-run Sharpe **-5.54**, Calmar
**-4.49**, SQN **-7.03**, and realized-balance MDD **3.51%**. DSR was **0.001**
but is non-binding with only 76 daily observations. Portfolio MDB was not
available because no comparison strategy ran concurrently.

**Final verdict: stopped, do not graduate to live capital, strategy parked.**
See the [full evaluation](execution/records/results/2026-08-05-hl-paper-evaluation.md)
and [shutdown record](execution/records/results/2026-08-05-hl-paper-shutdown.md).

The local repository has been refactored to the layout above. The VPS paper bot
was stopped cleanly on 2026-08-05; its database and logs were retained.

## Scope boundary

The SGX/IDX/HSI `trend_vol` source was removed as unrelated parked code. Its
dated results remain in `../wiki/artifacts/equity-trend-vol/results/` as historical evidence. The
Freqtrade source checkout is not retained; recreate a local environment from
the official distribution only if another backtest is needed.

## Later portfolio research

Concurrent June research explored Hyperliquid mean-variance portfolios after
the original strategy selection. A short-window signed variant reported
**+122.61% return, 3.86 Sharpe, 35.97 Calmar, and 17.23% maximum drawdown**;
the PC-neutral variant failed after fees. These results are retained as
research, not as a replacement for the stopped live experiment's verdict.
The signed result needs cross-cycle validation, and this repository does not
assert that its paper dashboard was deployed.
