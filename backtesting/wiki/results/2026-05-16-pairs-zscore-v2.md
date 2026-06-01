# PairsZScoreV2 — 2026-05-16

**Strategy file:** `user_data/strategies/PairsZScoreV2.py`
**Data:** Binance perp 5-coin (BTC/ETH/SOL/AVAX/DOGE) `USDT:USDT`, **4h**, 2020-09-23 → 2026-05-09 (5.5y, 2 bulls + 2 bears)
**Config:** `config_binance_5coin.json`, `PAIRS_V2_A=SOL`, `PAIRS_V2_B=DOGE`, `--fee 0.00035`, max-open-trades 5, default stoploss −10%
**Pair selection:** SOL–DOGE — the highest-passing pair from `scripts/cointegration_preflight.py` (7.4% of rolling 1000-bar windows pass p<0.05 + 12h≤HL≤240h; next best ETH–DOGE at 4.2%; everything else ≤ 3%). Cointegration on crypto majors is structurally weak.

---

## Thesis

V1 (`PairsZScore`) was single-leg synthetic: only the BASE coin traded; the partner side was ignored, making the strategy half-spread-exposed and effectively long-biased. Decision 005 pre-decision Q4 originally locked in two-leg; the 05-16 sprint overrode to single-leg for engineering speed and X1 was killed on cointegration grounds. Decision 010 prerequisite #4 calls for a true two-leg v2 to either rescue X1 (changes the family verdict) or strengthen the kill.

V2 trades **both legs** of the SOL–DOGE pair natively in Freqtrade: the same z-score signal opens long-A/short-B (z<−2) or short-A/long-B (z>+2), both legs share the mean-reversion exit (z crosses 0) and the widening stop (|z|>4).

---

## Metrics

| Metric | Value |
|---|---:|
| **Calmar (CT)** | 0.97 |
| **Sharpe (CT)** | 0.01 |
| Sortino (CT) | 3.37 |
| **SQN** | 0.42 |
| Profit Factor | 1.38 |
| Expectancy ratio | 0.23 |
| CAGR | +0.53% |
| Total return | **+3.04%** |
| **MDD (account)** | **2.91%** |
| Trade count | 13 (5 SOL + 8 DOGE) |
| Win rate | 38.5% |
| Avg duration | 5d 8h |
| Long trades / profit % | 7 / +5.10% |
| Short trades / profit % | 6 / −2.07% |
| Market change (B&H all 5) | +1737.97% |

### Layer 5 — Tail / Path shape

| Metric | Value | Reading |
|---|---:|---|
| Skew | +22.88 | right-tailed (rare big wins) |
| Excess kurtosis | +773.62 | very fat tails — Sharpe overstates |
| Tail ratio (\|P95\|/\|P5\|) | nan | N daily-non-zero < 20 |
| CVaR-5% (daily) | −0.00% | strategy is flat >99% of days |
| Ulcer Index | 0.82 | path-aware DD (low only because mostly flat) |
| Martin ratio | 0.65 | CAGR per unit ulcer |
| Pain index | 0.42 | mean abs drawdown |

_N_obs (daily): 2054_

---

## Comparison vs v1 PairsZScore (same window, same pair)

| Strategy | Return | Calmar | SQN | PF | MDD | Ulcer | Win % | Trades | Legs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| **v1** PairsZScore (SOL-only, partner DOGE) | **+8.66%** | 2.08 | 0.95 | 2.65 | **4.03%** | 0.48 | 50.0% | 10 | 1 |
| **v2** PairsZScoreV2 (SOL + DOGE both legs) | **+3.04%** | 0.97 | 0.42 | 1.38 | **2.91%** | 0.82 | 38.5% | 13 (5 + 8) | 2 |

The two-leg version **underperforms the single-leg version** on every Layer-2 metric (return, Calmar, SQN, PF, win rate) despite having a lower MDD. Reason — see "Framework obstacle" below.

---

## Per-pair breakdown

| Leg | Trades | Tot Profit % | Win Rate | Exit Mix |
|---|---:|---:|---:|---|
| **SOL** (leg A — base of spread) | 5 | **+9.94%** | 80.0% | 4 exit_signal (wins), 1 stop_loss |
| **DOGE** (leg B — partner) | 8 | **−6.90%** | 12.5% | 1 exit_signal, **7 stop_loss** |
| **TOTAL** | 13 | +3.04% | 38.5% | |

7 of 8 DOGE legs hit the per-leg −10% price stop and exited *before* their paired SOL leg. The two legs were never truly atomic.

---

## Framework obstacle (the real headline)

**Freqtrade cannot express two-leg atomic pair trades.** Each pair (instrument) is sized and stop-managed independently. The strategy emits paired entry signals on the same bar, but:

