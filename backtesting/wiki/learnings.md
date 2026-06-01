# What We've Learned

Running log. Each entry is a **confirmed fact**, an **open hypothesis**, something **ruled out**, or a pointer to what the next experiment / paper search should prioritise.

This file is the self-correction mechanism for the project. Entries in `Ruled Out` should always state the *mechanism* that broke the idea, not just the metric — so future-you (or the weekly paper-search agent) doesn't re-explore the same dead end with a slight variation. The "What the Next Paper Search Should Prioritise" section feeds directly into `wiki/agent-config/paper-search-trigger.md`.

---

**Reference:** `wiki/reference/strategy-archetypes.md` — canonical taxonomy of 7 strategy types (market making, stat arb, mean reversion, options, order flow, cross-exchange arb), each with signal logic, key parameters, known failure modes, and friction adjustments. Annotated with current project state. The meta failure-modes table there tracks which universal risks (transaction cost blindness, regime change, overfitting) are open vs addressed in this project.

---

## Confirmed Facts

### Evaluation
- **All slope-gate strategies have extreme right-skew and fat tails.** Layer-5 backfill on 6 leaderboard ZIPs (2026-05-16) measured skew +1.3 to +15.8 and excess kurtosis +21 to +338. These are *very* far from Gaussian. **Implication: Sharpe overstates these strategies materially.** Calmar + SQN + DSR partially compensate; Layer-5 reading (Martin + tail-ratio + CVaR-5%) is the explicit correction. Reported on the 6 cards in `wiki/results/2026-05-10-*.md`.
- **Bear-window slope-gate runs have tail_ratio = 0.00.** P95 of daily returns is exactly zero — there are no winners in the right tail because the slope gate keeps the strategy flat. Family is regime-conditional by design; the bear win-rate of ~22% is structural, not a bug. Confirmed from HmmSmaSlope/V2/V3 Hyperliquid bear ZIPs.
- **HmmCarry tail_ratio = NaN; near-zero daily returns.** The conjunction barely trades — most days the strategy is flat. Bull-window Ulcer 1.50 but the *reason* is "almost never deployed", not "deployed and uneventful." Don't read low Ulcer as edge here.
- **FundingCarry is chronically underwater, not just deeply once.** Ulcer 5.49 + Pain 4.05 on Binance bull — among the worst of any leaderboard strategy. MDD numbers alone underrepresent how much time this strategy spends underwater. Strong example of Ulcer disagreeing with point-in-time MDD: if MDD were the only DD signal, this strategy might be misranked vs strategies with the same point-in-time MDD but quicker recovery.
- **R2 (HmmRegime4Rolling) K1 kill is doubly justified under Ulcer.** A1.5 re-backtest on Binance common window (2020-09 → 2026-05) produced MDD 7.65%, Ulcer 4.01, Pain 3.47. Compared to T3 on same window (MDD 2.21%, Ulcer 1.30, Pain 1.12), R2 is 2-3× worse on path-aware metrics. The drawdown is *chronic*, not one event — Pain 3.47% says the strategy spends most of its life meaningfully underwater. K1 (MDD > 5.5%) is supported, not exaggerated, by the path-aware lens.
- **TrendFilter200 on common window is positive but lottery-shaped.** A1.5 re-backtest: total +15.49%, MDD 8.54%, **skew +15.02, excess kurtosis +308.0**, win rate 12.5%. The strategy is chronically underwater (Pain 3.04, Ulcer 3.79) with rare massive winners providing all the return. This refines the original "ruled out" verdict: TrendFilter200's *mechanism* (8-day MA on 1h) is correctly killed for bear regimes but accidentally captures bull-run breakouts; the family failure mode is "no slope gate", not "wrong window length". Slope-gate variants (SmaRegime180/720) achieve similar bull returns with 2-3× lower Pain.

### Infrastructure
- **Freqtrade** is the open-source framework this project is built on — live trading bot + backtester. We only care about the backtester for now.
- **Hyperliquid uses USDC as the quote currency.** Freqtrade pair notation for futures is `BTC/USDC:USDC` (base/quote:settle).
- **Freqtrade now ships a Hyperliquid adapter** (`freqtrade/exchange/hyperliquid.py` on current main). Last year when Ethan set this up, it didn't exist — that's why he had to source data externally.
- **Default data format in this repo is Feather.** Backtests must pass `--data-format-ohlcv feather` (also set in `config.json` as `dataformat_ohlcv`).

