# [Strategy Name] — YYYY-MM-DD

**Strategy file:** `user_data/strategies/<file>.py`
**Data:** [pair(s), timeframe, date range, candle count]
**Config:** [relevant non-default flags, position sizing, fees assumed]

---

## Thesis

One paragraph: what edge is this strategy trying to capture, and why should it exist in the data?

---

## Metrics

| Metric | Value |
|---|---:|
| **Calmar (primary)** | — |
| **Sharpe** | — |
| CAGR | — |
| MDD | — |
| Trade count | — |
| Win rate | — |
| Avg trade duration | — |
| Turnover (trades/day) | — |

Paste the raw `freqtrade backtesting` summary block below if useful.

### Layer 5 — Tail / Path shape

Generate with: `./freqtrade/.venv/bin/python scripts/eval_layers.py <zip_path>`

| Metric | Value | Reading |
|---|---:|---|
| Skew | — | … |
| Excess kurtosis | — | … |
| Tail ratio (\|P95\|/\|P5\|) | — | … |
| CVaR-5% (daily) | — | mean loss on worst 5% of days |
| Ulcer Index | — | path-aware DD (lower = better) |
| Martin ratio | — | CAGR per unit ulcer |
| Pain index | — | mean abs drawdown |

---

## What worked

- …

## What didn't

- …

## Next test

One concrete follow-up experiment. If the answer is "nothing — this direction is dead," add a `Ruled Out` entry in `wiki/learnings.md` with the mechanism.

---

## Leaderboard update

Add / update the row in `wiki/_index.md` Strategy Leaderboard.
