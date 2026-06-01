# Decision 006 — Pre-registered kill criteria: PairsZScore

**Status:** active (pre-registered before B1 backtest)
**Date:** 2026-05-16
**Strategy:** `user_data/strategies/PairsZScore.py`
**Family:** new — "X" (cross-sectional / pairs)
**Per pre-decision Q4 (decision 005):** Two-leg `informative_pairs` was originally locked in as full-fidelity execution. **V1 ships as single-leg synthetic** for engineering pragmatism; two-leg fidelity flagged as upgrade in result card. Modeling gap: V1 captures spread P&L from one leg only (the BTC side), so absolute return is roughly halved vs a clean spread trade. Vol is also roughly halved, so Sharpe and MDB-rp are approximately preserved.

---

## Strategy

Cointegration-based mean-reversion on a hedged spread between two crypto perpetuals.

- Universe: 5-coin Binance perp (BTC/ETH/SOL/AVAX/DOGE), 4h.
- Pair candidates: BTC-ETH, BTC-SOL, ETH-SOL (preflight selects which pair(s) qualify).
- Spread: `log(P_A) − β·log(P_B)` with β refit weekly on prior 60d only (walk-forward).
- Entry: when |z-score| > 2.0 (where z is computed against rolling 30d spread mean/std).
- Exit: when z crosses 0, OR stop at |z| > 4.0, OR time-stop at 3 × OU half-life.
- Position: long the underpriced leg only (single-leg synthetic v1).

---

## Pre-registered kill criteria (binding)

These thresholds were set *before* the first backtest run, anchoring our prior on what would constitute failure.

| Code | Criterion | Threshold | Action |
|---|---|---:|---|
| **K1-pairs** | Standalone MDD on common-window backtest | > 8% | **Hard kill** (looser than T3's 5.5% — pairs MDD shape includes both directions of the spread, naturally larger; 8% is the bear-Hyperliquid empirical reference) |
| **K2-pairs** | Cointegration p-value drift | > 0.20 for 30 consecutive days in preflight | **Hard kill** (the underlying premise of the strategy has broken) |
| **K3-pairs** | OU half-life drift | > 3× rolling 60d median | **Hard kill** (spread dynamics no longer mean-revert on tradeable horizon) |
| **K4-pairs** | β-flip during walk-forward | β changes sign between adjacent fits | **Hard kill** (hedge ratio is unstable) |
| **K5-pairs** | MDB-rp vs current book | < 0 robust across all 3 schemes | **Don't trade** (not portfolio-additive; still document as research) |
| **K6-pairs** | Single-leg → two-leg modeling gap | If two-leg V2 ever produces results materially different from V1, V1 results are flagged "modeling-biased" | **Re-evaluate** rather than kill |

---

## Why these specific thresholds

- **K1-pairs = 8%**: T3's K1 = 5.5% was calibrated against single-asset trend-following on BTC. Pairs trades have inherently larger MDD because they bet on both directions of the spread — one side blows up first when the cointegration breaks. 8% is the empirical threshold from the cross-cycle Hyperliquid HmmCarry run (similar two-sided structure, blew up at 23.86%; we want substantial headroom above that for our cleaner version).
- **K2-pairs**: Engle-Granger p-value monitoring is standard pairs-trading discipline. 30 consecutive days at p > 0.20 is the canonical "the spread is no longer stationary" signal.
- **K3-pairs**: OU half-life ~12h-10d in the preflight filter; 3× drift would mean half-life > 30d, which exceeds our time-stop horizon (3× half-life) — strategy can never exit profitably.
- **K4-pairs**: β sign-flip means the hedge has inverted; the trade is no longer market-neutral and any P&L is incidentally directional.

---

## Continuous shrinkage formula (analogous to decision 004)

For live deployment after a paper-trade period, position size is shrunk by:

```
size_pct = base_size × pf_factor × calmar_factor × cointegration_factor
```

where:
- `pf_factor = clip(rolling_180d_PF / 1.5, 0, 1)`
- `calmar_factor = clip(rolling_180d_Calmar / 2.0, 0, 1)`
- `cointegration_factor = clip((0.2 - rolling_30d_p) / 0.2, 0, 1)` — shrinks to 0 as p → 0.2

---

## Quarterly review

If V1 lands on the leaderboard, quarterly walk-forward review covers:
1. β stability across walk-forward fits.
2. Half-life stability (no drift > 3×).
3. P-value distribution (no consecutive runs > 0.20).
4. MDB-rp re-computation vs updated book.

A walk-forward break of any criterion above triggers a hard kill (size → 0) until re-validated on at least 90d of fresh data.

---

## Status if K1-K6 are passed

Strategy graduates to **▲ frontier** automatically (if MDB-rp > 0 robust) or **★ paper-trade** (if MDB-rp > 0.3 robust AND standalone Calmar > 5).
