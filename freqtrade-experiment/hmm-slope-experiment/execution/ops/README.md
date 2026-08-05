# Track B ops layer

Hosting + monitoring for the 30d Hyperliquid dry-run pre-registered in
[`../records/decisions/002-track-b-gate.md`](../records/decisions/002-track-b-gate.md).

Three pieces, no more:

1. **Docker Compose** — Freqtrade container with `restart: unless-stopped`.
   The image is based on the upstream stable Freqtrade image and adds the
   experiment's Python dependency (`hmmlearn`).
2. **Telegram bot** — operator channel. Required by gate §Hosting for remote
   `/stop` and alert delivery.
3. **healthchecks.io heartbeat** — sidecar container pings every 5 minutes
   if Freqtrade's REST `/ping` answers. healthchecks.io alerts if pings stop.

The bot's own log file (`freqtrade.log`) is rotated by Freqtrade's built-in
rotation when launched with `--logfile`. Container stderr/stdout is rotated
by Docker's json-file driver (10 MB × 5 files).

## VPS prerequisites

Any small VPS works — the bot is ~1 vCPU, ~512 MB RAM idle, ~1 GB with model
fits running. Tested target: DigitalOcean / Hetzner basic droplet.

- Docker 24+ and Docker Compose plugin
- Outbound HTTPS to Hyperliquid (`api.hyperliquid.xyz`)
- Outbound HTTPS to Telegram (`api.telegram.org`)
- Outbound HTTPS to healthchecks.io
- ~5 GB free disk (logs + sqlite + downloaded OHLCV)

No inbound ports needed. The Freqtrade REST API is bound to `127.0.0.1` on the
host and only the sidecar healthcheck container reaches it via the compose
bridge network.

## Initial setup

```sh
# On the VPS, clone the monorepo (or rsync algo-traders/).
git clone <repo-url> algo-traders
cd algo-traders/freqtrade-experiment/hmm-slope-experiment/execution/ops

# 1. Telegram bot
#    - DM @BotFather, /newbot, save token.
#    - DM the new bot once.
#    - Visit https://api.telegram.org/bot<TOKEN>/getUpdates to read chat_id.

# 2. healthchecks.io
#    - Create a Cron-style check, period 5m, grace 5m.
#    - Copy the ping URL.

# 3. Generate API password + JWT secret
openssl rand -hex 16     # FT_API_PASSWORD
openssl rand -hex 32     # jwt_secret_key in config.private.json

# 4. Copy + edit secrets
cp .env.example .env
$EDITOR .env

cp ../config.private.example.json ../config.private.json
$EDITOR ../config.private.json

# 5. Build + start
docker compose --env-file .env build
docker compose --env-file .env up -d

# 6. Verify
docker compose logs -f freqtrade   # boot, pair subscribe, "Bot heartbeat"
docker compose ps                  # both containers Up
# Telegram should receive a startup message.
# healthchecks.io dashboard should turn green within 5 minutes.
```

## Gate-required observables (mapping)

| Gate criterion (decision 002) | How this layer satisfies it                          |
|--------------------------------|------------------------------------------------------|
| Uptime > 99% / 30d             | `restart: unless-stopped` + healthchecks.io alerts   |
| No silent failures             | json-file log rotation + freqtrade.log + Telegram    |
| Remote /stop                   | Telegram `/stop` → Freqtrade bot                     |
| Heartbeat                      | healthcheck container → healthchecks.io ping URL     |

## Stop / restart / inspect

```sh
docker compose --env-file .env down            # graceful 30s stop
docker compose --env-file .env restart freqtrade
docker compose logs --tail 200 freqtrade
docker compose exec freqtrade ls user_data/logs
```

Any code or config change inside a gate window invalidates the run. Restart the
clock and record the reason in `../records/results/`.

## What's deliberately not here

- **CI/CD.** This is a 30d single-deploy, not a service. No GH Actions.
- **Prometheus/Grafana.** healthchecks.io covers the only liveness signal the
  gate requires. Add metrics later only if the gate asks for them.
- **Multi-region failover.** Out of scope; a single VPS outage is allowed
  uptime budget (gate threshold is 99% over 30d ≈ 7h budget).
- **Backups.** sqlite trade DB lives in the repo-mounted volume; the host's
  own snapshot policy is enough for a dry-run.
