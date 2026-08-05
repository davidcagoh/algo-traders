# Signed MV Paper Dashboard for Vercel

Self-contained Vercel paper monitor for the signed mean-variance Hyperliquid portfolio.

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
cd freqtrade-experiment/monitoring/mean-variance-paper
npm install
npm run dev
```

Local `/api/tick` still requires `KV_REST_API_URL` and `KV_REST_API_TOKEN`.