### Data sourcing
- **Freqtrade's `download-data` is fully disabled for Hyperliquid**, not just capped. `ohlcv_has_history=False` in the adapter triggers a hard refusal: "Hyperliquid does not support downloading trades or ohlcv data." Confirmed 2026-04-24.
- **We have a working direct-API downloader:** `scripts/download_hyperliquid.py` hits `/info candleSnapshot` and writes Feather in freqtrade's layout. Verified end-to-end — 5001 rows of 1h BTC/USDC:USDC data landed, `freqtrade backtesting` consumed them, 49 trades over ~200 days.
- **5000 candles is the hard public ceiling**, not a pagination cap. Hyperliquid API returns at most 5000 per call and doesn't expose older data via any public endpoint.
- **Hyperliquid publishes no bulk OHLCV to S3.** Official docs: "No other historical data sets are provided via S3 (e.g. candles or spot asset data)." Only L2 book snapshots (`s3://hyperliquid-archive/market_data/`) and asset contexts are available.
- **5000 candles is plenty for longer timeframes.** 1h = ~208 days, 4h = ~833 days, 1d = essentially the full life of the exchange. Only sub-hour strategies hit the constraint.

### Scoring
- **Co-primary metrics: Calmar (closed trades) + SQN.** Freqtrade reports both. Calmar = CAGR / max_drawdown on closed-trade equity; SQN = sqrt(N) × mean(R) / std(R). Use Calmar as primary when N≥20; use SQN as co-primary always because it explicitly penalises thin samples. At N<20, Calmar is mathematically valid but statistically unreliable — a single outlier trade can produce Calmar >20 on N=6. Always show SQN alongside. Confirmed 2026-04-30.
- **Also track: Profit Factor and Expectancy.** Profit Factor (gross profit / gross loss) is robust to thin samples and has no N assumption. Expectancy (mean return per trade, as ratio of risk) gives a complementary view. Both are now in the leaderboard.
- **Sharpe (closed trades) shown as sanity check.** "Daily wallet balance" Sharpe/Calmar penalises sparse strategies; don't use them for decision-making.
- **Prior leaderboard entries confirmed 2026-04-30:** LongOnlyStrategy closed-trade Calmar -4.55 (SQN -0.53, PF 0.81); TrendFilter200 closed-trade Calmar -6.84 (SQN -2.79, PF 0.43). The table previously said "n/a¹" for these — now corrected.
- **Fee correction (2026-05-03):** The original 6.33% SmaRegime180 result was NOT zero-fee. Freqtrade applied ccxt's hardcoded Hyperliquid default (0.045%/side). True zero-fee is 6.62% (Calmar 9.50). Actual Hyperliquid taker (0.035%/side): 6.39% (Calmar 8.86). **The `"fee"` key in config.json exchange block is silently ignored by the backtester — use `--fee FLOAT` CLI flag instead.**
- **Cost modeling complete (2026-05-03).** Historical Hyperliquid BTC funding rates applied per-trade across all 32 trades (19,733 8h periods, Feb 2024 → Apr 2026). Total drag: −2.25 USDC taker fees + −12.08 USDC funding = −14.33 USDC on 66.16 USDC gross (21.7% cost ratio). Net post-all-costs: +51.83 USDC (+5.18%), estimated Calmar ~7.2. Funding is 5.4× larger than taker fees in dollar terms and adversely selected: 85% of funding drag falls on the 7 winning trades (avg hold 25.9d) during bull-run periods, including 5.27 USDC from the 67-day Oct–Dec 2024 winner. Strategy survives realistic cost modeling — Calmar remains well above 2.0 threshold.

---

## Open Hypotheses

Ordered by how much the answer would change what we do next. Each should have a concrete test and a search direction if one exists.

1. **What's the current bottleneck on backtest speed?** Goal for this revisit was "make backtesting faster" — but a full backtest on 5000 1h candles returns in seconds. May already be fast enough; re-check only once real strategies and bigger sweeps are in play.
   - **Test:** `cProfile` or `python -X importtime` around a multi-pair sweep once we have one.
2. **What timeframe does the target strategy need?** Determines whether the 5000-candle cap matters. If 1h+, ignore the cap. If 1m / 5m and we want multi-month history, we need to accrete candles over time (rerun the script daily) or reconstruct from S3.
   - **Test:** pick a first real strategy; its timeframe answers the question.
3. **Is Freqtrade's Hyperliquid execution adapter mature enough to go live?** Separate track from backtesting; relevant only once a strategy is trustworthy.
   - **Test:** read freqtrade changelog entries tagged `hyperliquid`; check issue tracker for open execution bugs.
