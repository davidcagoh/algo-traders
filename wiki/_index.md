# Algo Traders — Meta Wiki

Cross-cutting workspace for two algorithmic-trading subprojects that share methodology, literature, and lessons but live in their own GitHub repos.

**Last updated:** 2026-05-09

## Subprojects

| Path | Domain | GitHub remote | Wiki |
|------|--------|---------------|------|
| `backtesting/` | Hyperliquid BTC/USDC perps via Freqtrade | own repo | `backtesting/wiki/_index.md` |
| `feishu/` | Chinese A-share quant competition | own repo | `feishu/wiki/_index.md` |

Both subprojects are gitignored at this root — they retain independent history. This repo only tracks the meta-layer: literature, methodology, cross-cutting learnings.

## Promotion rule

A learning lives at root **only if it applies to both subprojects** (e.g., overfitting at scale, multi-objective design, deflation rules). Subproject-specific facts (Hyperliquid 5000-candle cap, Feishu vwap_0930_0935 execution) stay in the subproject wikis.

## Contents

- [PATTERN.md](../PATTERN.md) — original cross-project pattern observations (May 2026)
- [learnings.md](learnings.md) — confirmed cross-cutting facts, open questions, data-sourcing defaults
- `methodology/`
  - [multi-objective-search.md](methodology/multi-objective-search.md) — design draft for Pareto-front sweep over a bounded primitive grammar
  - [cv-and-deflation.md](methodology/cv-and-deflation.md) — CPCV protocol, DSR/PBO gates, pre-registration template
  - [data-sourcing.md](methodology/data-sourcing.md) — default order: subproject downloader → ccxt → direct API → S3 → yfinance → scrapers
- `references/`
  - [divergence_portfolio_theory.md](references/divergence_portfolio_theory.md) — α-portfolio framing that motivates multi-objective search
- `ideas/` — parked ideas not yet attached to an experiment
  - [random-projection-stability.md](ideas/random-projection-stability.md) — sliced/projection-based stability tests for regime robustness; pull off shelf when the first Pareto front exists
- `../literature/` — shared paper library (PDFs)
