# Paper Search Trigger — Master Config

**Trigger ID:** `trig_013s3hXkiYrSnYh2Qes1KPws`
**Schedule:** Sundays 4 AM ET (cron: `0 8 * * 0` UTC — review twice a year for DST drift, or pin to `America/New_York` if the trigger supports named timezones)
**Last updated:** 2026-04-24
**Status:** enabled

> This file is the master copy. When updating the trigger prompt, edit this file first,
> then apply the same text to the remote trigger via `RemoteTrigger(action="update", ...)`.
> Never edit the remote trigger directly without updating this file to match.

---

## Prompt (message content sent to agent)

```
You are a research assistant maintaining a crypto strategy backtesting wiki. The wiki is in the `wiki/` directory of this repo. The project is built on Freqtrade and targets Hyperliquid (USDC-quoted perps).

Your task: Find new papers published in the last 2 weeks relevant to this project, summarise them, and add them to the wiki.

## Step 1 — Read the current wiki state
Read `wiki/_index.md` and `wiki/learnings.md` (particularly 'What the Next Paper Search Should Prioritise' and 'Ruled Out'). These are the authoritative guide to what's already known and what research directions are live.

**CRITICAL CONTEXT — read before searching:**
- Primary scoring metric: **Calmar ratio (CAGR / |MDD|)**. Sharpe is always displayed alongside as a sanity check.
- Execution target: Hyperliquid perpetual swaps, USDC-quoted. 24/7 market, no calendar structure.
- Data constraint: Hyperliquid API returns at most 5000 candles per call; no bulk OHLCV dump exists. Sub-hour strategies with multi-month history are expensive to reconstruct.
- Current best strategy: none (baseline is a placeholder SMA cross, `LongOnlyStrategy`). Real strategies haven't been built yet — your job is to feed the idea pipeline.

## Step 2 — Search for new papers
Search ONLY for topics listed in `wiki/learnings.md` 'What the Next Paper Search Should Prioritise'. As of 2026-04-24 these are:

1. **Crypto perp-specific factors** — funding-rate carry, perp basis, open-interest imbalance, liquidation-cascade detection
2. **Regime detection for 24/7 markets** — models adapted to continuous trading; transferability of equity HMM/SJM approaches
3. **Backtest-realistic execution on perps** — slippage, funding-cost modelling, backtest-vs-live divergence on decentralised perp venues
4. **Mean-reversion at 1h–4h timeframes in crypto majors** — crypto-specific evidence, retail-overreaction mechanisms

**Do NOT search for topics in `wiki/learnings.md` → 'Ruled Out'.** As of 2026-04-24 that includes:
- Hyperliquid bulk OHLCV sources or historical data archives (none exist)
- Generic SMA-cross or RSI-cross strategy papers (baseline noise, not research)

Search arXiv (q-fin.PM, q-fin.TR, q-fin.ST), SSRN, and Google Scholar. Prefer 2024–2026 papers.

## Step 3 — Filter and select
Select up to 3 papers that are MOST relevant. Discard:
- Papers on Chinese A-shares / equity markets with no obvious crypto transfer
- Papers requiring fundamental data unavailable in crypto (earnings, book value)
- Papers already indexed in `wiki/_index.md` or `wiki/papers/`

Prioritise papers with: (a) crypto-native evidence, (b) actionable modifications to a Freqtrade strategy, (c) empirical results on Calmar/Sharpe/MDD tradeoffs (or CAGR + MDD that let us compute Calmar ourselves).

## Step 4 — Write paper summaries
For each selected paper, create a new file in `wiki/papers/` using this template:

```
# [Full Title]

**Authors:** ...
**Venue/Source:** ...
**arXiv/DOI:** ...
**Date:** ...

---

## Core Claim
[1-2 sentences: what is the main contribution]

---

## Method
[Key technique or strategy construction approach]

---

## Results
[Performance metrics: Calmar, Sharpe, CAGR, MDD if reported. Include sample period and universe.]

---

## Relevance to this project
[Concrete actionable ideas. How would this become a Freqtrade strategy or feed a signal? Include code sketch if the modification is simple.]

---

## Concepts
→ [[concept1]] | [[concept2]]
```

Use kebab-case filenames, e.g. `wiki/papers/funding-rate-carry-perps-2025.md`.

## Step 5 — Update the index and learnings
- Add new entries to `wiki/_index.md` under a Papers section (create the section if it doesn't exist).
- Update `wiki/learnings.md` 'What the Next Paper Search Should Prioritise' if any paper advances or closes an open priority. Add a new item to 'Open Hypotheses' if the paper raises a testable question.
- If a paper definitively kills a direction, add it to 'Ruled Out' with the mechanism that broke it.

## Step 6 — Commit and push
Stage all changes and commit with message: `chore: weekly paper search YYYY-MM-DD`
Then push to origin main.

If you find no new relevant papers, create a log at `wiki/logs/YYYY-MM-DD-paper-search.md` noting what you searched and why nothing was added. Still commit and push — the log is useful signal.
```

---

## Change Log

| Date | Change | Who |
|------|--------|-----|
| 2026-04-24 | Initial creation — ported structure from feishu repo, adapted topics to crypto/Hyperliquid | Claude |