4. **Do crypto-specific factors (funding rates, perp basis, on-chain flow) add orthogonal signal to price-only strategies?** Partially explored — see papers below.
   - **What we know:** Funding rates on BTC perps (Binance, Bybit) are one-step-ahead predictable via DAR models but predictability is time-varying (Inan 2025). Roughly 60% of apparent DEX carry is eaten by transaction costs + spread reversals (Zhivkov 2026). **NEW (Aug 2025):** Empirical carry-only strategies on DEX perps (Drift, ApolloX) yield extremely high Sharpe ratios (23.55, 6.50) vs. negative on CEX (Binance −7.34, Bitmex −7.93) over the same period; DEX carry exhibits *no correlation* with spot HODL — pure diversifier (see `dex-carry-funding-rate-arbitrage-2025.md`). The CEX negativity confirms that our bear-market test window compressed CEX funding rates; DEX venues retained premia due to less-sophisticated arbitrage. A carry strategy therefore needs: (a) minimum funding-rate threshold (≥20–25 bps per 8h per Zhivkov), (b) DAR forecast confirming persistence (Inan), (c) DEX venue preference over CEX for Sharpe. Leverage on carry raises risk non-linearly; test unleveraged first.
   - **Test:** implement a funding-rate threshold + DAR-direction gated carry strategy. Requires adding funding-rate data fetching to `scripts/download_hyperliquid.py` (Hyperliquid API exposes current funding rate; build a collector). Then backtest with and without DAR gate; compare Sharpe/Calmar.
   - **Search:** Hyperliquid-specific fee schedule and taker cost; open-interest imbalance or liquidation-cascade signals as carry-timing overlays — still open.
5. **Can a regime filter work on crypto at all, given the `TrendFilter200` failure?** The naive 1h SMA200 cross-up failed (see Ruled Out). The family isn't dead — it's the *specification* that failed.
   - **What we know from SmaRegime720 (2026-04-30):** Lengthening to SMA720 (≈30d) and adding a slope gate (`sma720 > sma720.shift(24)`) eliminated most whipsaw — 6 trades vs 90 for TrendFilter200, MDD 0.30% vs 4.22%, first positive total return (+0.80%) in the bear window. Closed-trade Calmar was 28.96 — best result so far. BUT: sample is only 6 trades (1 winner at +10.98%, 5 losers). Thin evidence. Bull-market validation pending.
   - **4h unscaled test failed** (13 trades, -1.73%, market change +25.51%): not a fair comparison — SMA720 on 4h = 120-day window, not the intended 30-day window. A fair bull test needs a 4h-scaled variant (SMA180 + slope_lookback=6) or extended 1h history.
   - **SmaRegime180 bull-window result (2026-04-30):** 4h variant (SMA180, slope_lookback=6) on BTC 4h, Feb 2024 → Apr 2026 (includes 2024–2025 bull). 32 trades, Calmar (CT) 8.68, SQN 1.02, Profit Factor 2.72, CAGR +2.83%, MDD 1.74%, win rate 21.9%. Bear sub-window alone: Calmar 6.59, 5 trades, SQN 0.33. **H7 PASS** — positive Calmar in both windows. Slope gate confirmed as a whipsaw suppressor across both regimes.
   - **Remaining open questions:** (a) Do post-cost metrics remain positive? (Estimated ~2.24% fee drag vs 6.33% gross — see Scoring note.) (b) Would an HMM regime filter improve win rate from ~22% to ~40%+ while preserving low MDD?
   - **What we know from HMM papers:** A Wasserstein HMM (arXiv 2603.04441) achieves Sharpe 2.18 vs SPX 1.18. 4-state NH-HMM on Bitcoin 2024–2026 outperforms standard 2-state HMM (Preprints.org 202603.0831) — likely {low-vol bull, high-vol bull, low-vol bear, high-vol bear}.
   - **Implication:** Build 4-state NH-HMM (not 2-state), use Bayesian posterior at P(bull) > 0.65, add 24h realised-vol as the transition covariate.
   - **Next test:** 4-state NH-HMM via `hmmlearn` GaussianHMM(n_components=4) on rolling 500h returns + log-volume, enter at P(bull-state) > 0.65. Compare Calmar, SQN, and win rate directly against `SmaRegime180`. First: re-run `SmaRegime180` with realistic fee config to confirm post-cost viability (top priority per "What the Next Experiments Should Prioritise").
   - **Search:** crypto-specific 1h/4h HMM validation with Calmar — daily Bitcoin validation found, intraday still open.
