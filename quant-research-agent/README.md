# Quant Research Agent

Reusable workflow material for an autonomous quantitative-research loop.

- `PATTERN.md` documents the architecture, operating discipline, and failure modes.
- `paper-search-trigger.md` is the master prompt for the scheduled/manual
  `.github/workflows/paper-search.yml` workflow.
- [`../literature/search-config.yml`](../literature/search-config.yml) defines
  independent search threads, budgets, exclusions, and bounded keyword refinement.

The agent reads shared state from `../wiki/`, then writes PDFs, paper notes,
indexes, and search history under `../literature/`. It does not own literature,
experiment results, publication manuscripts, or durable wiki claims.

The workflow uses the official OpenAI Codex Action, opens a pull request for
review. Each enabled thread is searched on every run; new notes remain drafts
until reviewed. The workflow requires an `OPENAI_API_KEY` repository secret and
exits without calling the agent when it is absent.
