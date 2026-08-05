# Mean-Variance Research Findings

## Confirmed

- The 9-coin universe screen selected BTC, HYPE, PAXG, TRX, WLFI, VVV, TON,
  ZRO, and XPL with average pairwise daily-return correlation 0.30 and maximum
  0.54 over 2025-11-05 through 2026-06-01.
- The first long-only shrunk mean-variance baseline was cash-dominated: Sharpe
  2.33 and Calmar 4.41, but only 16% average exposure and 2.74 effective assets.
- With `mean_shrink=0.50` and `risk_aversion=1.0`, the short-window long-only
  sweep reached +126.59%, Sharpe 3.65, Calmar 30.35, MDD 21.47%, 82% average
  exposure, and 4.25 effective assets.
- The signed variant returned +122.61% with Sharpe 3.86, Calmar 35.97, MDD
  17.23%, 1.01 average gross exposure, 0.08 average net exposure, and 5.42
  effective assets. Funding PnL was +4.72%.
- The signed optimizer needs a robust seed. A zero initialization could falsely
  accept all-zero weights under the absolute gross-exposure constraint; the
  current implementation uses split positive/negative variables and a
  signal-seeded fallback.
- PC-neutral pair stat-arb was mildly positive but too sparse to be compelling
  (+0.38%, Sharpe 0.71, active on 0.3% of bars). Individual PCA-residual mean
  reversion failed after fees (best -3.66%, Sharpe -0.49).

## Caveats

- All headline results use a short, favorable window and may depend heavily on
  VVV/HYPE momentum. Cross-cycle validation is required before another paper run.
- The signed test does not model borrow constraints, liquidation mechanics,
  slippage, or margin interest.
- Funding was omitted from the PC-neutral sweep after API rate limiting.

See [`analysis/results/`](analysis/results/) for preregistered decisions and
generated evidence.