6. **Does the CEX → Hyperliquid (DEX) funding-rate lead time create an exploitable signal?** Zhivkov (2026) shows Granger causality runs CEX→DEX with zero reverse; the lead is measured in minutes on 1-min data. At 1h frequency this lag may be fully collapsed, but on 15m or 5m data a CEX (Binance) funding-rate signal might lead Hyperliquid by 1–3 bars.
   - **Test:** download Binance BTC funding rate at high frequency and correlate with Hyperliquid funding rate lags using Granger test. Determine if lead persists at 15m or 1h.
   - **Search:** CEX–DEX funding rate lead-lag; Hyperliquid-specific execution dynamics.
7. **Are our backtests artificially inflated by the bear-market regime at construction time?** A 2026 empirical study (Liu, arXiv 2604.18821) across 1,726 commercially distributed strategies shows that pro-forma backtests predominantly capture the factor regime present at construction time, not strategy skill — and strategies launched after extreme regime conditions experience sharper live-period deterioration.
   - **What this means here:** All our backtests are from Oct 2025 → Apr 2026, a sustained BTC bear (−37.20% buy-and-hold). Any strategy that avoids long exposure looks good purely because the regime rewarded flatness or shorts. A strategy with positive Calmar in this window may flip negative once BTC recovers.
   - **Test:** for any strategy with Calmar > 0 in the current test window, backtest over a bull sub-window using 4h data (~833 days available via `scripts/download_hyperliquid.py`). Require the strategy to show positive risk-adjusted return in BOTH regimes before moving to live consideration.
   - **Benchmark fix:** when adding new results to the leaderboard, report *benchmark-relative Calmar* (strategy Calmar minus buy-and-hold Calmar for the same period) as an additional column to reduce regime carry-over flattery.
8. **Does a SaR proxy (bid-ask spread × depth imbalance from Hyperliquid L2 book) predict liquidation cascade risk and correlate with adverse funding drag?** Sepper 2026 (arXiv 2603.09164) shows SaR spikes before the Oct 2025 cascade. 85% of our funding drag falls on winning trades during bull-run periods — exactly when OI and leverage are high. If high-SaR periods precede funding spikes, adding a LOB-depth check as a "pause carry" condition could improve post-cost Calmar.
   - **Test:** download Hyperliquid L2 book snapshots (`/info l2Book`) during historical high-funding periods; correlate top-5 ask depth with next-period funding rate change. If correlation > 0.3, prototype a SaR proxy filter.
   - **Search:** papers combining LOB depth with funding-rate prediction on perp venues.
