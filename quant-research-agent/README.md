# Quant Research Agent

Reusable workflow material for an autonomous quantitative-research loop.

- `PATTERN.md` documents the architecture, operating discipline, and failure modes.
- `paper-search-trigger.md` is the master prompt for the scheduled/manual
  `.github/workflows/paper-search.yml` workflow.
- `source-dives/` contains agent-produced thematic literature syntheses.

The agent reads shared knowledge from `../wiki/`, keeps primary material in
`../literature/sources/`, records thematic syntheses in `source-dives/`, and hands experiment-specific hypotheses to the relevant project.
It does not own experiment results, publication manuscripts, or primary-source PDFs.

The workflow uses the official OpenAI Codex Action, opens a pull request for
review, and requires an `OPENAI_API_KEY` repository secret. Without that secret, scheduled runs exit
without calling the agent.
