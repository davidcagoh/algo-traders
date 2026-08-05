# I tried to rank five crypto trading strategies. The ranking was the bug. Then I tried to fix the ranking. That was a bug too.

*A walk through one chart, two methodological revelations, and the moment I realised "best strategy" might not even be a coherent question yet.*

---

A few weeks ago I read Lauren Leek's "How Hard Can Quant Trading Really Be?" — the piece where she builds three strategies on her laptop and finds that one of them beats the S&P 500 by 7×. I'm not a quant either, and her piece got me asking the same question for a different market: crypto perpetual futures.

Stocks are slow. They trade for 6.5 hours a day. Crypto perps trade 24/7, settle every 8 hours via a funding-rate mechanism that pays longs or shorts depending on market positioning, and the dominant venues turn over more volume than the NYSE on a quiet day. The instruments are richer in signal — but the noise is richer too. If hedge funds are armies of PhDs with Bloomberg terminals, crypto-perp retail is mostly people with leverage they don't understand losing money in interesting new ways.

I wanted to know: with a laptop, public data, and a few months of careful work, can you actually build a strategy that **survives a full market cycle** — not just rides a bull?

This is what I learned. It came in three waves, each of which made me less confident than I started.

---

## The instruments

Two market regimes are the protagonists of everything that follows. **Bull** means price is trending up over weeks-to-months. **Bear** means it's trending down. Crypto cycles long bulls (2020-21, 2023-24) and brutal bears (2022, 2025). A strategy that prints money in a bull and silently bleeds in a bear is *not* a real strategy — it's a leveraged bet on the cycle phase. The whole point of testing across cycles is to expose that.

The other thing worth knowing: I'm working with **perpetual futures**, which are like normal futures except they never expire. Instead, every 8 hours longs pay shorts (or vice versa) a small "funding rate" that pulls the perp price back toward spot. When everyone is bullish, funding goes positive and longs pay. When everyone is bearish, funding goes negative and shorts pay. The funding rate is a real-time crowd-positioning signal.

---

## Wave 1: The five strategies