9. **Does adding a `funding_aligned` feature improve NH-HMM state separation?** Badawi 2025 (arXiv 2601.06084) documents that funding/4h-trend alignment predicts expansion vs. compression regimes. Our planned NH-HMM uses returns + log-volume. Adding a binary `funding_aligned` covariate (sign of funding agrees with 4h SMA slope) may improve bull-state recall without hurting precision.
   - **Test:** compare NH-HMM(features=[returns, log-vol]) vs. NH-HMM(features=[returns, log-vol, funding_aligned]) on held-out 2025 data. Measure: bull-state precision, bear-state precision, and regime-conditional Calmar.
   - **Dependency:** requires funding-rate history download (already planned as Experiment #2).
10. **Is the 1h-4h range the right mean-reversion horizon for BTC on Hyperliquid, or does the transition zone shift with volatility regime?** Safari & Schmidhuber 2025 (arXiv 2501.16772) show the reversion-to-trending transition occurs in the 1–4h range broadly, but note crypto may differ due to higher retail participation. The transition boundary may compress to 15–30 min in high-vol regimes and expand to 4–8h in low-vol regimes.
    - **Test:** measure 1h BTC return autocorrelation (lag-1) separately during HMM bull-state vs. bear-state periods. If autocorrelation sign differs by regime, mean-reversion strategy should be state-conditional.
    - **Search:** papers on regime-conditional autocorrelation in crypto 1h returns.
11. **Should the carry strategy use OU z-score entry and a time-exit of 2–3 bars at 4h?** Le 2026 (arXiv 2605.06405) calibrates funding OU dynamics on Hyperliquid ETH/BTC/SOL perps and finds half-life ≈ 8h for ETH (Binance proxy; Hyperliquid likely similar). This means: (a) a funding-elevated position decays to mean in ~1 day; (b) entry should use z-score above OU mean (not absolute rate) to distinguish persistent-high from spike entries; (c) spike entries (>3σ) revert faster and should be excluded.
    - **Test:** calibrate OU(θ, μ, σ) on the existing Hyperliquid BTC funding parquet (`user_data/data/hyperliquid/funding/BTC-funding.parquet`) using `scipy.optimize`. Confirm half-life is in the 6–12h range. Then implement a carry strategy with: entry at z > 1.5, spike-exclusion at z > 3, time-exit at hold_bars ≥ 3 (at 4h). Compare Calmar vs. naive threshold strategy.
    - **Dependency:** OU calibration is a ~30-line Python snippet using the existing funding data.

---

## Ruled Out

Explain the mechanism, not just the metric — so we don't re-explore variants.

- **Hunting for Ethan's original data source.** Confirmed there's no canonical public bulk OHLCV for Hyperliquid. Whatever he used was ad hoc and isn't worth the time to retrace. Mechanism: Hyperliquid simply does not publish it. See `decisions/002`.
- **Maintaining `freqtrade_hyperliquid_download-data` as a separate repo.** It existed because freqtrade didn't support Hyperliquid; now it does. Mechanism: upstream closed the gap. See `decisions/001`.
- **Using freqtrade's built-in `download-data` for Hyperliquid.** Hard-disabled in the adapter via `ohlcv_has_history=False`. Mechanism: not a config toggle — it's a structural refusal in the exchange class. Use `scripts/download_hyperliquid.py` instead.
- **Naive 1h SMA200 cross-up as a regime filter** (`TrendFilter200`, 2026-04-24). Calmar -6.84, 12.2% win rate, 26 consecutive losses. Mechanism: 200 periods on 1h = ~8 days, too short to define a regime in crypto. In a sustained bear every cross-up is a bull-trap. Short-window, single-asset, single-timeframe regime filters get whipsawed. The broader family ("regime filters on crypto majors") is still open — see `wiki/results/2026-04-24-trend-filter-200.md` for candidate refinements (longer window, slope confirmation, higher-timeframe agreement).

---

## What the Next Experiments Should Prioritise

Updated 2026-05-10.

**Done (2026-05-16):**
- **Two-leg PairsZScoreV2 shipped** (`user_data/strategies/PairsZScoreV2.py`, SOL+DOGE, 5.5y common window): +3.04% / Calmar 0.97 / MDD 2.91% / SQN 0.42 / 13 trade-legs. **Confirms v1's X1 kill** rather than rescuing it — SOL leg is essentially directional alpha; DOGE leg loses 7/8 trades to per-leg −10% stops *before* the joint z-score mean-reverts. Surfaces a Freqtrade framework limit: per-leg stops break atomic pair execution. Decision 010 prerequisite #4 resolved. See `wiki/results/2026-05-16-pairs-zscore-v2.md`.
- **Binance funding parquets extended to full 5.5y (2020-09 → 2026-05) for all 5 coins; C1 and F1 re-backtested.** C1 (FundingCarry): +32.44% / Calmar 1.93 / MDD 15.65% / SQN 1.22 — real standalone edge but MDD kills it (2.85× K1, > 11% decision-009 hard cap). F1 (FundingExtremeMR): −11.60% / Calmar −0.32 / MDD 33.51% — stays killed; not a truncation artefact. See `wiki/results/2026-05-16-funding-{carry,extreme-mr}-fullwin.md`. Unblocks decision-010 prerequisite #5.
- **Reverse-sign HmmCarry tested** (`HmmCarryReverse`, 5-coin Binance common window): +12.67% total / Calmar 0.78 / MDD 15.09% / SQN 0.56 / 2006 trades / win rate 34.8%. Sign flip is directionally correct vs the 05-10 HmmCarry catastrophe (HmmCarry Calmar 0.08, MDD 35.46%) — confirms the anti-complementarity mechanism — but **still fails K1 by 2.7×** and decision 009 portfolio gate by an even wider margin. BTC win rate rehabilitated (7.7%→35.9%); AVAX has opposite sign (−9.79%). **Single-rule HMM × funding conjunction is killed in both sign directions**; only per-coin signed-funding remains as a live extension. See `wiki/results/2026-05-16-hmm-carry-reverse.md`.
- **Layer-5 evaluation tooling shipped** (`scripts/eval_layers.py`). 6 result cards backfilled with tail/path metrics. Decision 005 published. See `wiki/decisions/005-evaluation-and-diversity-plan.md`.
- **Pre-decisions locked in** for the evaluation-and-diversity buildout (correlation window, MDB weighting, held-out reserve, pairs mechanics). Documented in decision 005 section 7.
- **Cross-cycle re-backtest on Binance 5-coin common window (2020-09 → 2026-05)** completed for 12 strategies — 6 BTC-only + 6 multi-asset. Results appended to `_index.md` as "Common-Window Leaderboard (A1.5)".
- **Major finding: R∧T family (HmmSmaSlope V1/V2/V3) on 5 coins is the new headline frontier.** R∧T2 Calmar 30.23, SQN 2.73, CAGR 21.31% over 5.5y. MDD 6.05% breaches K1 (5.5%) by 0.55pp — disputed whether this kills the strategy or whether K1 was mis-calibrated on bear-only Hyperliquid data. Decision deferred to A2 (MDB will tell us whether R∧T2 is portfolio-justified vs T3 regardless of MDD breach). See `_index.md` footnote 8.
- **R2 (HmmRegime4Rolling) K1 kill is doubly justified under Layer-5.** Common-window MDD 7.65%, Ulcer 4.01, Pain 3.47 — chronic underwater, not one event. T3 same window: MDD 2.21%, Ulcer 1.30, Pain 1.12. R2 is 2-3× worse on every path-aware metric.
- **HmmCarry anti-complementarity reproduces on Binance common window.** MDD 35.46% (vs Hyperliquid bear -19.59%). Conjunction confirmed dead, not regime-specific.
- **TrendFilter200 partial-rehabilitation.** Common window +15.49%, but skew +15 / kurt +308 / Pain 3.04 → lottery-shaped, not durable edge.

**Done (2026-05-10 late):**
- **Pre-registered kill criteria** for SmaRegime180 — `decisions/004-kill-criteria-sma-regime-180.md`. Hard kills (MDD > 5.5%, six straight stops, 365d return ≤ 0 for 30d, walk-forward Calmar < 2). Continuous-shrinkage formula tying live size to rolling 180d PF, Calmar, and bull/bear ratio (Davies–Ravagnani 2026). Quarterly walk-forward review mandatory.
- **CEX bull-window validation** for SmaRegime180 — Binance BTC/USDT:USDT perp 4h, 2019-10 → 2026-05, 6.7y, 92 trades, 2 bull + 2 bear cycles. Full-window Calmar 7.23 (vs Hyperliquid 8.68), SQN 1.73, PF 2.85, MDD 2.22%, win rate 21.7% (vs 21.9% on Hyperliquid — structurally identical). Sub-windows: bulls Calmar 14 / 21, 2022 deep bear Calmar −5.23 with PF 0 but MDD 0.28% (slope gate correctly stays flat), 2025 mild bear +1.61%. **SmaRegime180 graduates from leaderboard headline to paper-trading candidate.** H7 inflation is bounded (~20%), not collapsing.

**Next (refreshed 2026-05-16 post-sprint):**

Paper prerequisites (per `decisions/010-paper-plan-deferred.md`):
1. **Begin 30-day paper-trading dry-run for the candidate book {T3, R∧T2}** on Hyperliquid live, evaluating against decisions/004 (T3 standalone K1) and decisions/009 (portfolio-aware K1). Live action — schedule, not autonomous.
2. **Two-leg PairsZScore v2.** Decision 005 pre-decision Q4 was overridden to single-leg in the 05-16 sprint. Implement v2 (two-leg cointegration with proper hedge ratio); either rescues X1 (changes results) or confirms killed verdict (strengthens it). Result feeds the paper.
3. **Extend Binance funding parquets from 2.3y → full 5.5y.** Currently truncates C1 (FundingCarry) and F1 (FundingExtremeMR) evaluation. Re-run both on full history; may move them between categories.
4. **Forward held-out window** (Binance 2026-06 → 2026-12, locked by decision 005). Stays untouched until the above three complete.

Secondary follow-ups (smaller, can run in parallel with #2/#3):
5. ~~**Reverse-sign HmmCarry**~~ — **DONE 2026-05-16**: sign flip is directionally correct (+12.67% vs HmmCarry's MDD-35% disaster, BTC win rate rehabilitated 7.7%→35.9%) but MDD 15.09% still fails K1 by 2.7×; Calmar 0.78. AVAX has opposite sign. **Single-rule HMM×funding conjunction killed in both sign directions**; only per-coin signed-funding remains live. See `wiki/results/2026-05-16-hmm-carry-reverse.md`.
6. **Compute combined-book MDD on the common window** via `scripts/run_correlation_mdb.py`. Decision 009 §3 needs this scalar to confirm the portfolio-aware gate's ✓ for {T3, R∧T2} is actual, not provisional.
7. **Backfill Ulcer column** across remaining leaderboard rows (a few are still "—").

**Earlier 2026-05-10 priorities (still open):**

1. **Rolling-window HMM refit for HmmRegime4.** The 2026-05-09 backtest (BTC 1h bear, 74 trades, win rate 45.9%, SQN 1.38, Calmar 26.35) was run with the HMM fit on the full visible window — i.e. with look-ahead. Implement a walk-forward variant: re-fit the HMM every K bars on prior data only. If win rate stays above ~35%, the regime signal is real. If it collapses toward 22%, the look-ahead was the alpha. **This is the single most important next experiment** — it tells us whether HmmRegime4 is genuine regime detection or an artifact.
2. **Multi-asset HmmRegime4 run.** Data for 7 Hyperliquid majors (BTC/ETH/SOL/HYPE/ARB/AVAX/DOGE) × {1h, 4h} now on disk (downloaded 2026-05-09). Run HmmRegime4 across all 7 to check whether regime structure generalises beyond BTC. Watch for cross-asset correlation (BTC dominance ≈ 0.7+) — effective sample size is less than 7×.
3. **Funding-rate carry strategy.** Funding history (~25k records) for all 7 coins now on disk. Next: implement threshold-gated carry strategy (minimum rate ≥20–25 bps/8h, DAR-direction gate per Inan 2025).
4. **Post-cost analysis for HmmRegime4.** Apply taker fees (already in the run) + funding drag per-trade (similar to SmaRegime180 cost modelling on 2026-05-03). Funding adversely selects to long-hold winners; HmmRegime4's avg duration is 1d 09:47 so funding drag should be much smaller than SmaRegime180's 12.08 USDC.
5. **Profile** (deferred). "Make backtesting faster" still unverified as a bottleneck.

**Done (2026-05-09):** `HmmRegime4` backtest run on BTC 1h bear window (Nov 2025 → May 2026, 187d, --fee 0.00035, 74 trades). Calmar 26.35 (inflated by tiny 1.03% MDD), SQN 1.38, **win rate 45.9% vs SmaRegime180's 21.9%** — open hypothesis #5 (HMM regime detection lifts win rate from ~22% toward 40%+) confirmed. Profit Factor 1.58 (down from SmaRegime180's 2.72 — wins more often but each win smaller). Look-ahead caveat per strategy docstring: HMM fit on full visible window, treat as upper bound. Result card: `wiki/results/2026-05-09-hmm-regime-4.md`. Two minor fixes during run: (a) `log_vol.std().clip(lower=...)` → `max(log_vol.std(), 1e-9)` (pandas scalar vs Series API); (b) `download_hyperliquid.py` funding payload — `fundingHistory` API contract changed (flat fields, not `req`-wrapped) and 0.2s inter-page sleep added to avoid 429 on long histories. Multi-asset OHLCV expansion completed: 7 Hyperliquid majors × {1h, 4h} + funding history for all 7 (~25k records each, except HYPE 12.5k since coin only existed Dec 2024+).

**Done (2026-05-05):** `HmmRegime4` strategy implemented (`user_data/strategies/HmmRegime4.py`). 4-state GaussianHMM on rolling 24h log return + log-volume z-score; entry at P(bull-state)>0.65, exit at P(bull-state)<0.45. Requires `pip install hmmlearn`. Funding-rate history collector added to `scripts/download_hyperliquid.py` (`--funding --coins BTC ETH`); writes `user_data/data/hyperliquid/funding/<COIN>-funding.parquet` with incremental-update support.

**Done (2026-05-03):** Full cost modeling for SmaRegime180. Discovered that original 6.33% was already fee-inclusive (ccxt default 0.045%/side, not zero-fee). Fetched 19,733 historical Hyperliquid funding rate records; applied per-trade. Net post-all-costs return +5.18%, est. Calmar ~7.2. Funding drag (1.21% portfolio) is 5.4× larger than taker fees (0.23%) and adversely selected to winning trades. Strategy survives.

**Done (2026-04-30):** H7 bull-window validation for the slope-gate SMA family (SmaRegime180 passes). Prior leaderboard entries corrected with closed-trade Calmar. Leaderboard expanded with SQN and Profit Factor columns.

---

## What the Next Paper Search Should Prioritise

Updated 2026-05-10 (weekly paper-search agent). This section is the source text for the weekly paper-search agent's prompt — keep it current.

**Do NOT search for:**
- Hyperliquid bulk OHLCV sources or historical data archives (ruled out above — none exist).
- Generic SMA-cross or RSI-cross strategy papers — these are baseline noise, not research.
- General funding-rate carry papers at the "naive always-on carry" level — we already know DEX carry exists and is profitable in isolation (Drift Sharpe 23.55, Aug 2025). Search only for papers that address *conditional* carry (threshold-gated, rate-predicted, or cost-adjusted) or that quantify Hyperliquid-specific carry costs.
- HMM papers on equity or FX markets — daily Bitcoin-specific NH-HMM validation is now in hand (Preprints.org 202603.0831). Do NOT search for more daily-frequency HMM papers unless they report 1h or 4h results.
- General slippage/execution papers on equity markets or CEX spot — we need perp-specific or Hyperliquid-specific studies only. Slippage at the SaR methodology level (Sepper 2026, arXiv 2603.09164) is now found; don't re-search this angle.
- Market-making papers on perpetual DEXs — Le 2026 (arXiv 2605.06405) has mined the Hyperliquid OU calibration data from the market-making literature. Further market-making papers are unlikely to add directional carry signal.

**Priority 1 — Funding-rate carry on DEX perps: Hyperliquid-specific threshold (NARROWED further).**
We now have: (a) empirical backing that DEX carry is profitable (Drift Sharpe 23.55, Aug 2025), (b) the carry timing principle — funding aligned with 4h context expands, funding divergent compresses (Badawi 2025, arXiv 2601.06084), (c) DAR predictability of next-period rate (Inan 2025, SSRN 5576424), (d) OU half-life of funding ~8h on Hyperliquid ETH/BTC/SOL, spike-exclusion filter warranted (Le 2026, arXiv 2605.06405). The remaining open question: the *actual break-even funding-rate threshold* on Hyperliquid accounting for taker fee (0.035%/side) + DAR uncertainty + OU mean. The threshold is not an absolute rate but a z-score above OU mean. Search for: papers that backtest threshold-gated carry with DAR forecasts on perp venues and report Calmar or Sharpe by threshold level; papers that calibrate OU parameters on a Hyperliquid BTC funding time series specifically (not Binance proxy).

**Priority 2 — Regime detection: intraday HMM with quantitative performance results (NARROWED).**
We have: daily 4h Bitcoin NH-HMM validation (Preprints 202603.0831), Wasserstein HMM technique (arXiv 2603.04441), and a candidate covariate — funding/4h-context alignment (Badawi 2025, arXiv 2601.06084). The remaining gap: a paper reporting *regime-conditional Calmar or Sharpe* on 1h or 4h crypto data. Search for: (a) NH-HMM or MSGARCH papers on crypto intraday that include a strategy backtest with Calmar/Sharpe; (b) any paper using funding rate or OI imbalance as an explicit HMM transition covariate and quantifying the improvement in regime purity or strategy performance.

**Priority 3 — CLOSED (2026-05-10).** The T+0 vs T+1 fill-semantics residual gap has been searched across 3+ cycles with no relevant papers found. This is likely a gap in published literature rather than an explorable research direction. Internally estimate the fill-timing bias by comparing Freqtrade's "open of next bar" fill model against a T+1 fill model on SmaRegime180's 32 trades — entry prices differ by at most 1 OHLC open-to-close range, which is well within the SmaRegime180 edge at Calmar 8+. Close this search priority.

**Priority 4 — Mean-reversion at 1h–4h timeframes in crypto majors (NARROWED — implementation gap).**
We now have structural evidence: markets revert sub-hour and trend at hours-to-years (Safari & Schmidhuber 2025, arXiv 2501.16772), and the 4h funding-divergence mechanism provides a mean-reversion trigger (Badawi 2025, arXiv 2601.06084). The remaining gap is implementation-level: a Calmar-validated crypto mean-reversion strategy at 1h granularity. Search for: (a) crypto intraday mean-reversion backtests with Calmar ≥ 2 at 1h frequency; (b) short-horizon reversal after funding-rate extremes on BTC perps with quantified Sharpe/Calmar; (c) order-flow imbalance (OFI) as a 1h mean-reversion signal in crypto perps. NOTE: OFI papers found so far operate at sub-second to 1-minute frequencies (Binance Futures LOB data); none yet translated to the 1h granularity relevant to our strategies.
