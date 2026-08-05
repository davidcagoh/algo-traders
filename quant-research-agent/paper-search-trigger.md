# Paper Search Trigger — Master Config

**Former trigger ID:** `trig_013s3hXkiYrSnYh2Qes1KPws` (retired Claude remote trigger)
**Schedule:** Sundays 4 AM America/Toronto
**Workflow:** `.github/workflows/paper-search.yml`
**Last updated:** 2026-08-05
**Status:** enabled; `OPENAI_API_KEY` repository secret configured 2026-08-05

> This file is the master prompt. The GitHub Action reads it at runtime; do not
> duplicate the full prompt in the workflow.

---

## Prompt (message content sent to agent)

```
You are a research assistant maintaining a crypto strategy backtesting wiki. The wiki is in the `wiki/` directory of this repo. The project is built on Freqtrade and targets Hyperliquid (USDC-quoted perps).

Your task: Find new papers published in the last 2 weeks relevant to this project, summarise them, and add them to the wiki.

## Step 1 — Read the current wiki state
Read `wiki/_index.md`, `wiki/open-threads.md`, and grep `wiki/learnings-archive.md` for related confirmed or ruled-out findings. These are the authoritative guides to what is active and already known.

**CRITICAL CONTEXT — read before searching:**
- Primary scoring metric: **Calmar ratio (CAGR / |MDD|)**. Sharpe is always displayed alongside as a sanity check.
- Execution target: Hyperliquid perpetual swaps, USDC-quoted. 24/7 market, no calendar structure.
- Data constraint: Hyperliquid API returns at most 5000 candles per call; no bulk OHLCV dump exists. Sub-hour strategies with multi-month history are expensive to reconstruct.
- Current state: the Freqtrade paper run is stopped and parked after failing its live gate. New papers should feed a genuinely new, pre-registered experiment rather than tune the parked strategy.

## Step 2 — Search for new papers
Search ONLY for topics that advance an item in `wiki/open-threads.md`. The retained crypto priorities are:

1. **Crypto perp-specific factors** — funding-rate carry, perp basis, open-interest imbalance, liquidation-cascade detection
2. **Regime detection for 24/7 markets** — models adapted to continuous trading; transferability of equity HMM/SJM approaches
3. **Backtest-realistic execution on perps** — slippage, funding-cost modelling, backtest-vs-live divergence on decentralised perp venues
4. **Mean-reversion at 1h–4h timeframes in crypto majors** — crypto-specific evidence, retail-overreaction mechanisms

**Do NOT search for directions recorded as ruled out in `wiki/learnings-archive.md`.** This includes:
- Hyperliquid bulk OHLCV sources or historical data archives (none exist)
- Generic SMA-cross or RSI-cross strategy papers (baseline noise, not research)

Search arXiv (q-fin.PM, q-fin.TR, q-fin.ST), SSRN, and Google Scholar. Prefer 2024–2026 papers.

## Step 3 — Filter and select
Select up to 3 papers that are MOST relevant. Discard:
- Papers on Chinese A-shares / equity markets with no obvious crypto transfer
- Papers requiring fundamental data unavailable in crypto (earnings, book value)
- Papers already indexed in `wiki/_index.md` or `quant-research-agent/source-dives/`

Prioritise papers with: (a) crypto-native evidence, (b) actionable modifications to a Freqtrade strategy, (c) empirical results on Calmar/Sharpe/MDD tradeoffs (or CAGR + MDD that let us compute Calmar ourselves).

## Step 4 — Write paper summaries
For each selected paper, create a new file in `quant-research-agent/source-dives/` using this template:

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

Use kebab-case filenames, e.g. `quant-research-agent/source-dives/funding-rate-carry-perps-2025.md`.

## Step 5 — Update the H3L wiki
- Add a reusable synthesis to `wiki/concepts/` only when the paper supports a durable concept beyond its source dive; inventory it in `wiki/_index.md`.
- Update `wiki/open-threads.md` when a paper advances, closes, or raises an actionable question.
- Append a confirmed or ruled-out finding to `wiki/learnings-archive.md` when evidence warrants it; include the mechanism and source-dive path.

## Step 6 — Open a reviewable pull request
The GitHub workflow creates or updates
`research/weekly-paper-search-YYYY-MM-DD`, stages only the documented knowledge
paths, and commits with message `chore: weekly paper search YYYY-MM-DD`.

Push that branch and open one pull request targeting `main`. Never push generated
research directly to `main`. If a pull request for the same dated branch already
exists, update that branch rather than opening a duplicate.

If you find no new relevant papers, add a short dated entry to `wiki/session-log.md` noting what you searched and why nothing was added. Still commit and push — the log is useful signal.
```

---

## Change Log

| Date | Change | Who |
|------|--------|-----|
| 2026-08-05 | Replaced retired remote trigger with scheduled/manual OpenAI Codex Action and PR review gate | Codex |
| 2026-08-05 | Updated paths and write targets for the H3L wiki structure | Codex |
| 2026-04-24 | Initial creation — ported structure from feishu repo, adapted topics to crypto/Hyperliquid | Claude |
