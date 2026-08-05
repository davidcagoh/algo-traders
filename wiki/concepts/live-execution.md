# Live execution and monitoring patterns

Reusable operational lessons distilled from the Hyperliquid paper run.

## Deployment shape

Keep the strategy and deployment wrapper in the experiment repository while
using a pinned upstream runtime image. Add only the dependencies the strategy
needs in a thin extension image. Record the resulting image digest at the
start of a pre-registered run and do not rebuild during the gate window.

## Read-only observability

The paper run used a read-only SQLite connection, a periodic sync process,
Supabase tables protected by read-only browser policies, and a Vercel
dashboard. The monitoring path could fail without affecting order execution.
Service credentials remained on the VPS; the browser received only a
publishable key.

## Infrastructure references

Store non-committed deployment coordinates in a gitignored `.env.infra` file
as soon as a VPS is provisioned. Include the host, provider, healthcheck ID,
API username, and pointers to credentials without committing secrets.

## Source evidence

The concrete gate and dated records live in
`freqtrade-experiment/hmm-slope-experiment/execution/records/`.
