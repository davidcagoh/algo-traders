# Paper Search Log — 2026-05-31

## Target window
May 17–31, 2026 (two weeks since last search on 2026-05-24).

## Summary
Three parallel searches across arXiv (q-fin.PM/TR/ST/RM), SSRN, and Google Scholar found **no new papers in the May 17–31 window** that matched all qualifying criteria for any of the three open priorities. The specific niches searched are sparsely covered in the published literature broadly; a 2-week window compounds this.

Three papers from earlier in 2026 or 2025 were identified as genuine wiki indexing gaps and added this session.

---

## Priority 1 — Conditional carry: basis-gated entry, log-basis OU calibration

**Search terms used:**
- `log basis perpetual futures carry strategy 2026`
- `perp spot spread z-score strategy crypto 2026`
- `conditional carry perpetual swap Calmar Sharpe 2026`
- `basis-gated carry z-score threshold Hyperliquid`
- `Ornstein-Uhlenbeck log basis perpetual crypto backtest`
- `SSRN "log basis" "perpetual futures" 2026`
- Direct fetches: arXiv 2605.05089, 2605.06405, SSRN 6365329

**May 17–31 result:** Null. The specific combination of (a) basis-gated entry, (b) z-score threshold analysis reporting Calmar by level, (c) perp venue is absent from indexed literature.

**Near-miss (arXiv:2605.05089, May 6, 2026):** "Dynamic Collateral Control for Permissionless Spot Perpetual Basis Trading" models carry-loss vs. rebalancing-cost tradeoff as a stochastic control boundary for BTC/ETH/LINK/DOGE. Adjacent to P1 in spirit but is about collateral sizing (not signal entry), no Calmar/Sharpe reported, and falls just outside the 2-week window. Could be indexed in a future pass if the collateral sizing angle becomes relevant.

**Gap added to wiki:** `crypto-carry-regime-decomposition-2026.md` (Management Science 2026, BIS WP 1087) — Schmeling, Schrimpf, Todorov document naive CEX carry degradation (Sharpe 6.45 → negative in 2025). Not a basis-gated paper, but the regime decomposition cross-validates our C1 kill and confirms DEX-only strategy direction.

---

## Priority 2 — Intraday HMM regime detection on crypto (1h/4h)

**Search terms used:**
- `nonhomogeneous HMM crypto intraday 2026`
- `MSGARCH bitcoin 1h 4h regime Calmar Sharpe 2026`
- `Markov switching hourly bitcoin perpetual 2026`
- `HMM funding rate OI covariate crypto transition 2026`
- `regime-conditional position sizing crypto perpetual 2026`
- `arXiv q-fin.TR hidden Markov cryptocurrency May 2026`

**May 17–31 result:** Null. This is the third consecutive search cycle without a qualifying paper. No paper satisfies all four criteria simultaneously: (a) crypto-specific, (b) 1h or 4h frequency, (c) HMM/MSGARCH model, (d) explicit strategy backtest with Calmar or Sharpe. The literature gap is structural, not a search artifact.

**Observation:** This priority may remain empty for multiple more cycles. The intraday HMM + strategy backtest combination appears to require proprietary tick data (for LOB features) that academic researchers rarely have on-exchange perp data for. Consider closing or downgrading P2 in the next learnings.md update if a 4th cycle also returns null.

---

## Priority 4 — 1h-aggregated OFI / NBV on crypto perps

**Search terms used:**
- `order flow imbalance hourly crypto perpetual 2026`
- `net buy volume bitcoin 1h 4h signal backtest`
- `OFI aggregated cryptocurrency hourly frequency`
- `intraday mean reversion bitcoin 1h Calmar 2026`
- `OHLCV order flow proxy crypto perpetual backtest`
- `microstructure signal hourly bitcoin perp 2026`
- `arXiv q-fin.TR order flow cryptocurrency 2026`

**May 17–31 result:** Null. The specific niche (1h LOB-aggregated OFI or OHLCV-NBV on crypto perps, fee-beating strategy) is genuinely underexplored in published literature as of this search.

**Near-miss (arXiv:2506.05764):** "Exploring Microstructural Dynamics in Crypto LOBs, Bybit" — 100ms–multi-second LOB snapshots. Excluded per the existing "Do NOT search for minute-level OFI" rule.

**Gaps added to wiki:**
- `on-chain-flows-hourly-bitcoin-return-2024.md` (arXiv:2411.06327, Nov 2024) — USDT exchange inflow → BTC 1h returns at 1h frequency (strongest horizon). Confirms hourly flow aggregation retains predictive power but via stablecoin inflow channel, not OHLCV-derived NBV.
- `order-flow-cross-sectional-crypto-returns-2026.md` (SSRN 5020002, JFM Jan 2026) — Daily FX-adjusted OFI → cross-sectional crypto returns, Sharpe 3.63 out-of-sample. Sets the daily-frequency lower bound; 1h single-asset is still open.

---

## Why the window was empty

The three priorities are all highly specific niches:
1. P1: basis-gated carry with z-score thresholds and Calmar reporting — no academic group appears to be working in this exact frame.
2. P2: intraday HMM + crypto + strategy backtest — requires proprietary high-frequency data that academics rarely publish papers on.
3. P4: 1h OHLCV-derived OFI on crypto perps — gap confirmed real, not a search artifact.

Academic output at this specificity level should not be expected every 2-week cycle. The search infrastructure is working correctly; the gaps are in the literature.

## Next scheduled search
2026-06-07 (weekly cadence per `quant-research-agent/paper-search-trigger.md`).
