# Quant Research Agent

Reusable workflow material for an autonomous quantitative-research loop.

- `PATTERN.md` documents the architecture, operating discipline, and failure modes.
- `paper-search-trigger.md` is the retained paper-search automation specification.
- `source-dives/` contains agent-produced thematic literature syntheses.

The agent reads shared knowledge from `../wiki/`, keeps primary material in
`../literature/sources/`, records thematic syntheses in `source-dives/`, and hands experiment-specific hypotheses to the relevant project.
It does not own experiment results, publication manuscripts, or primary-source PDFs.