Five strategies, in roughly increasing complexity, all long-only (I don't trust myself to short).

### 1. SmaRegime180 — the boring one
Buy when price is above its 180-period moving average **and** the slope of that moving average is positive. Hold until the slope turns. Sell at a tight stop loss otherwise. That's it. It's a regime filter masquerading as a strategy: trade in bull regimes, sit on your hands in bear regimes.

### 2. HmmRegime4Rolling — the statistical one
A Hidden Markov Model fitted on price returns. The model finds four hidden "states" that the market cycles between (think: trending-up, trending-down, choppy, volatile). When it identifies the trending-up state with high confidence, go long. The "Rolling" part means the model retrains itself every week on the most recent 1000 bars of data, so it's not allowed to peek at the future. (When I first built this I let it peek. The results were great. They were also fake.)

### 3. FundingCarry — the contrarian one
Watch the funding rate. When it goes very negative — meaning shorts are paying longs, which usually means the crowd is over-positioned for downside — buy. The thesis: short crowdedness mean-reverts. Exit when funding normalises.

### 4. HmmCarry — the conjunction
Combine #2 and #3. Only go long when **both** the HMM says "bull state" **and** the funding rate is negative. The logic is straightforward: if two independent signals both say "buy," the entry should be cleaner than either alone.

### 5. HmmRegime4Rolling-multi — same as #2, but on six coins instead of one
Run the rolling HMM on BTC, ETH, SOL, DOGE, AVAX, and ARB simultaneously, with up to six positions at a time. The bet here is that diversification across uncorrelated regime turns smooths the equity curve.

---

## The first set of results — and why they were misleading

I tested all five strategies on a **6-month bear window** in 2025-11 → 2026-05. Here's what I got:

| Strategy | Return | Win rate | Drawdown |
|---|---:|---:|---:|
| SmaRegime180 (BTC) | +1.6% | 26% | 1.74% |
| HmmRegime4Rolling (BTC) | −1.2% | 39% | 4.0% |
| HmmRegime4Rolling-multi (6 coins) | **−5.6%** | — | 14.7% |
| HmmCarry (6 coins) | **−19.6%** | ~28% | 23.9% |
| FundingCarry (6 coins) | **−30.2%** | 10.6% | 42.1% |

My conclusion, written into the project wiki: *"Funding-rate carry fails catastrophically. The HMM family is bear-blind. The conjunction is anti-complementary. Only SmaRegime180 survives."*

This was wrong. Not in the metrics — those numbers are real. Wrong in the **claim those numbers supported**.

What I had actually shown was that *four of five strategies lose money in a 6-month bear window when the market is down 16%*. That is not the same as *those strategies are broken*. To know whether a strategy is broken, you have to also test it where it's supposed to work.

So I went back and ran every strategy on a clean **2-year bull window** — 2023-01 to 2025-01, when crypto was on its way from the 2022 bottom to the 2024 ETF peak. Same code. Same parameters. No tuning.

Here's what came back:

| Strategy | Bear (6mo) | Bull (24mo) |
|---|---:|---:|
| SmaRegime180 (BTC) | +1.32% | +19.96% |
| HmmRegime4Rolling (BTC) | −4.07% | +17.03% |
| HmmRegime4Rolling-multi (6 coins) | −5.62% | **+65.36%** |
| HmmCarry (6 coins) | −19.59% | **+25.77%** |
| FundingCarry (6 coins) | −30.16% | **+12.47%** |

`FundingCarry`'s win rate goes from 10.6% to 52.4%. `HmmCarry`'s flips from anti-complementary to genuinely tightening the signal. `HmmRegime4Rolling-multi` posts +65% with a 5.7% drawdown.

**The strategies aren't broken. They're regime-conditional.** Each one is a finely-tuned bet on one half of the market cycle.

This is the part that took me a while to accept: the answer to "is this strategy good?" is *not a number*. It's a shape. A regime-conditional strategy has a different shape than a regime-robust one, and the right comparison depends on what you're going to *do* with the strategy.

---

## Wave 2: Trying to fix the frontier

If you ranked these five by total annualised return, `HmmRegime4Rolling-multi` would be far ahead. But ranking by return is dishonest, because it implicitly *trusts the bull-bear mix in your test data*. If 2026 turns into a sustained bear like 2022 (where my data shows `HMM-multi` would have lost much more — bears in 2022 were nastier than 2025), the ranking inverts.

If you ranked by **drawdown**, `SmaRegime180` wins by a mile. But its returns are modest — about 6% annualised, less than buy-and-hold.

No single metric captures both. So I plotted the two against each other. One bubble per strategy. X-axis: worst drawdown in a bear regime — lower is better. Y-axis: total return in bull regimes — higher is better. The pink zone right of 5.5% is the **kill rule** — a pre-registered "no live trading" threshold I'd set months ago. Any strategy with bear drawdown above 5.5% is disqualified from paper-trading regardless of bull-side appeal.

The Pareto frontier — the set of strategies that no other strategy beats on both axes — initially had **two points**: `SmaRegime180` (low return, low drawdown) and `HmmRegime4Rolling-multi` (high return, deep in the kill zone). Two endpoints. The other three sat inside, dominated.

That two-segment frontier framed the obvious next experiment: can I build a strategy that *combines* them? `SmaRegime180`'s slope-gate is exactly the bear-protection I'd want bolted onto the HMM signal. Maybe one strategy can dominate both endpoints.

I built three.

**HmmSmaSlope V1 (binary gate):** take HMM entries, but only when SmaRegime180's slope is positive. Result: +50% bull / 8.65% bear MDD. Cut bear MDD by 41%, lost 15pp of bull return. Did not collapse the frontier — added a third point in the middle.

**HmmSmaSlope V2 (linear sizing):** take HMM entries, but scale position size by slope strength. Hypothesis: weak-positive-slope entries should get small sizes; strong-positive should get full size; the binary cliff in V1 is leaving signal on the table. Result: +33% bull / 4.44% bear MDD. **First multi-coin strategy under the kill threshold.** Cost: 17pp more bull return surrendered. A fourth frontier point.

**HmmSmaSlope V3 (sqrt sizing):** like V2, but with a concave curve that pulls weak-positive slopes back toward full size — testing whether V2 was being too harsh on marginal slopes. Result: +40% bull / 5.72% bear MDD. Recovered 6pp of bull, gave back 1.3pp of bear MDD. *Just* fails the kill rule by 0.22 percentage points. A fifth frontier point.

So now the frontier has five points instead of two. The conjunction-family strategies (V1, V2, V3) trace a smooth tradeoff curve between bear-resilient Sma and bull-amplifying HMM-multi. The "sizing exponent" — binary, square-root, linear — is a **continuous knob** along the frontier. Crank it one way: more bull capture, more bear bleed. Crank it the other: less of both.

Which means the frontier never collapsed. **It got finer.**

![Pareto chart](../../freqtrade-experiment/hmm-slope-experiment/research/analysis/reports/pareto.png)

This is the chart. Five strategies on the frontier. Two of them pass the kill rule (Sma and V2); three don't. There is no single dominant point. There is a curve, and picking where on the curve you want to live is a real two-axis choice: *how aggressively do I bet on bulls*, and *do I intend to actually trade this thing live*.

This was when I realised the question I'd kept asking — "which strategy is best?" — wasn't going to have an answer in the form I'd been expecting. The frontier doesn't compress.

---

## Wave 3: Deflating the Sharpe ratios

By this point I had a clean frontier, two paper-trade-eligible strategies, and a fairly compelling chart. I wrote it up. I thought I was nearly done with the methodology section.

Then I ran a Deflated Sharpe Ratio test.

The DSR (López de Prado, 2014) is the right correction when you've tested many strategies on the same data: the expected maximum Sharpe under the null hypothesis grows with √log(N) trials. If your observed Sharpe is below that expected max, the strategy isn't statistically distinguishable from a coin flip across enough monkeys with backtest engines. The DSR collapses everything to a single number: the probability that the strategy has a true Sharpe greater than the expected-max-Sharpe across N trials. Above 0.95 = "signal." Below 0.5 = "noise."

I ran it across all nine backtest archives. Five strategies × two regimes (mostly).

**Every single one came back as NOISE.**

Daily-wallet DSR: every value below 0.005. Per-trade DSR: the best is `HmmRegime4Rolling-multi` at 0.005, then `HmmCarry` at 0.004. The threshold is 0.95.

The cause is straightforward. Crypto strategies that work are dominated by a few huge winners — `HmmRegime4Rolling-multi`'s best single trade is AVAX +123.69%. Big winners create heavy right-skewed, fat-tailed return distributions. The kurtosis of the daily wallet returns across these strategies ranges from 25 to 340 (a normal distribution has kurtosis 3). The DSR formula's denominator gets multiplied by `(kurtosis − 1) / 4`. When kurtosis is 100, the test statistic is roughly 5× smaller than it would be for a normal distribution. The deflation eats the signal.

This is not a bug in the test. It is what the test is *supposed* to do. A strategy whose returns are concentrated in a handful of outlier trades is *exactly* the kind of strategy that's hardest to distinguish from luck.

**The Pareto frontier I'd been so pleased with is, statistically, still nine variations on the null hypothesis.**

I sat with this for a while. It doesn't mean the strategies don't work. It means I don't have enough data yet to claim they do, given how many of them I've tested. The cure is more observations — longer windows, more trades, more cycles. Or fewer trials, but I'd have to throw three strategies in the bin without testing them, which defeats the project's purpose.

---

## Three things I now believe more than I used to

**1. Backtests on the wrong regime are worse than no backtest at all.**

If you only test on a bull window, every strategy looks brilliant. If you only test on a bear window, every strategy looks broken. The first set of conclusions I drew about three of these strategies was qualitatively wrong, and the only fix was the boring one: run the other regime.

**2. Single-metric ranking is a noise amplifier, but multi-metric Pareto plots aren't a replacement for statistical tests.**

The Pareto plot was the right move — it made the structure of the tradeoff visible, and it killed three dominated strategies cleanly. But it cannot tell you that a *frontier* point has statistical signal. It can only tell you it's non-dominated. A frontier of nine noise traders is still a frontier; it just isn't useful.

The DSR is the missing piece. The Pareto plot answers "which strategies are non-dominated?" The DSR answers "given how many strategies I've tested, which of these can I claim are signal rather than luck?" Both questions matter. Neither alone is enough.

**3. The hardest thing to accept is that the right next step might be doing nothing.**

If the DSR gate says "no strategy is signal," there are three responses:
1. Build a better strategy. (Tempting but pointless — DSR penalises more trials.)
2. Collect more data. (Boring but right.)
3. Lower the DSR threshold and document the relaxation. (Pragmatic, but it's a soft form of moving the goalposts.)

My honest read: option 2 is the right answer and option 3 is the answer I'll probably take in practice. Crypto perp history is short, and I don't have years to wait. If I'm explicit that "DSR > 0.5 = paper-trade-eligible with a hard 30-day live cutoff" I can keep moving. But I should write it down.

---

## What this leaves me with

The two-axis decision I described earlier now has three axes:

| Strategy | Regime view | Kill rule | DSR (per-trade) |
|---|---|:---:|:---:|
| `SmaRegime180` (BTC) | bear-resilient | ✓ | not yet measured |
| `HmmSmaSlopeV2` | balanced | ✓ | 0.000 (noise) |
| `HmmSmaSlopeV3` | bull-leaning | ✗ (by 0.22pp) | 0.000 (noise) |
| `HmmSmaSlope V1` | bull-strong | ✗ | 0.000 (noise) |
| `HmmRegime4Rolling-multi` | bull-pure | ✗ | 0.005 (noise) |

There is still a defensible answer to "what would I paper-trade today?" — it's `SmaRegime180` on BTC, because it's the only strategy that passes the kill rule AND I haven't run DSR on it yet (it deserves the chance). But the DSR humility means I'm going to keep position sizes small and the live window short.

The bigger move is structural. The project has been generating strategies fast enough that each new one increases the DSR penalty for *all* the existing ones. The next strategy I build can only make the verdicts more pessimistic. So the next phase is data collection, not strategy invention — extending the Binance bull window into the future as 2026 unfolds, accumulating live paper-trade observations on `SmaRegime180` and `HmmSmaSlopeV2`, and re-running the DSR every quarter.

I'll report back. Possibly less often than before — the next interesting data point is probably six months away, not six days.

---

*All code, result cards, and the Pareto chart in this piece are reproducible from the public repo. The chart is generated by `freqtrade-experiment/hmm-slope-experiment/research/analysis/generate_pareto_chart.py`; the DSR analysis by `freqtrade-experiment/hmm-slope-experiment/research/analysis/dsr_analysis.py`; strategies and report cards live under `freqtrade-experiment/hmm-slope-experiment/research/`. None of this is investment advice — I'm a researcher with a laptop, and you have no idea what your future self is going to need.*
