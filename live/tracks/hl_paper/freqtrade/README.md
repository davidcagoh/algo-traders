# Track B — Freqtrade harness (Hyperliquid 30d dry-run)

Pre-registered under `live/wiki/decisions/002-track-b-gate.md` (BINDING 2026-05-20).
This directory holds only the dry-run **config and run scripts**. Strategy code and the
Freqtrade install are imported from `../../../backtesting/` to avoid drift; the gate
explicitly requires "same strategy, same code" as the backtest.

## Version pins (locked by gate 002)

- **Freqtrade:** in-repo editable clone at `../../../backtesting/freqtrade/`
  - version: `2026.4-dev`
  - commit: `9d0fb9b0257dad05f19c153d624f74e0ac931647`
  - upstream: `https://github.com/freqtrade/freqtrade.git`

  **VPS deploy note.** The Freqtrade source is *not* tracked in the
  `davidcagoh/backtesting` repo (gitignored — it's hundreds of MB of upstream
  code). On a fresh VPS clone, materialise it before running `setup.sh`:

  ```sh
  cd ~/algo-traders/backtesting
  git clone https://github.com/freqtrade/freqtrade.git
  cd freqtrade && git checkout 9d0fb9b0257dad05f19c153d624f74e0ac931647
  ```
- **Strategy:** `HmmSmaSlopeV2` at
  `../../../backtesting/user_data/strategies/HmmSmaSlopeV2.py`
- **Hyperliquid CCXT adapter:** `freqtrade/exchange/hyperliquid.py` in the pinned clone.

Do not `pip install -U freqtrade` or pull the backtesting submodule during the 30d
window. Parameter or strategy edits invalidate the run; restart the 30d clock.

## What this is

- `dry_run=true` against **Hyperliquid mainnet** (real prices, real order book,
  simulated fills locally). Testnet is rejected by gate 002 — thin liquidity would
  break the slippage-realism criterion.
- 6 perp pairs, USDC quote: BTC, ETH, SOL, DOGE, AVAX, ARB (matches the
  cross-cycle CEX backtest universe in `backtesting/wiki/learnings.md` H3
  bull-window run).
- Wallet $1000 simulated, $200 per pair max — same economics as the backtest
  config `backtesting/user_data/config_hl_multi.json`.
- Timeframe 4h, set by the strategy class (`HmmSmaSlopeV2.timeframe`).

## Run command (local smoke test)

From repo root, with the backtesting venv:

```sh
./backtesting/freqtrade/.venv/bin/freqtrade trade \
  --config        live/tracks/hl_paper/freqtrade/config.json \
  --strategy      HmmSmaSlopeV2 \
  --strategy-path backtesting/user_data/strategies \
  --userdir       live/tracks/hl_paper/freqtrade \
  --logfile       live/tracks/hl_paper/dryrun/freqtrade.log
```

Wallet/API-key fields in `config.json.exchange` are empty on purpose — dry-run
does not place orders. Public market data only.

## Gate-checked observables (see decisions/002)

| Observable                | Where to read it                                   |
|---------------------------|----------------------------------------------------|
| Uptime / heartbeat        | healthchecks.io ping + `freqtrade.log` gaps        |
| Signal fidelity vs BT     | compare dry-run entries to a same-window backtest  |
| Slippage realism          | dry-run fill price vs `entry_pricing` quote        |
| MDD                       | `freqtrade show_trades` + dryrun wallet curve      |
| Trade count               | `freqtrade show_trades`                            |
| Funding-rate net          | per-pair funding ledger (Hyperliquid API)          |
| Unhandled exceptions      | `freqtrade.log` grep                               |

## Layout

```
live/tracks/hl_paper/
├── freqtrade/
│   ├── config.json          # this directory
│   ├── README.md            # this file
│   └── user_data/           # created at first run (data/, logs/)
└── dryrun/
    └── freqtrade.log        # rotated logs
```

## Next

1. ~~Smoke test.~~ **Done 2026-05-20.** Boot → analysis → idle in ~30s on the
   pinned venv, 6 pairs subscribed, `Bot heartbeat … state='RUNNING'`,
   zero ERROR/Traceback. Only warnings were `hmmlearn` non-convergence
   (expected, same as backtest).
2. ~~Wire ops layer.~~ **Done 2026-05-20.** See `../../../ops/README.md` —
   Docker Compose builds from pinned commit `9d0fb9b`, Telegram + healthchecks.io
   sidecar.
3. Start 30d clock. Record start timestamp + initial Hyperliquid funding rates +
   the dominant regime (bull / chop / bear) in a new
   `live/wiki/results/2026-MM-DD-hl-paper-start.md`.
