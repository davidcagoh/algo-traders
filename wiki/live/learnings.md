# live/ cross-track learnings

Cross-track facts go here. Currently empty — no results yet.

Promotion rule: a learning lives here only if it applies to **both** Track A (SGX+IDX equities) and Track B (Hyperliquid perps). Track-specific findings stay in `../tracks/<name>/notes.md`. Findings that apply to feishu and backtesting too get promoted further to `../../wiki/learnings.md`.

---

## Confirmed

- **No tradeable trend_vol-family equity strategy on SGX, IDX, or HSI (2026-05-20).** Across default params (gate 001 baseline), sanity-swept params (top5/top8 × weekly/monthly), and hedged variant (200d SMA on equal-weighted universe), no configuration passes all of: pre-registered gate 001 *or* gate 004 *and* the cross-cycle stress gate 006. The hedged variant passes 001 and 004 on SGX (tuning + bull-only held-out) but is falsified by gate 006 on HSI 2014-2024. Documented mechanism failure: selection layer is venue-sensitive (low-vol picks winners on A-shares/SGX, picks below-buy-and-hold on HSI). Mechanism family parked; new equity mechanism would require a new pre-reg gate chain.
- **The full 6-layer + pre-reg + cross-cycle protocol catches what eyeballing wouldn't.** Without gate 006, SGX hedged would have graduated to paper-trade based on the bull-regime held-out pass. The cross-cycle stress on HSI cost one extra backtest run and saved real money + 6+ months of wall-clock. Pattern is exportable to any future strategy in either track.
- **Track B deployment shape: wrapper repo + external upstream + extension Dockerfile (2026-05-21).** Final working layout: `davidcagoh/algo-traders-live` (this repo) holds ops + strategy harness; `davidcagoh/backtesting` holds the strategy file (`HmmSmaSlopeV2.py`) and wiki; `github.com/freqtrade/freqtrade` (gitignored under `backtesting/freqtrade/`) is cloned upstream during VPS bring-up. The Docker image is **not** built from the local Freqtrade source — it FROMs `freqtradeorg/freqtrade:stable` and an extension Dockerfile in `live/ops/Dockerfile.ext` adds `hmmlearn` + build-essential. Pin mechanism is image digest, snapshotted at clock start. Documented in `decisions/002` Resolved + Revised sections. Replicate this shape for any future strategy that needs deps outside Freqtrade core.
- **Public observability shape: read-only SQLite → Supabase → Vercel, decoupled from the bot (2026-05-22).** For exposing a paper-trading bot to public visitors without touching its hot path: a systemd timer (30s) on the VPS runs a Python sidecar that opens Freqtrade's `tradesv3.sqlite` with `mode=ro` (so it cannot interfere with the writer), upserts deltas to Supabase `public.at_*` tables via REST using the service-role key, and writes a heartbeat row. The Vercel-hosted Next.js page reads with the *publishable* key under RLS that only permits `SELECT`. The service key never leaves the VPS; the browser cannot mutate state even if the publishable key is exfiltrated. Cost $0 (Supabase free + Vercel hobby) and the observability layer can crash without affecting the bot. Replicate for any future deployed strategy. Code lives in `live/dashboard/`.

## Promoted up (in `../../wiki/learnings.md`)

The three findings above generalised to cross-project rules:
1. Held-out windows that don't span design regime → passing-but-uninformative gates.
2. Mechanism transplants are venue-sensitive at the SELECTION layer, not just the parameter layer.
3. Hedge layers can shift tail-risk shape rather than reduce tail risk.

---

- **Supabase legacy JWT keys deprecated; new `sb_secret_...` format required (2026-05-29).** On the `dad-trading-copilot` project, legacy `service_role` JWTs were auto-disabled 2026-05-09. The sync sidecar's `SUPABASE_SERVICE_KEY` must be the new secret key (format `sb_secret_...`, from Settings → API → Secret key) not the old JWT. The `Authorization: Bearer` header works identically — it's a drop-in at the env-var level. Publishable keys follow the same change (`sb_publishable_...`). Apply on any future strategy that uses this observability stack.
- **Gitignored `.env.infra` pattern for deployed-strategy infra references (2026-05-29).** When a strategy is live on a VPS, the infra facts needed to reconnect in a future session (IP, SSH user, healthchecks UUID, compose path, API credential pointer) have nowhere to live: they're not secrets (no `.env` pattern) and not code (not committed). Solution: `live/.env.infra`, gitignored, holds VPS_IP, VPS_PROVIDER, HEALTHCHECK_UUID, FT_API_USERNAME and a comment pointing to where the password lives. Create this file the moment a VPS is provisioned. Without it, the only recovery path is pasting panel screenshots.

## Parked ideas

- **FX-as-input v2 of Track A.** Adding FX channels to the trend_vol mechanism (local-curr-weakness as EM-outflow regime filter; export-vs-domestic cross-sectional sort à la Hau & Rey) is a documented-alpha extension. Deliberately deferred: spawning it before v1's held-out result is in would conflate "does the methodology generalise" with "does adding FX help." Spawn `tracks/sgx_idx_trend_vol/v2_with_fx/` and `decisions/003-track-a-v2-fx.md` only after v1 gate result is known. (2026-05-20)
- **DXY-as-regime for Track B.** Root wiki already notes DXY → BTC as a known regime signal. Not added to v1 of Track B because the dry-run is testing execution-realism of an existing strategy, not improving it. Park as a future `backtesting/` experiment. (2026-05-20)
