# Cross-cycle proxy validation — liquid majors substitute

**Not a validation of the actual 9-coin book.** The real universe
(`BTC, HYPE, PAXG, TRX, WLFI, VVV, TON, ZRO, XPL`) cannot be backtested
across cycles: Hyperliquid's API caps history at ~5000 1h candles (~208
days), and `WLFI`/`VVV`/`XPL` launched in 2025 with no prior cycle to test
on any venue. This substitutes `BTC, ETH, SOL, AVAX, ARB, DOGE` (deep
history on Binance) into the identical `shrunk_mean_variance_signed`
construction (same optimizer, same code — `run_portfolio_short_funding.py`
— only the data source and universe differ), across two windows chosen to
*not* repeat the original study's regime shape (the original window,
2025-11-05 -> 2026-06-01, was itself a sharp bear-into-recovery leg, which
is why a short-capable strategy shone there).

## Results

**Bull window (2023-10-01 -> 2024-04-01):** `shrunk_mean_variance_signed`
placed **last of 5** — Sharpe 2.88 vs. equal-weight-long's 4.15, and even
below plain `btc_long` (3.50). Every method made money in a clean bull; the
signed variant made the least, largely because its short components (net
exposure fell to 0.57) worked against a rising market.

**Chop window (2024-04-01 -> 2024-11-01):** every method lost money. The
signed variant lost the least (-18.11% vs. equal-weight's -38.12%, MDD
-22.24% vs. -48.88%) and had the mildest Sharpe (-0.79 vs. -0.88 for
equal-weight) — but "least bad in an all-losing period" is not the same as
beating the decision-011/012 kill criterion ("Sharpe > equal-weight
Sharpe"), which it did clear here, marginally, only because equal-weight's
own Sharpe was more negative.

## Reading

Neither window reproduces the original headline result. The methodology
does not show a robust edge over equal-weight outside the one favorable
window it was originally tested on — in a clean bull it underperforms, and
in chop it merely loses less. This is evidence against the *shrunk-MV +
funding-signed method itself* having a strong general edge; it is not
evidence about the actual traded book, since none of `HYPE, PAXG, TRX,
WLFI, VVV, TON, ZRO, XPL` are in this proxy universe, and the concern
`LEARNINGS.md` originally raised (VVV/HYPE-momentum dependency) is about
those specific tokens, not the liquid majors.

## Verdict

Neither "kill" nor "paper-trade ready." The proxy result argues for
caution about the *construction*, independent of any newer-token concern.
Recommend: hold at `gate_outcome="pending"` for the cross-cycle gate (do
not upgrade to paper-trade eligible on this evidence), and separately let
`WLFI`/`VVV`/`XPL` accumulate real forward history if/when the paper
monitor is deployed — that is the only path to answering the
token-specific question this proxy test cannot.

Reproduce: `./.venv/bin/python analysis/cross_cycle_liquid_majors.py`
