# Paper: A Six-Layer Evaluation Stack and a Portfolio-Aware Kill Criterion

Single-column LaTeX draft of the crypto-perp strategy-evaluation framework
paper. The contribution is the methodology (six-layer stack + portfolio-aware
K1 + continuous shrinkage), not the candidate book; the book is the worked
example.

## Build

```
make          # produces main.pdf via pdflatex -> bibtex -> pdflatex x2
make clean    # removes aux files
make distclean # also removes the PDF
```

Requires a standard TeX Live install (pdflatex + bibtex). No external image
files; all tables are inline TeX.

## Files

| File | Role |
|------|------|
| `main.tex` | Paper body, single-column `article` class. |
| `references.bib` | BibTeX entries: primary literature + per-result-card project artifacts. |
| `tables/leaderboard.tex` | Full common-window leaderboard, `\input{}`'d from `main.tex` §6. |
| `Makefile` | `make` / `make clean` targets. |

## Outstanding TODOs

These are explicit in the paper (§8 Threats to Validity, §9 Future Work):

1. **Forward held-out window 2026-06-01 → 2026-12-31.** Not downloaded;
   will not be touched until after submission. One-shot OOS gate.
2. **30-day live paper-trade dry-run** of the candidate book {T3, R∧T2}
   against decision-004 kill criteria, on Hyperliquid.
3. **Per-coin signed-funding learning** for the R∧C family.

Status of artifacts referenced in the bibliography: every `result_*` key in
`references.bib` points to a markdown card under
`../backtesting/wiki/results/`. These are the per-experiment evidence the
paper cites.
