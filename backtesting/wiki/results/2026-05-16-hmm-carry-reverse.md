# HmmCarryReverse — 2026-05-16

**Strategy file:** `user_data/strategies/HmmCarryReverse.py`
**Data:** Binance perp 5-coin (BTC/ETH/SOL/AVAX/DOGE) `USDT:USDT`, 1h, 2020-09-23 → 2026-05-09 (5.5y, 2054 days, 2 bulls + 2 bears)
**Config:** `config_binance_5coin.json`, `CARRY_FUNDING_EXCHANGE=binance`, `--fee 0.00035`, max-open-trades 5, stop −10%
**Variant note:** Binance funding parquets cover **2022-11 → 2025-02 (~2.3y of 5.5y)** — strategy is flat (funding NaN) outside that window. Same truncation as the R∧C1 HmmCarry common-window run.

---

## Thesis

The 05-10 HmmCarry post-mortem found HMM-bull AND funding-NEGATIVE to be *anti-complementary*: HMM is reactive, funding is forward-looking, intersection picks late-cycle bull lag against early-cycle bear lead. **Inverting the funding sign** (require funding-POSITIVE: longs paying = healthy bull, traders willing to pay carry) should recast the conjunction as confirmation rather than contradiction. If both signals truly point the same direction, the two-signal stack should be additive.

This is the natural alternative flagged in the 05-10 result card open follow-ups (§Reverse-sign HmmCarry).

---

## Metrics

| Metric | Value |
|---|---:|
| **Calmar (CT)** | 0.78 |
| **Sharpe (CT)** | 0.23 |
| Sortino (CT) | 0.59 |
| **SQN** | 0.56 |
| Profit Factor | 1.05 |
| Expectancy | 0.03 |
| CAGR | +2.14% |
| Total return | **+12.67%** |
| MDD | **15.09%** |
| Trade count | 2006 |
| Win rate | 34.8% |
| Avg duration | 1d 5:35 |
| Avg duration winners | 2d 0:14 |
| Avg duration losers | 0d 19:36 |
| Max consec losses | 25 |
| Stop-loss exits | 40 (all losers, −40.14% cum) |
| Market change (B&H all 5) | +1667.42% |

### Layer 5 — Tail / Path shape

| Metric | Value | Reading |
|---|---:|---|
| Skew | +4.99 | right-tailed (rare big wins) |
| Excess kurtosis | +61.87 | very fat tails — Sharpe overstates |
| Tail ratio (\|P95\|/\|P5\|) | 1.07 | balanced |
| CVaR-5% (daily) | −1.00% | mean loss on worst 5% of days |
| Ulcer Index | 7.50 | path-aware DD (high = chronically underwater) |
| Martin ratio | 0.28 | CAGR per unit ulcer (low) |
| Pain index | 5.05 | mean abs drawdown |

_N_obs (daily): 2054_

---

## Comparison vs original HmmCarry (5-coin, common window)

| Strategy | Return | Calmar | SQN | PF | MDD | Ulcer | Win % | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **HmmCarry** (funding-negative, R∧C1) | — | **0.08** | 0.14 | — | **35.46%** | 9.57 | — | — |
| **HmmCarryReverse** (funding-positive) | +12.67% | **0.78** | 0.56 | 1.05 | **15.09%** | 7.50 | 34.8% | 2006 |

The sign flip **halves MDD (35% → 15%), 10× Calmar (0.08 → 0.78), 4× SQN (0.14 → 0.56)**, and turns the strategy from "destroyed by stops" to "marginally profitable." Reversal is the right direction — but the result still sits far below the K1 threshold.

---

## Per-pair (HmmCarryReverse)

| Pair | Trades | Tot Profit % | Win % | Note |
|---|---:|---:|---:|---|
| **DOGE/USDT:USDT** | 314 | **+9.61%** | 35.7% | Best pair. Right-skew benefits DOGE most. |
| **BTC/USDT:USDT** | 404 | +5.00% | 35.9% | Recovered from 05-10's 7.7% win rate / −1.26% catastrophe. Sign flip cleanly rescues BTC. |
| SOL/USDT:USDT | 312 | +4.11% | 33.7% | Modest positive. |
| ETH/USDT:USDT | 445 | +3.74% | 35.3% | Modest positive. |
| **AVAX/USDT:USDT** | 531 | **−9.79%** | 33.9% | Sole loser; eats most of the gain from the other four. AVAX bull-funding signal is anti-correlated with return — opposite of DOGE/BTC. |
| **TOTAL** | 2006 | **+12.67%** | 34.8% | |

