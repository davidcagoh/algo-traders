# Decision 007 — Pre-registered kill criteria: CrossSectionalMomentum

**Status:** active (pre-registered before B2 backtest)
**Date:** 2026-05-16
**Strategy:** `user_data/strategies/CrossSectionalMomentum.py`
**Family:** new — "X" (cross-sectional)

---

## Strategy

Long-only cross-sectional momentum on the 5-coin Binance perp universe.

- Universe: BTC, ETH, SOL, AVAX, DOGE on 4h.
- At each 4h bar, rank coins by trailing 7-day return.
- Enter long the top-1 coin (single position to keep capital concentrated).
- Hold until either (a) the coin is no longer top-1 at the next 24-bar rebalance, or (b) a stop fires.
- Rebalance cadence: every 24 bars (4 days).
- Equal-weight when the strategy is on; flat when no coin clears a minimum momentum threshold (7d return > 0).

This is a degenerate 1-factor model where the factor is "trailing 7-day return rank." The simplest form of the cross-sectional thesis on the smallest possible basket.

---

## Pre-registered kill criteria (binding)

| Code | Criterion | Threshold | Action |
|---|---|---:|---|
| **K1-xs** | Standalone MDD on common-window backtest | > 12% | Hard kill (long-only multi-asset MDD is naturally larger than single-asset trend; 12% threshold matches the empirical multi-asset HMM benchmark of 21% as 'unacceptable' minus headroom) |
| **K2-xs** | Standalone Calmar | < 1.0 over 5y common window | Hard kill (worse than buy-and-hold benchmark adjusted) |
| **K3-xs** | MDB-rp vs current book (T3 + R∧T2) | < 0 robust across all 3 schemes | Don't trade (not portfolio-additive) |
| **K4-xs** | Win-rate degradation under fee correction | post-fee Sharpe < 0.0 | Hard kill (the trade-frequent structure makes this fee-sensitive) |

---

## Why these specific thresholds

- **K1-xs = 12%**: cross-sectional momentum picks one of N coins; when the basket goes through a synchronised drawdown (which crypto majors do), the strategy has nowhere to hide. 12% threshold reflects ~half of R2x's catastrophic 21.47% as the "acceptable but careful" line.
- **K2-xs**: a long-only momentum strategy with Calmar < 1 over 5 years isn't producing risk-adjusted alpha; it's just exposed long.
- **K3-xs**: book is now T3 + R∧T2 (two strategies). The candidate must add to the *combined* book Sharpe under risk-parity. Bar is naturally higher than vs T3 alone.
- **K4-xs**: rebalance every 96 hours = ~14 trades per coin per year × 5 coins = ~70 trades/year. Fees matter. Post-fee Sharpe must remain positive.

---

## Continuous shrinkage formula

For live deployment:

```
size_pct = base_size × pf_factor × calmar_factor × dispersion_factor
```

where:
- `pf_factor = clip(rolling_180d_PF / 1.5, 0, 1)`
- `calmar_factor = clip(rolling_180d_Calmar / 2.0, 0, 1)`
- `dispersion_factor = clip(rolling_30d_basket_return_std / 0.02, 0, 1)` — shrinks when the basket is moving in lockstep (no momentum to exploit)

---

## Status if K1-K4 are passed

If MDB-rp > 0.3 robust AND standalone Calmar > 3 → **★ paper-trade candidate**.
If MDB-rp > 0 robust AND standalone Calmar > 1 → **▲ frontier**.
Otherwise → research-only.
