# Shared Literature Index

Authoritative top-level manifest for cross-project literature. The scheduled
search agent reads this file to route discoveries and deduplicate across
collections. Directory conventions belong in [`README.md`](README.md).

## Collections

| Collection | Scope | Detailed manifest |
|---|---|---|
| [`crypto-markets/`](crypto-markets/) | Crypto perpetuals, funding and carry, regimes, microstructure, execution, and backtest portability. PDFs and notes are flat and stable-ID-first. | [`crypto-markets/_index.md`](crypto-markets/_index.md) |
| [`strategy-evaluation/`](strategy-evaluation/) | Validation methods, execution-risk audits, foundational inference, and surveys. | [`strategy-evaluation/_index.md`](strategy-evaluation/_index.md) |
| [`ai-methods/`](ai-methods/) | Agent and machine-learning methods with cross-cutting research relevance. | Sources listed below |
| [`quant-trading/`](quant-trading/) | Broad practitioner context that is not evidence for one experiment. | Sources listed below |

## Quant trading

| Source | Local copy | Role |
|---|---|---|
| Lauren Leek, *How Hard Can Quant Trading Really Be? I Tried It to Find Out* (2026) | [PDF](quant-trading/2026-leek-how-hard-can-quant-trading-really-be.pdf) | Practitioner narrative that motivated the original trading experiment; not peer-reviewed evidence. |

## AI methods

| Source | Local copy | Used for |
|---|---|---|
| Tajwar et al., *Maximum Likelihood Reinforcement Learning* (2026), arXiv:2602.02710 | [PDF](ai-methods/2602.02710-maximum-likelihood-reinforcement-learning.pdf) | Cross-cutting RL method; not specifically a trading paper. |
| Simhi et al., *Old Habits Die Hard: How Conversational History Geometrically Traps LLMs* (2026), arXiv:2603.03308 | [PDF](ai-methods/2603.03308-history-echoes.pdf) | Mechanistic support for avoiding path-dependent strategy ideation loops. |
| Maes et al., *LeWorldModel* (2026), arXiv:2603.19312 | [PDF](ai-methods/2603.19312-leworldmodel.pdf) | Source for random-projection stability and anti-collapse concepts. |

## Search controls

- [`search-config.yml`](search-config.yml) defines the six recurring search
  threads, budgets, exclusions, and adaptive-keyword policy.
- [`search-log.md`](search-log.md) records exact queries, screening outcomes,
  access failures, and keyword proposals for every run.
- [`../quant-research-agent/paper-search-trigger.md`](../quant-research-agent/paper-search-trigger.md)
  defines unattended operating rules. New interpretive notes remain drafts
  until reviewed; durable synthesis is promoted separately to the wiki.

## Inventory rules

- Every selected source must appear here or in a linked collection manifest.
- Record inaccessible or paywalled papers with a canonical URL and access
  status; lack of a local PDF is not a reason to lose the citation.
- Validate local PDFs with file type, PDF metadata, and first-page text checks.
- Do not duplicate a PDF across collections; link to its owning copy.
- Source notes describe evidence and limitations but are not durable wiki facts.

Last reconciled: 2026-08-05.
