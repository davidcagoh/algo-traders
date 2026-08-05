# monitoring/

Read-only paper-trading tape for the Hyperliquid bot. Three pieces:

```
monitoring/
├── sync/        # VPS sidecar — reads tradesv3.sqlite, pushes to Supabase
├── web/         # Next.js app — hosted on Vercel, reads from Supabase
└── README.md
```

Nothing in this directory touches Freqtrade or the gate. It's an observability
layer bolted onto an existing sqlite DB; if it breaks, it cannot affect the
bot's execution.

## Architecture

```
   VPS (existing)                  Supabase (free tier)        Vercel
   ┌──────────────────┐            ┌──────────────────┐        ┌──────────────┐
   │ docker-compose   │   sqlite   │ at_trades        │  REST  │ Next.js page │
   │  freqtrade       │ ─────────► │ at_equity_snaps  │ ◄───── │ (this repo)  │
   │  tradesv3.sqlite │            │ at_sync_state    │ realtime               │
   └──────────────────┘            └──────────────────┘        └──────────────┘
            ▲                              ▲
            │ read-only                    │ service_role write
            │                              │
   ┌──────────────────┐                    │
   │ systemd timer    │ ───────────────────┘
   │ sync.py (30s)    │
   └──────────────────┘
```

The sync sidecar is read-only against Freqtrade's SQLite (`mode=ro` URI) so it
cannot interfere with the writer. It posts deltas to Supabase using the
service-role key, which never leaves the VPS. The browser only ever sees the
publishable key, which by RLS can only `SELECT` from the `at_*` tables.

## Supabase

Already provisioned. Project `dad-trading-copilot` is shared; our tables are
all prefixed `at_` (algo-traders) and live in `public`:

- `at_trades` — one row per freqtrade trade, upserted on `trade_id`.
- `at_equity_snapshots` — append-only, ~one row per sync tick.
- `at_sync_state` — singleton row, heartbeat.

Schema migration: applied via Supabase MCP, name `algo_traders_move_to_public`.

## VPS deploy (sync sidecar)

On the VPS, from the repo root:

```sh
sudo cp freqtrade-experiment/hmm-slope-experiment/monitoring/sync/algo-traders-sync.env.example /etc/algo-traders-sync.env
sudo chmod 600 /etc/algo-traders-sync.env
sudo nano /etc/algo-traders-sync.env   # paste SUPABASE_SERVICE_KEY, fix paths
sudo bash freqtrade-experiment/hmm-slope-experiment/monitoring/sync/install.sh
```

Verify:

```sh
sudo systemctl status algo-traders-sync.timer
sudo journalctl -u algo-traders-sync.service -f
```

The service-role key is in Supabase dashboard → Project Settings → API → "Reveal
secret keys". Do **not** confuse it with the publishable key.

## Vercel deploy (web)

```sh
cd freqtrade-experiment/hmm-slope-experiment/monitoring/web
npx vercel link                # one-time
npx vercel env add NEXT_PUBLIC_SUPABASE_URL
npx vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY
npx vercel deploy --prod
```

Use the **publishable** key (`sb_publishable_…`), not the service role. Values
for both are in `web/.env.example`.

Local dev:

```sh
cd freqtrade-experiment/hmm-slope-experiment/monitoring/web
cp .env.example .env.local
npm install
npm run dev
```

## RLS posture

- `anon` / `authenticated` roles → `SELECT` only.
- No `INSERT`/`UPDATE`/`DELETE` policies → writes require `service_role`.
- The publishable key shipped to the browser cannot mutate anything even if
  exfiltrated.

## Cost

$0/mo on Supabase free tier (well under the 500MB / 50k MAU limits for this
workload — ~3000 rows/day at the current trade rate). Vercel hobby tier is also
free for a single static-ish page. No paid services introduced.

## Failure modes

| Failure | Effect on dashboard | Effect on bot |
|---|---|---|
| Sync timer dies | dashboard shows `stale` after 120s | none |
| Supabase outage | dashboard 5xx until SSR retry | none |
| VPS network out | dashboard goes stale | bot also can't trade (separate concern) |
| Freqtrade rotates db | sync errors, logged in journalctl | none |

The bot has its own healthcheck pipeline via `freqtrade-experiment/hmm-slope-experiment/execution/ops/healthcheck.sh` — this
dashboard is **not** an alerting surface. It exists for visitors, not operators.
