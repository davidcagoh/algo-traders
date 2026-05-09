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
- [learnings.md](learnings.md) — confirmed cross-cutting facts and open questions
- `methodology/` — reusable experiment-design protocols (CV, deflation, multi-objective search)
- `references/` — theoretical frames that inform methodology (e.g., divergence portfolio theory)
- `../literature/` — shared paper library (PDFs)
