# Cross-Cutting Learnings

Facts, hypotheses, and ruled-out directions that apply to **both** subprojects. Subproject-specific learnings stay in their own wikis.

---

## Confirmed (cross-project)

- **LLM-driven sequential strategy refinement gets geometrically trapped.** Both feishu and backtesting independently saw an LLM start from a simple template (SMA, momentum) and refine along that vein for many iterations without exploring orthogonal signal families. The local-minimum is the LLM's prior, not the data. **Mechanistic confirmation:** Simhi et al. 2026 ("Old Habits Die Hard: How Conversational History Geometrically Traps LLMs", arXiv 2603.03308) measures this directly across 3 model families × 6 datasets — once a phenomenon appears in a turn, it persists, with Spearman 0.78 between probabilistic (Markov trace) and geometric (hidden-state angle) measures. **Mitigation hint:** the paper shows the trap *dissolves under topical inconsistency* — randomly shuffling unrelated prompts breaks carryover. Practical implication for strategy ideation: deliberately interleave unrelated topics in any LLM-driven search loop, don't let it stay on one thread for many iterations. See `methodology/multi-objective-search.md` for the structural escape route (move to bounded primitive grammar + Pareto search).
- **Single-objective optimisation overfits at any scale.** Feishu IS-parameter-space exhaustion was reached at modest sweep size; further tuning was flagged as overfitting risk. Backtesting's thin samples (N=6, N=32) make any single-metric ranking noise-dominated.
- **Deflated Sharpe Ratio (López de Prado).** Expected max Sharpe under the null grows with √log(N_configs). Any sweep across more than ~10 configs needs DSR or PBO as a gate, otherwise the winner is structurally noise. Pre-register the gate before running the sweep.

## Data sourcing (cross-project)

- **`ccxt` is the default multi-exchange OHLCV/funding library.** Wraps ~100+ exchanges (Binance, Bybit, OKX, Coinbase, Kraken, Hyperliquid, etc.) with a unified API. Free, no auth for public endpoints. Supports OHLCV, funding rates, order book snapshots, trades. Use this before reaching for anything custom unless an exchange explicitly disables it (Hyperliquid OHLCV via Freqtrade is one such case — see `backtesting/wiki/decisions/002`).
- **Free historical funding rate JSON** is published by Binance and Bybit going back years, no auth. Cheapest path to test the CEX→DEX funding lead-lag hypothesis (`backtesting/wiki/learnings.md` open #6).
- **CEX OHLCV as proxy for pre-Hyperliquid history.** Binance BTC perps go back to ~2019; Hyperliquid only ~2023. Use CEX history to *train* regime detectors and HMMs across more cycles. Do **not** use CEX history to *evaluate* a Hyperliquid strategy — microstructure (fee, funding mechanism, liquidity, slippage) differs.
- **`yfinance`** — fine for daily/hourly equities + ETFs + spot crypto (BTC-USD). Useless for perps, funding, intraday <1h, or anything Hyperliquid-specific. Reach for it only when you want equity/macro covariates (SPY, DXY, VIX) as regime inputs to a crypto model.
- **`Scrapling`** (and other scrapers) — wrong tool for market data. Bookmark for non-API sources only (CryptoQuant dashboards, Coinglass heatmaps, on-chain UI-only metrics). Default to ccxt + direct exchange APIs first.
- **Hyperliquid S3 L2 book snapshots** (`s3://hyperliquid-archive/market_data/`) — free, public, massive. Only worth ingesting when the SaR slippage proxy hypothesis (`backtesting/wiki/learnings.md` open #8) becomes the active experiment.

## Open hypotheses (cross-project)

1. **Multi-objective Pareto search beats single-metric max** when objectives are negatively correlated under noise (Calmar-bull, Calmar-bear, ulcer, turnover-adjusted PF, OOS-stability). Inspired by `references/divergence_portfolio_theory.md` — same logic as α-portfolio for distribution fitting.
   - **Test:** scaffold an NSGA-II run on a small primitive grammar (~6 signal families × 2–3 hyperparams) once a subproject has enough independent trades per fold.
   - **Open methodology:** see `methodology/multi-objective-search.md`.

2. **Strategy retirement / kill criteria are missing from both subprojects.** Per Dan Davies (ex-quant, in the comment thread of Leek 2025): *"quant funds survive in the long term because of fundamentally non-quantitative attributes of their managers; it is a very rare person indeed [who] combines the common sense to turn the model off when it is breaking down, with self-discipline to resist the temptation to tinker."* Neither feishu's `trend_vol_v4` nor backtesting's `SmaRegime180` has a documented condition under which it would be retired. This is the real survival mechanism — risk *management*, not signal *quality*.
   - **Test:** before any strategy graduates from leaderboard to paper-trading, write a retirement rule of the form: "kill if rolling-90d Calmar drops below X, or if drawdown exceeds Y% of historical max DD, or if regime indicator Z flips for N consecutive bars."
   - **Open methodology:** add `methodology/kill-criteria.md` once the first concrete rule is drafted (don't write it speculatively — wait for the first real candidate).

## Ruled out (cross-project)

- *(none yet — promote from subproject wikis as patterns appear in both)*

---

## Methodology to write up

- **Combinatorial purged CV with embargo** — protocol doc in `methodology/` once first sweep is run.
- **Deflated Sharpe / PBO gate** — pre-registration template before any sweep.
- **Primitive grammar for signal search** — bounded DSL of signal families to avoid the "infinite strategy space" trap.
