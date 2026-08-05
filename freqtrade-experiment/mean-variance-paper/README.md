# Signed Mean-Variance Paper Project

Collaborator-owned research, strategy, results, and paper-monitor implementation
for the signed mean-variance Hyperliquid portfolio.

This is a collaborator-owned research side project. It is intentionally kept
beside `hmm-slope-experiment/`; it is not part of that project's
stopped Freqtrade live-deployment monitor.

## Research state

The short 2026 window produced a promising signed result: +122.61% return,
3.86 Sharpe, 35.97 Calmar, and 17.23% maximum drawdown. It remains a research
candidate until it survives cross-cycle validation. The PC-neutral alternative
was sparse or negative after fees and is parked.

- [`LEARNINGS.md`](LEARNINGS.md) — detailed findings and caveats.
- [`analysis/`](analysis/) — universe selection, baselines, parameter sweeps,
  signed-funding evaluation, and PC-neutral alternatives.
- [`analysis/results/`](analysis/results/) — decisions, result cards, JSON, and charts.
- [`strategies/`](strategies/) and [`configs/`](configs/) — Freqtrade strategy and universe configuration.
- `app/`, `lib/`, and `local_dashboard.py` — paper-only monitoring implementations.

The code reads shared market data from `../hmm-slope-experiment/research/data/`
and uses the ignored Freqtrade environment at
`../hmm-slope-experiment/research/.venv/`. It does not own the original
strategy-selection or live-deployment monitor.

Vercel cannot run a permanent process, so the app uses Vercel Cron instead:

- `/api/tick` runs hourly from `vercel.json`.
- It fetches Hyperliquid mids, candles, and funding.
- It simulates paper positions, fees, funding, equity, and weekly rebalances.
- State is stored in Upstash/Vercel KV.
- `/api/status` serves the dashboard.

## Deploy

1. Create an Upstash Redis database or add Vercel KV/Upstash Redis to the Vercel project.
   Vercel Hobby cron is daily-only; the included hourly `vercel.json` schedule requires a plan that supports hourly cron.
2. Set env vars in Vercel:

```bash
KV_REST_API_URL=...
KV_REST_API_TOKEN=...
CRON_SECRET=<random-secret>
```

Raw Upstash names also work:

```bash
UPSTASH_REDIS_REST_URL=...
UPSTASH_REDIS_REST_TOKEN=...
CRON_SECRET=<random-secret>
```

3. Deploy this folder as the Vercel project root:

```bash
npm install
npm run build
vercel --prod
```

4. Initialize immediately instead of waiting for the next hourly cron:

```bash
curl -H "Authorization: Bearer <CRON_SECRET>" \
  "https://<your-vercel-domain>/api/tick?force=1"
```

## Local Development

```bash
cd freqtrade-experiment/mean-variance-paper
npm install
npm run dev
```

Local `/api/tick` still requires `KV_REST_API_URL` and `KV_REST_API_TOKEN`.