1. **Stops are per-leg, not per-spread.** When SOL moves +30% (a strong divergence widening the spread), DOGE often hasn't moved by the same percentage — *but DOGE's own price-stop at −10% triggers on the DOGE leg in isolation* and closes it. The remaining SOL leg is now naked-directional, no longer hedging anything. That's exactly what the trade data shows: of 8 DOGE trades, 7 hit per-leg stop-loss; the SOL leg kept running and exited cleanly on z-mean-reversion, capturing +9.94% of "alpha" that is mostly directional, not spread-driven.
2. **Sizing is dollar-equal, not β-weighted.** Freqtrade's `custom_stake_amount` could scale by β but the per-leg stoploss can't be β-aware, so the bigger issue (#1) dominates.
3. **No spread-level exit.** Each leg sees only its own price, never the joint z-score, so a divergence widening on one leg's price triggers that leg's stop independently of whether the *spread* z-score is still in the trade.

**What would fix this:** either (a) a strategy framework with native multi-instrument atomic execution (Backtrader's `Strategy.buy(data=X)/sell(data=Y)` with custom risk-management; or QuantConnect / Lean; or rolling our own minimal backtester), or (b) live execution where we manage paired position-state in our own broker layer above Freqtrade and disable Freqtrade's per-leg stops. Inside Freqtrade alone, this strategy's two legs are *operationally independent positions that happen to enter on the same bar* — that is not market-neutral pairs trading.

This is a structural limitation; it's not solved by parameter tuning.

---

## Verdict

### K1-pairs (decision 006, MDD > 8%): **PASS**
MDD 2.91% << 8% threshold. The combination of weak cointegration + per-leg stops actually *limits* drawdown — but only because it limits *anything*, including profit.

### K2-pairs (cointegration p > 0.20 for 30 consecutive days): **FAIL across most of the window**
Preflight: 7.4% of windows pass p<0.05 + HL-in-band; the K2 gate (p<0.20) is the runtime entry filter, and the strategy still only finds 13 trade-pairs in 2054 days. Most of the 5.5y window has p > 0.20 — strategy is *correctly* flat.

### Decision 009 portfolio gate vs {T3, R∧T2}: **FAIL**
- Return is below the noise floor for a 5.5y window: +3.04% / +0.53% CAGR vs T3's +2.83% CAGR at a fraction of the position effort.
- I did not regenerate the correlation matrix for a single-row addition, but v1's MDB-rp was **−0.898** (very-low-vol strategy receives oversized risk-parity weight without enough return). V2 is structurally similar: low volatility (Ulcer 0.82, flat >99% of days), low return — same RP-weight problem. MDB-rp is expected to remain deeply negative.
- 13 trades over 5.5y is far below DSR's effective-sample threshold; any "edge" reading is statistical noise.

### Status: **✗ (killed, with v2 strengthening rather than rescuing v1's verdict)**

---

## What the two-leg version changed about the X1 family verdict

**Verdict strengthened, not rescued.** Three new pieces of evidence:

1. **The cointegration premise is genuinely weak on crypto majors**, not an artifact of v1's single-leg execution. V2 found only 13 trade-pairs in 2054 days despite trading both sides — the K2 cointegration gate stays open for most of the window. The preflight pass-rate of 7.4% for the best pair (SOL-DOGE) is the real ceiling on this family's trade count.
2. **V1's +8.66% / Calmar 2.08 was directional, not spread-driven.** When v2 forces the partner leg to actually trade, the partner loses −6.90% (DOGE: 7 of 8 stopped out at per-leg −10%) and the net falls to +3.04%. V1 captured the SOL-side directional move during the 2021 bull and the late-2024 SOL run; the "pairs" framing was incidental.
3. **Freqtrade is the wrong tool for atomic pair trades.** Per-leg stops break the spread-neutrality assumption. This is a structural finding worth recording: any future pairs strategy in this repo needs either a different framework or a custom risk-management layer above Freqtrade. (Decision 006 K6 — the modeling-gap rule — applies: v1 results are flagged "modeling-biased toward the active leg," but the underlying cointegration verdict isn't changed.)

The family stays ✗. The standalone metric (low MDD) looks superficially fine but the strategy is a long-duration flat curve punctuated by 13 trade-pairs whose joint behavior was never truly market-neutral. Cointegration on crypto majors is too weak to support a tradeable pairs family in this universe.

---

## Limitations of this v2 implementation

- **Equal-dollar sizing, not β-weighted.** Rolling β on SOL-DOGE ranges roughly 0.4–1.3 in the preflight; equal-dollar deviates from β-weighted by up to ±30%. Mechanically fixable via `custom_stake_amount` per-leg with β passed through `self.custom_info` — but per-leg stops (the headline problem) would remain. Wasn't worth the complexity given the verdict.
- **Single pair (SOL-DOGE).** Multi-pair trading would compound overlap (DOGE appears in ETH-DOGE) without rescuing the cointegration premise. Other pairs have even lower pass rates.
- **Per-leg stops (the central problem).** See "Framework obstacle" above.

---

## Leaderboard update

New row X1v2 in Common-Window leaderboard. X1 status remains ✗ — kill verdict strengthened by v2 evidence (cointegration genuinely weak; v1's metrics were directionally inflated by single-leg execution).
