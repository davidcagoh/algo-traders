# Algo Traders — Meta Wiki

Cross-cutting workspace for the algorithmic-trading subprojects in this repo.

**Last updated:** 2026-06-01

## Subprojects

| Path | Domain | Wiki |
|------|--------|------|
| `backtesting/` | Hyperliquid BTC/USDC perps via Freqtrade | [`backtesting/wiki/_index.md`](../backtesting/wiki/_index.md) |
| `live/` | Hyperliquid 30d dry-run + cross-venue equity | [`live/wiki/_index.md`](../live/wiki/_index.md) |
| `feishu/` | Chinese A-share quant competition | gitignored — own repo |

`backtesting/` and `live/` are tracked in this repo (merged 2026-06-01). Their prior independent git histories are archived at `github.com/davidcagoh/backtesting` and `github.com/davidcagoh/algo-traders-live`. `feishu/` remains in its own repo — different market, different competition context.

## Promotion rule

A learning lives at root **only if it applies to both subprojects** (e.g., overfitting at scale, multi-objective design, deflation rules). Subproject-specific facts (Hyperliquid 5000-candle cap, Feishu vwap_0930_0935 execution) stay in the subproject wikis.

## Contents

- [PATTERN.md](../PATTERN.md) — original cross-project pattern observations (May 2026)
- [learnings.md](learnings.md) — confirmed cross-cutting facts, open questions, data-sourcing defaults
- Public-facing writeups (root):
  - `../writeup-2026-05-10.md` / `.pdf` — narrative essay on five-strategy ranking, Pareto frontier, DSR humility
  - `../writeup-2026-05-16.md` / `.pdf` — principled writeup, layered evaluation stack (L1–L6), candidate book {T3, R∧T2}
  - `../website-brief.md` — adapted-paper brief for the public site (essay + repo, not paper-shaped)
- Formal artifacts (root):
  - [`../paper/`](../paper/) — arXiv preprint, 14 pages single-column LaTeX; six-layer evaluation stack + portfolio-aware K1 as load-bearing contributions. Build: `cd paper && make`.
  - [`../essays/principled-strategy-evaluation-at-laptop-scale.md`](../essays/principled-strategy-evaluation-at-laptop-scale.md) — long-form practitioner essay, ~5000 words, five principles for laptop-scale strategy evaluation.
- `methodology/`
  - [multi-objective-search.md](methodology/multi-objective-search.md) — design draft for Pareto-front sweep over a bounded primitive grammar
  - [cv-and-deflation.md](methodology/cv-and-deflation.md) — CPCV protocol, DSR/PBO gates, pre-registration template
  - [kill-criteria.md](methodology/kill-criteria.md) — pre-registered retirement rules: four canonical axes, family-specific axis, Davies–Ravagnani continuous shrinkage, calibration discipline
  - [data-sourcing.md](methodology/data-sourcing.md) — default order: subproject downloader → ccxt → direct API → S3 → yfinance → scrapers
- `references/`
  - [divergence_portfolio_theory.md](references/divergence_portfolio_theory.md) — α-portfolio framing that motivates multi-objective search
- `ideas/` — parked ideas not yet attached to an experiment
  - [random-projection-stability.md](ideas/random-projection-stability.md) — sliced/projection-based stability tests for regime robustness; pull off shelf when the first Pareto front exists
- `../literature/` — shared paper library (PDFs)
