# Trading-Strategy Evaluation Literature

Authoritative manifest for the evaluation-framework literature corpus. A source
is recorded even when no legal local PDF could be retrieved.

## Scope and protocol

- Question: which methods make backtest selection and trading-strategy
  evaluation more resistant to leakage, multiple testing, dependence, regime
  selection, execution costs, and backtest-to-live decay?
- Coverage: foundational work plus relevant 2024–2026 research, searched through
  2026-08-05.
- Discovery: existing `literature/crypto-markets/` notes, arXiv, SSRN, NBER,
  publisher DOI pages, and citation chaining from included papers.
- Inclusion: primary methods, empirical validation studies, and surveys that
  materially describe evaluation practice. Strategy papers are included only
  when their validation or execution protocol is reusable.
- Exclusion: papers reporting only headline Sharpe/return, inaccessible sources
  that could not be identified reliably, and duplicate versions.
- PDF validation: every local PDF passed `file`, `pdfinfo`, and first-page text
  extraction checks. Local copies come from arXiv, NBER, or author-hosted pages.

### Access status

- **Local PDF** — validated file in this repository.
- **Record only: fetch failed** — identifiable open paper, but automated download
  failed (for example SSRN 403).
- **Record only: paywalled** — bibliographic record is available but no legal
  open PDF was confirmed.

## Current methods