**Most striking BTC change:** under HmmCarry (funding-negative) BTC win rate was 7.7%; here it's 35.9%. **The sign flip rescues BTC entirely** — confirming the 05-10 mechanism diagnosis (HMM-bull × funding-negative was buying tops on BTC).

---

## Verdict

### K1 standalone (decisions/004): **FAIL**

- MDD 15.09% ≫ 5.5% threshold (breach by 9.59pp / 2.7×).
- Calmar 0.78 ≪ 2.0 walk-forward minimum.
- Trade count is plentiful (2006), so the failure isn't statistical noise — it's the strategy.

### Decision 009 portfolio gate vs {T3, R∧T2}: **FAIL**

- Standalone MDD breach is 9.59pp over 5.5% (decision 009 allows up to +2.5pp = 8% cap **only if** MDB-rp ≥ 0.30 robust). 15% blows past the hard 11% ceiling outright.
- I did not compute the formal MDB-rp here (correlation matrix not regenerated for this single-row addition), but the strategy is mechanically expected to overlap heavily with T3 + R∧T2 during bull regimes (it only fires in HMM-bull) and contributes nothing in bears (funding-positive rarely sustained). The chronic Ulcer 7.50 / Pain 5.05 — worse than R2 (the K1-killed reference) — means even a positive MDB-rp couldn't carry it through the magnitude floor.
- **Verdict: not admitted to the book.** Stays at ✗.

---

## What worked

- **Sign flip is directionally correct.** Going from −19.59% (Hyperliquid bear) / Calmar 0.08 (Binance common) to +12.67% / Calmar 0.78 confirms the 05-10 mechanism: HMM × funding-negative was systematically buying late-cycle bull tops; the inverse correctly aligns the two signals as confirmation.
- **BTC win rate fully rehabilitated** (7.7% → 35.9%). The single most telling per-coin number from the 05-10 post-mortem is reversed here. Mechanism diagnosis confirmed.
- **DOGE/BTC respond cleanly** to bull-funding-as-confirmation.

## What didn't

- **AVAX has the opposite sign** (−9.79%). Bull funding on AVAX in this window does *not* confirm trend — it precedes drawdowns. This is exactly the per-coin sign heterogeneity the 05-10 card flagged as the obvious next experiment. One-size-fits-all funding gates still destroy alpha that exists per-coin.
- **MDD 15.09% is structural**, not a tail event. 40 stop-loss exits (−40.14% cum P&L drag), max-consec-loss 25, Ulcer 7.50, drawdown 137-day duration. The strategy is chronically underwater during sideways/bear sub-periods even when funding is positive.
- **Funding-parquet truncation** still applies — only 2.3y of 5.5y is signal-active. Net +12.67% is concentrated in the 2022-11 → 2025-02 window. The "common window" framing is misleading for funding strategies; this should be called a "funding-parquet-truncated common window" until decision 010 #3 is done.
- **Tails are very fat** (kurt +61.87). Sharpe 0.23 overstates the smoothness; the actual experience is long flat stretches punctuated by stop-loss clusters.

---

## What this result means for the funding-conjunction line of effort

The sign flip is a *partial rescue* but **not a rehabilitation of the conjunction family**. The 05-10 post-mortem's central insight — that signals are anti-complementary on most coins — is confirmed: simply inverting the funding gate flips the direction of the error on BTC/DOGE/ETH/SOL but doesn't eliminate it on AVAX, and the resulting strategy fails K1 by a wide margin. **The HMM × funding conjunction with a single global sign cannot pass our kill criteria in either direction.** The line of effort isn't fully dead — per-coin signed-funding (open follow-up #2 in the 05-10 card) is now the cleanly-motivated next experiment, and AVAX's reversed sign provides explicit evidence that it's needed. But the *single-rule* version of the conjunction (positive or negative) is closed: both signs have been tested, both fail, and the structural reason (signal heterogeneity across coins) is now twice-confirmed.

**Resolution status of the funding-conjunction line: not rescued, not fully killed — narrowed to "per-coin signed-funding only."** Single-rule conjunction is killed in both directions.

---

## Next test

**Per-coin signed-funding HmmCarry.** Either (a) fit a per-coin sign offline (regress next-bar return on lagged funding within HMM-bull, take sign), or (b) learn jointly with the HMM via a funding covariate. The reverse sign for AVAX in this run + the original 05-10 finding that HYPE/ETH responded to negative funding while BTC didn't gives concrete evidence the heterogeneity is real and exploitable. If even per-coin signed-funding fails to clear K1, declare the family closed.

---

## Leaderboard update

New row in Common-Window leaderboard (R∧C1-reverse). HmmCarry single-rule conjunction family stays ✗ in both sign directions.