| Year | Source | Evaluation contribution | Maturity | Access |
|---|---|---|---|---|
| 2026 | Bysik & Ślepaczuk, *Machine Learning-Based Bitcoin Trading Under Transaction Costs* ([arXiv:2606.00060](https://arxiv.org/abs/2606.00060)) | 27-fold walk-forward testing, cost-aware trade filtering, fold dispersion, block-bootstrap comparison, and multiple-testing correction. | Preprint | [Local PDF](methods/2606.00060-cost-aware-walk-forward-bitcoin.pdf) |
| 2026 | Sepper, *Slippage-at-Risk* ([arXiv:2603.09164](https://arxiv.org/abs/2603.09164)) | Forward-looking order-book slippage and concentration stress for perpetual futures. | Preprint | [Local PDF](methods/2603.09164-slippage-at-risk.pdf) |
| 2026 | Mroziewicz & Ślepaczuk, *Double Out-of-Sample Data and Walk-Forward Techniques* ([arXiv:2602.10785](https://arxiv.org/abs/2602.10785)) | Treats train/test window lengths as selected hyperparameters, followed by one untouched final test and cross-asset transfer. | Preprint | [Local PDF](methods/2602.10785-double-oos-walk-forward.pdf) |
| 2025 | Deep, Deep & Lamptey, *Interpretable Hypothesis-Driven Trading* ([arXiv:2512.12924](https://arxiv.org/abs/2512.12924)) | Sequential walk-forward folds, information-set discipline, realistic constraints, and explicit reporting of insignificant results. | Preprint | [Local PDF](methods/2512.12924-rigorous-walk-forward-validation.pdf) |
| 2025 | Oliveira, Guzman & Firoozye, *Non-Parametric Bootstrap Robust Optimization* ([arXiv:2510.12725](https://arxiv.org/abs/2510.12725)) | Selects portfolio and strategy parameters from conservative bootstrap quantiles rather than the in-sample optimum. | Preprint | [Local PDF](methods/2510.12725-bootstrap-robust-optimization.pdf) |
| 2026 | Chauhan, *Sharpe-ratio variance inflation under cross-sectional and serial dependence in trading panels* ([SSRN 6861958](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6861958)) | Date-level aggregation, HAC-delta inference, dependent bootstraps, researcher-menu correction, factor diagnostics, and turnover-scaled costs. | Working paper | **Record only: fetch failed (SSRN 403)** |
| 2026 | Jung, *A Filtered-Label Calibrated XGBoost Framework with Walk-Forward Validation for Robust Bitcoin Direction Prediction* ([SSRN 6727738](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6727738)) | Combines walk-forward validation with Holm/Bonferroni corrections, DSR, PBO/CSCV, and slippage sensitivity. | Working paper | **Record only: fetch failed (SSRN 403)** |
| 2026 | Arnold, Gavrilopoulos, Schulz & Ziegel, *Sequential Model Confidence Sets* ([publisher](https://academic.oup.com/jrsssb/advance-article/doi/10.1093/jrsssb/qkag066/8676743)) | Extends model-confidence sets with time-uniform sequential coverage; adjacent to ongoing strategy monitoring rather than trading-specific. | Peer-reviewed | **Record only: full-text HTML, no local PDF mirrored** |

## Empirical audits and execution evidence

| Year | Source | Reusable lesson | Maturity | Access |
|---|---|---|---|---|
| 2026 | Liu, *Evaluating Structured Strategy Backtests* ([arXiv:2604.18821](https://arxiv.org/abs/2604.18821)) | Measures pro-forma-to-live decay relative to peer and external benchmarks and conditions the haircut on launch regime. | Preprint; 1,726 commercial strategies | [Local PDF](empirical-audits/2604.18821-backtest-regime-live-performance.pdf) |
| 2026 | Jadouli, *Predictive Extrema, Unprofitable Policies* ([arXiv:2607.19453](https://arxiv.org/abs/2607.19453)) | Evidence audit covering reused dates, unpurged outcome horizons, same-close execution, missing artifacts, and post-hoc promotion. | Single-author preprint; negative study | [Local PDF](empirical-audits/2607.19453-negative-results-evidence-audit.pdf) |
| 2026 | Bieganowski & Ślepaczuk, *Explainable Patterns in Cryptocurrency Microstructure* ([arXiv:2602.00776](https://arxiv.org/abs/2602.00776)) | Purged walk-forward evaluation, fee sensitivity, maker/taker comparison, and flash-crash stress testing; latency and queue position remain unmodeled. | Preprint | [Local PDF](empirical-audits/2602.00776-explainable-crypto-microstructure.pdf) |

## Foundational inference

| Year | Source | Role | Access |
|---|---|---|---|
| 2017 | Bailey, Borwein, López de Prado & Zhu, *The Probability of Backtest Overfitting* ([DOI record](https://escholarship.org/uc/item/4w1110bb)) | PBO estimated through combinatorially symmetric cross-validation across strategy trials. | [Local PDF](foundational/probability-of-backtest-overfitting.pdf) |
| 2014 | Bailey & López de Prado, *The Deflated Sharpe Ratio* ([author record](https://www.davidhbailey.com/dhbpapers/)) | Corrects Sharpe evidence for selection across trials and non-normal returns. | [Local PDF](foundational/deflated-sharpe-ratio.pdf) |
| 2016 | Harvey, Liu & Zhu, *…and the Cross-Section of Expected Returns* ([NBER WP 20592](https://www.nber.org/papers/w20592)) | Multiple-testing thresholds and false-discovery concerns for large strategy/factor searches. | [Local PDF](foundational/harvey-liu-zhu-cross-section-expected-returns.pdf) |
| 2005 | Hansen, *A Test for Superior Predictive Ability* ([DOI](https://doi.org/10.1198/073500105000000063)) | Studentized bootstrap comparison of many alternatives against a benchmark. | [Local PDF](foundational/hansen-test-superior-predictive-ability.pdf) — read in full and implemented 2026-08-06, see `evaluation-framework/evaluation/spa.py` |
| 2000 | White, *A Reality Check for Data Snooping* ([DOI](https://doi.org/10.1111/1468-0262.00152)) | Bootstrap test of whether the best model in a specification search beats a benchmark after data reuse. | [Local PDF](foundational/white-reality-check-data-snooping.pdf) — read in full and implemented 2026-08-06, see `evaluation-framework/evaluation/spa.py` |
| 2011 | Hansen, Lunde & Nason, *The Model Confidence Set* ([DOI](https://doi.org/10.3982/ECTA5771)) | Produces a set of statistically indistinguishable superior models instead of forcing a single winner. | **Record only: paywalled** |

## Surveys

| Year | Source | Coverage | Maturity | Access |
|---|---|---|---|---|
| 2025 | Pippas, Ludvig & Turkay, *The Evolution of Reinforcement Learning in Quantitative Finance* ([arXiv:2408.10932](https://arxiv.org/abs/2408.10932)) | Critical survey of 167 papers, including reward design, costs, market impact, factor controls, survivorship bias, and deployment realism. | ACM Computing Surveys | [Local PDF](surveys/2408.10932-rl-quant-finance-survey.pdf) |
| 2025 | Fu, *The New Quant* ([arXiv:2510.05533](https://arxiv.org/abs/2510.05533)) | LLM prediction/trading survey emphasizing time-safe corpora, full costs, capacity, regime slices, latency, and audit logs. | Single-author preprint | [Local PDF](surveys/2510.05533-new-quant-llm-survey.pdf) |
| 2025/2026 | Ferrell & McInnes, *Reinforcement Learning and NLP for Stock Market Trading: A Methodological Survey* ([SSRN 5135573](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5135573)) | Reviews datasets and evaluation metrics and identifies reproducibility and insufficient-evaluation problems. | Working paper, revised 2026 | **Record only: fetch failed (SSRN 403)** |
| 2025 | Degiannakis et al., *Major Issues in High-Frequency Financial Data Analysis: A Survey of Solutions* ([publisher](https://www.mdpi.com/2227-7390/13/3/347)) | Adjacent survey on data and quantitative-method problems that affect high-frequency backtest validity. | Peer-reviewed, open access | **Record only: open PDF not yet mirrored** |

## Synthesis for this framework

The corpus supports a complementary stack rather than one replacement metric:

1. Maintain a complete trial and artifact ledger before statistical evaluation.
2. Purge overlapping labels and enforce next-executable-price timing.
3. Select models and window lengths without touching one final holdout.
4. Compare against buy-and-hold, peer strategies, factor exposures, and regime
   slices—not only zero return.
5. Model fees, spread, turnover, funding, latency, capacity, and tail slippage.
6. Aggregate to the actually tradable date-level portfolio and use dependent
   bootstrap/HAC inference where observations share shocks.
7. Correct strategy searches using DSR, PBO/CSCV, SPA/Reality Check, or a model
   confidence set as appropriate; pre-registration complements these checks but
   does not mathematically replace them.
8. Reconcile backtest, paper, and live results with the same evidence schema and
   retain negative outcomes.

## Immediate implementation implications

- Add a machine-readable trial ledger so DSR and PBO use the actual search size.
- Add CSCV/PBO and block-bootstrap confidence intervals to `evaluation/`.
- Add purged double-out-of-sample split utilities and prevent partial inspection
  of the final holdout.
- Add fee/slippage grids, funding, and order-book stress inputs.
- Add benchmark/factor/regime decomposition and a backtest-to-live comparison
  report.
- Revise any documentation implying that pre-registration substitutes for DSR;
  it controls researcher freedom but not dependence, non-normality, or the
  sampling distribution of the selected maximum.

## Search notes and unresolved access

Searches combined topic terms for backtest overfitting, walk-forward and purged
validation, multiple testing, Sharpe inference, transaction costs, slippage,
regime robustness, and live decay. Searches were run by category rather than as
one generic query. SSRN blocked three automated PDF fetches with HTTP 403; those
records remain above. No unofficial paywall bypasses were used.
