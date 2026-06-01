# Six Layers, Not One: Principled Strategy Evaluation at Laptop Scale

A practitioner's framework for deciding whether a backtest means anything, when your data is short, your trial count is large, and your strategies' return distributions are not Gaussian.

---

## The problem, stated honestly

A single laptop. A free Binance perp data feed. One backtesting framework (Freqtrade). Eight months of part-time work. Roughly two dozen strategies tried, of which a dozen are still alive in some form: trend filters, regime detectors, funding-rate carries, signal conjunctions, pairs, cross-sectional momentum, funding mean-reversion. The question that this kind of project nominally asks is: **do any of them work?**

The answer cannot be a single number. It cannot even be a single chart. Anyone who has spent a season grinding through backtests at retail scale has felt the same recurring failure mode: a strategy looks brilliant on its first 200-trade window, gets enshrined in a leaderboard, gets joined by three variants, and then — quarters later, sometimes only after live capital lights it on fire — turns out to have been a Calmar-shaped optical illusion produced by one good regime, one tail trade, or one happy interaction with the specific six months of history the laptop happened to have downloaded.

The instinct is to defend against this with a single heroic metric. Calmar is popular. Sharpe is popular. Risk-adjusted-anything sounds like it should be enough. It is not. What this essay argues is that **the bar for "this works"** at laptop scale is structurally higher than one metric, and structurally lower than the academic literature's ideal: it is **six interlocking checks**, each fixing the failure mode of the one above it, applied to **pre-registered** kill criteria, evaluated at the **portfolio** level rather than the strategy level, and held against a continuous shrinkage rather than a binary on-off switch.

Five principles follow. They emerged from a specific project — a five-coin Binance perp backtesting setup whose current candidate book is two strategies, `T3 SmaRegime180` and `R∧T2 HmmSmaSlopeV2`, with combined-book MDD of 2.12% over a 5.5-year window. The concrete numbers in this essay come from that project's leaderboard ([backtesting/wiki/_index.md](backtesting/wiki/_index.md)). The principles, the author hopes, do not. **Skipping any one of them produces backtests that look real but aren't.**

---

## Principle 1 — The six-layer evaluation stack

A single metric, no matter how clever, answers a single question. Backtest evaluation has at least six questions, and they form a dependency chain: each layer addresses a failure mode that the layer above can't see.

The stack:

| Layer | Question | Headline metric | Failure mode it fixes |
|---|---|---|---|
| L1 | Did the strategy make money? | Total return, CAGR | (nothing — this is the starting point) |
| L2 | Is the return worth the risk? | Calmar, Sharpe | L1's blindness to drawdown |
| L3 | Is the sample big enough to believe? | SQN | L2's blindness to thin samples |
| L4 | Has the trial count been deflated? | DSR (Deflated Sharpe) | L3's blindness to multiple-testing inflation |
| L5 | Is the path shape lying about the moments? | Ulcer, Martin, skew, kurtosis, CVaR-5% | L4's reliance on Gaussian-shaped returns |
| L6 | Does it add to a book, or just duplicate it? | MDB (Marginal Diversification Benefit), correlation-to-book | L1-L5's strategy-by-strategy framing |

Each layer is necessary because the previous one is solvable by accident.

**L1 → L2.** A strategy with +20% CAGR and a 60% drawdown is not a strategy, it's a leveraged bet. Calmar (CAGR ÷ |MDD|) turns the L1 number into a question about risk. The project's conservative core, `T3 SmaRegime180`, gets a Calmar of 8.76 on the 5.5-year common window: +3.42% CAGR against a 2.21% MDD. The high-return variant `R∧T2 HmmSmaSlopeV2` gets a Calmar of 30.23 (+21.31% CAGR against 6.05% MDD). On L1 they both work. On L2 the second looks *much better* — a fact that L3 immediately complicates.

**L2 → L3.** Calmar is a ratio of two random variables, both estimated on a small sample. Van Tharp's **System Quality Number** — SQN = (mean trade R-multiple ÷ stdev trade R-multiple) × √N — adds the sample-size correction directly. A strategy with 12 trades and a Calmar of 28 has worse SQN than one with 92 trades and a Calmar of 7, because the larger N anchors the estimate. In the leaderboard, `SmaRegime720` posts a headline Calmar of 28.96 on six trades; SQN is 0.69, and footnote ² flags it as unreliable. Same data, different layer, different verdict.

**L3 → L4.** SQN penalises one strategy with a thin sample. It does not penalise *the researcher* for having tested 25 strategies. **López de Prado's Deflated Sharpe Ratio (2014)** does. The intuition: across N independent strategies, the *expected maximum* Sharpe under the null hypothesis grows roughly with √log(N). If you ran 25 backtests and kept the best, the bar that "best" needs to clear is not the standard Sharpe-against-zero null — it is a deflated threshold that already accounts for the 24 monkeys who didn't win. This is the right correction; it is also the layer where laptop-scale evaluation hits its hardest wall, as Principle 2 unpacks.

**L4 → L5.** DSR assumes returns are *moments-tractable* — that mean and variance carry most of the information about the distribution. Crypto trend strategies do not satisfy this. The winning trades in this project, when they fire, are 40–120% multi-month positions on coins that occasionally triple; the daily-wallet kurtosis ranges from 25 to 340 (a normal distribution has kurtosis 3). Sharpe-derived statistics are *systematically* misleading when kurtosis is in this range. Layer 5 introduces metrics whose definitions don't depend on the second moment being a good summary: the **Ulcer Index** = √mean(drawdown_pct²), which measures *time spent underwater*, and the **Martin ratio** = CAGR ÷ Ulcer, which is L2's Calmar replaced with a path-aware denominator. Concretely:

| Strategy | MDD | Ulcer | Reading |
|---|---:|---:|---|
| T3 SmaRegime180 | 2.21% | 1.30 | Tight; recovers fast |
| R2 HmmRegime4Rolling | 7.65% | 4.01 | Chronic underwater |
| C1 FundingCarry | 8.52% | 2.80 | Deep but recovers |

`R2` and `C1` have similar MDD; their Ulcer indices say very different things about what holding them feels like. L2 hides this. L5 surfaces it.

**L5 → L6.** A strategy that passes layers 1–5 still need not belong in a *book*. If it's 0.95 correlated with something already in the book, it adds noise and turnover, not edge. **Marginal Diversification Benefit** is the metric that answers L6: given current book *B* and candidate *C*, does the portfolio Sharpe of *B ∪ {C}* exceed the Sharpe of *B*? In this project MDB is computed under three weighting schemes — equal-weight, risk-parity (90-day trailing vol — the headline), and long-only Markowitz mean-variance — and a strategy is "robustly diversifying" only if MDB is positive under all three. This is the gate that ultimately kept the three variants `R∧T1`, `V2`, `V3` from co-existing in the book despite each looking like a strong frontier point on L1–L5: their pairwise Pearson is 0.96 to 1.00, so they are statistically *one strategy* and only one belongs in any book.

### What this discipline actually changes

In the project, applying L1 through L6 stripped a leaderboard of fourteen serious strategies down to a candidate book of two. Six fell at L2/L3 (Calmar fine, SQN or trade count thin). Three fell at L5 (chronic Ulcer despite acceptable MDD). Five fell at L6 (positive MDB only under risk-parity, or negative everywhere, or correlated > 0.95 with something already in). And — crucially — **all 14 fall at L4** under standard DSR thresholds, which is the subject of Principle 2.

The structural claim is not that every project must compute every layer for every strategy. It is that **a strategy cannot graduate from research to paper-trade on a metric drawn from a single layer**, and that the layers must be applied in order — because each one's *failure mode* is invisible to the layer above. A Calmar leaderboard sorts strategies by L2 alone; that is exactly the kind of sort that produces the optical illusions retail backtesters fall into. The fix is not a better leaderboard. It is a *stack* of leaderboards.

---

## Principle 2 — DSR is necessary but not sufficient at laptop scale

López de Prado's Deflated Sharpe Ratio (2014) is the right idea, framed crisply: every additional strategy you test inflates the expected maximum Sharpe under the null. If you test ten variants and pick the best, you must require the best to clear a threshold that already accounts for the other nine. Skipping this step is how strategy-mill researchers — whether at hedge funds or at laptops — discover "edges" that are nothing but reordered noise.

So the layer is necessary. It is also, at laptop scale, structurally too strict to use as a binding gate.

The DSR test statistic is, roughly:

```
DSR = Φ( (SR_obs − SR_expected_max) · √(N_obs − 1) /
         √( 1 − γ₃·SR_obs + ((γ₄ − 1)/4)·SR_obs² ) )
```

where `γ₃` and `γ₄` are skew and excess kurtosis. The denominator term `(γ₄ − 1)/4 · SR²` is where laptop crypto strategies die. Concretely: the project's nine archived backtests have daily-wallet excess kurtosis ranging from 25 to 340. When kurtosis is 100, the test statistic is roughly five times smaller than it would be for a normal distribution. Even a beautifully-performing strategy gets deflated to "noise."

The numerical result: every one of the project's nine backtests comes back as DSR < 0.005 on a 0.95 signal threshold. Every. Single. One. Including `T3 SmaRegime180`, which has 92 trades across 6.7 years of Binance data covering two bulls and two bears, a Calmar of 7.23 cross-cycle, and a 2.22% MDD whose worst regime (2022) is a contained-failure rather than a blowup — the strategy stays flat for twelve months because its slope-gate refuses to fire.

There are exactly three honest responses to this:

1. **Build a better strategy.** Tempting and pointless — DSR penalises more trials, so adding strategies makes the gate stricter.
2. **Collect more data.** Boring and right. Crypto perpetual history is short (Binance BTC perp starts in 2019; Hyperliquid in 2023); more years are the only structural fix. But the data accumulates at one second per second.
3. **Demote DSR from gate to humility check, and bind on a different set of layers.**

This project chose option 3. The binding gates are L2 + L3 + L5 + L6: Calmar / SQN / Ulcer / MDB-rp. DSR is computed and reported on every result card, but a strategy that passes L2–L3–L5–L6 and fails DSR is still allowed to graduate to paper-trade, provided the failure is the kurtosis-denominator artefact rather than a low observed Sharpe. The discipline is to *write down* the relaxation — in `decisions/005`, the file that pre-registers the evaluation framework — rather than silently retire DSR.

This is not the academically correct answer. The academically correct answer is "wait for more data, then re-run DSR." It is the *practitioner's* answer, and it is defensible on the following ground: **at laptop scale the DSR denominator is dominated not by trial count but by the fat-tailed distributions characteristic of trend-following strategies on volatile underlyings**. The strategies in question are not "winning by luck across many trials." They are winning by riding occasional large moves on fundamentally non-Gaussian markets. The DSR's denominator is correctly diagnosing the latter; it is not — at this kurtosis range — informative about the former.

Two corollaries follow.

**The candidate book is robustly diversifying *and* DSR-rejected, simultaneously.** Both are true. The combined-book MDD of `{T3, R∧T2}` is 2.12% under risk-parity weighting, well under half of the 5.5% kill ceiling; the two strategies' drawdowns occur at uncorrelated times (Pearson 0.07) so their volatilities partially cancel; the marginal diversification benefit of adding `R∧T2` to a `{T3}` book is +0.55 robust across all three weighting schemes. These are not fake numbers, and they are not luck-of-the-shuffle artefacts. They survive the kind of cross-cycle out-of-sample testing that single-window backtests do not. And yet every individual strategy in the book fails DSR. The right reading is **both facts at once**: the book is a defensible candidate and the project should not get cocky about it.

**The right replacement for DSR-as-gate is *pre-registration*, not relaxation.** What DSR exists to catch is the researcher's freedom to test many strategies and report the best. Pre-registration — committing the kill criteria for a strategy to a dated file *before* the first backtest, as documented in [methodology/kill-criteria.md](wiki/methodology/kill-criteria.md) — closes the same loophole by a different mechanism: it eliminates the freedom to silently move thresholds. The project enforces this with files named `decisions/00N-kill-criteria-<strategy>.md`, one per strategy, written before any result is generated. The fourth canonical kill axis (walk-forward Calmar on rolling 365 days) substitutes for the multiple-testing correction by forcing each strategy to clear a held-out fold rather than a deflated bar.

DSR remains in the stack. It is the layer's *concept* — multiple-testing inflation is real — that survives, even when the *number* the formula produces is unusable. Treat it as a humility check, not a gate, and reach for it again when either trade counts cross ~200 with bounded kurtosis or a less kurtosis-sensitive deflator (PBO, CSCV) is evaluated head-to-head. Until then, the binding logic is L2+L3+L5+L6, and the freedom-to-fish problem is addressed by pre-registration.

---

## Principle 3 — Continuous shrinkage beats binary gates

A strategy is rarely simply *broken* or *working*. More often, it is **regime-conditional**: it works in one half of the market cycle and doesn't in the other. Treating it as a binary on-off device throws away most of its information. The right form for a kill rule — or, more generally, for any rule that modulates the strategy's behaviour in response to recent performance — is a **continuous shrinkage** of position size, not a hard switch.

The cleanest evidence in the project is the `HmmSmaSlope` family. The premise: combine the Hidden Markov Model regime detector (which performs well in bulls but is bear-blind) with the SMA-180 slope filter (which is bear-resilient but mostly stays flat). Three variants were tested, differing only in how the slope value modulates position size:

| Variant | Sizing rule | Calmar | MDD | Frontier role |
|---|---|---:|---:|---|
| V1 (binary) | `slope > 0 ⇒ full size, else 0` | 25.01 | 8.21% | aggressive corner; breaches K1 by 2.71pp |
| V2 (linear) | `size = clip(slope / 0.005, 0, 1)` | 30.23 | 6.05% | best Calmar/MDD pair; admitted to book under portfolio-aware K1 |
| V3 (sqrt) | `size = clip((slope / 0.005)^0.5, 0, 1)` | 27.28 | 6.91% | bull-leaning intermediate; 1.41pp past K1 |

Numbers are 5.5-year Binance common-window aggregates from [`backtesting/wiki/_index.md`](backtesting/wiki/_index.md). Three observations.

**First, these are not three different strategies; they are three points on a tradeoff curve.** Pairwise Pearson correlation between V1, V2, V3 is 0.96–1.00. The underlying signal is the same; the sizing exponent is the only knob. Crank it toward infinity and you get a binary gate (V1); crank it toward zero and you get full-size always (the unfiltered HMM-multi); the exponent values 1.0 (V2) and 0.5 (V3) trace a smooth path between.

**Second, the binary gate (V1) is dominated.** On the Pareto frame of (Calmar, MDD), V2 dominates V1 outright — higher Calmar (30.23 vs 25.01) at lower MDD (6.05% vs 8.21%). V3 sits between them. The binary rule throws away signal because it treats a barely-positive slope identically to a strongly-positive one — and barely-positive entries turn out to be roughly as profitable on average as strongly-positive ones in this signal. The cost of V1's harshness is structural, not noise.[^vwindow]

[^vwindow]: A finer-grained bull-window / bear-window decomposition of the same three variants exists for the Hyperliquid 1h substrate (see [`articles/the-ranking-was-the-bug.md`](../articles/the-ranking-was-the-bug.md) and the per-variant cards under [`backtesting/wiki/results/2026-05-10-hmm-sma-slope*.md`](backtesting/wiki/results/)). The common-window Calmar / MDD numbers reported here are the aggregate 5.5-year Binance figures used for paper-candidate selection; they collapse the bull-return vs bear-MDD tradeoff into a single risk-adjusted-return frame.

**Third, the family of continuous-shrinkage forms generalises.** Ravagnani et al. (2026, summarised in the project's papers folder) propose the same shape for robust forecast combination:

```
h_robust = h_standard × (1 − δ/σ²)
```

— continuously shrink the hedge ratio as forecast error grows relative to volatility, rather than discretely switching off at a threshold. The same form is what Dan Davies — in the comment thread under Leek (2025), an informal but pithy reference — was gesturing at when he wrote that the rare ex-quant skill is "the common sense to turn the model off when it is breaking down, with self-discipline to resist the temptation to tinker." Continuous shrinkage operationalises the first half (turn off gradually as evidence accumulates); pre-registration operationalises the second (no tinkering on the way down).

The project applies the same form to its kill criteria. `T3`'s continuous shrinkage formula, pre-registered in [decision 004](backtesting/wiki/decisions/004-kill-criteria-sma-regime-180.md), reads roughly:

```
size_multiplier = min(1.0, pf_factor × calmar_factor × regime_factor)

pf_factor     = clip((rolling_180d_PF - 1.0) / 1.0,           0.0, 1.0)
calmar_factor = clip( rolling_180d_Calmar / 4.0,              0.0, 1.0)
regime_factor = clip(1.0 - abs(log(bull_calmar / bear_calmar)) / log(3),
                                                              0.25, 1.0)
```

A Profit Factor below 1.0 forces zero size; rolling Calmar above 4.0 unlocks full size; a bull-vs-bear Calmar divergence exceeding 3× triggers a quarter-size cap. The strategy never "turns off" except when its own short-horizon evidence says it should — and even then, only smoothly. The discrete kill axes (MDD > 5.5%, six consecutive stops, rolling-365d return ≤ 0 for 30 days, walk-forward Calmar < 2.0) sit *above* the shrinkage, as a safety net for catastrophic regime change.

The principle generalises beyond kill rules into signal construction itself. Any time a strategy turns a continuous signal (slope strength, regime probability, funding rate magnitude, z-score) into a binary trade/no-trade decision via a threshold, ask whether the threshold is structural (e.g. cointegration p < 0.05 is a real test) or arbitrary (e.g. "slope > 0" is just one of infinitely many cutoffs). If arbitrary, the binary version is almost certainly dominated by a continuous version that sizes by signal strength. Three of the project's frontier points come from precisely this transformation; one of them is the only multi-coin strategy that passed the original kill threshold.

---

## Principle 4 — Portfolio-aware kill criteria, not strategy-aware

`T3`'s kill criteria were pre-registered in `decisions/004` before its first backtest. The hard MDD ceiling was set at **K1 = 5.5%**, derived as roughly 3× the strategy's in-sample MDD of 1.74% on a single BTC-only bear window. That multiplier captures a well-documented empirical fact: live MDD typically exceeds in-sample MDD by ~3× under regime shift, because execution slippage, missing fills, regime carry-over, and the survivorship bias of any backtested universe all bias in-sample MDD downward.

So far, so principled. The trouble shows up when the same 5.5% ceiling is asked to gate a *second* strategy entering an *existing* book.

`R∧T2 HmmSmaSlopeV2` posts a 5.5-year standalone MDD of 6.05%. By the letter of `decisions/004`, that's a 0.55-percentage-point breach of K1, and the strategy should be killed. By every other layer of the stack, the strategy is the most attractive candidate on the leaderboard: Calmar 30.23, SQN 2.73, Martin +7.41, MDB-rp +0.55 robust against `{T3}`, Pearson correlation to T3 of 0.07.

The instinct in this situation is to either grandfather the breach in ("close enough") or kill the strategy ("rules are rules"). Both are wrong. The right move is to recognise that **K1 was calibrated on a single-strategy, single-window basis, and the calibration scope does not transfer to portfolio additions**. Two specific assumptions break:

1. **Single-window scope.** The 1.74% in-sample anchor was measured on a six-month BTC-only bear. On the 5.5-year, five-coin common window, `T3` itself widens to a 2.21% MDD — the same strategy, more demanding substrate. Applying the 3× rule consistently on the new substrate would push K1 to ~6.6%, not 5.5%.

2. **Single-strategy scope.** A 6.05% MDD on `R∧T2` that occurs at a *different* time from `T3`'s drawdowns is a fundamentally different beast from a 6.05% MDD that compounds them. With Pearson 0.07, the combined book's MDD is bounded well below the sum of the standalone MDDs.

The empirical confirmation is direct: the combined-book MDD of `{T3, R∧T2}` under risk-parity weighting is **2.12%** over the same 5.5-year window. Under equal weighting it is 3.20%; under mean-variance weighting it is 1.99%. All three are well under K1 = 5.5%. The portfolio is *less* risky than `T3` alone would be at the same gross exposure, because `R∧T2`'s drawdowns are not synchronised with `T3`'s. This is what diversification looks like when it is actually working.

What's needed is a kill rule whose subject is the *book*, not the strategy. The project specifies it in [decision 009](backtesting/wiki/decisions/009-portfolio-aware-k1.md) as a logical predicate:

```
A candidate strategy C may enter book B if EITHER path passes:

  Standalone path (default):
    standalone_MDD(C) ≤ K1_standalone               # 5.5%

  Portfolio path (for K1-breaching candidates):
    standalone_MDD(C) ≤ K1_hard_cap                 # 11.0% = 2 × K1_standalone
    AND combined_MDD(B ∪ {C}) ≤ K1_book             # 5.5%
    AND MDB(C, B) > 0 under all three schemes       # robust positive
    AND MDB-rp(C, B) ≥ 0.30                         # meaningful magnitude
    AND max_pairwise_pearson(C, B) < 0.85           # not a duplicate
```

Each clause is load-bearing.

**`K1_hard_cap = 2 × K1_standalone = 11.0%`** is the absolute ceiling above which no portfolio-justification rescues the candidate. The rationale is mechanical: at MDD > 11%, the strategy concentrates so much standalone risk that the only way risk-parity weighting can neutralise it is by driving its book-weight toward zero — and a strategy at near-zero weight is not meaningfully *in* the book. It's a phantom entry. The worked example is `R2x HmmRegime4Rolling 5-coin`, MDD 21.47%, MDB-rp +0.069: technically robust-positive MDB, but per the hard-cap it cannot enter the book, regardless.

**`K1_book = 5.5%`** equals `K1_standalone` deliberately. The portfolio's combined drawdown is what actually hits live capital, so it inherits the same risk ceiling that `T3` was originally calibrated to. The relaxation is *only* on the per-strategy axis, never on the portfolio axis.

**`MDB-rp ≥ 0.30`** is a magnitude floor, not just a positivity check. A barely-positive MDB does not justify accepting a K1 breach. The threshold is calibrated to be roughly 50% of the headline MDB-rp observed for `R∧T2` (+0.55); strategies whose only claim to admission is a noise-level positive MDB (e.g. `R2`'s +0.010 to +0.012) fail this clause cleanly. The current open case is `X2 CrossSectionalMomentum`, MDD 13.04% (under its family-specific hard cap of 24%) but MDB-rp +0.048: it passes every clause except the magnitude floor, and is correctly held out of the book.

**`Pearson < 0.85`** kills statistical duplicates. The V1/V2/V3 variants of `HmmSmaSlope` cannot all enter — they are one strategy in three guises.

The principle: a kill ceiling calibrated on one strategy's own metrics, on one window, cannot govern decisions about *adding* a strategy to *an existing* book. The right form is a predicate over the post-addition portfolio, with hard bounds (the 11% cap, the 0.30 MDB floor) chosen specifically so that the relaxation cannot be abused into admitting whatever happens to currently look good. Daisy-chaining is explicitly disallowed: the book must always contain at least one strategy that passed standalone K1, and a strategy admitted via the portfolio path can never become the anchor for another portfolio-path admission. The relaxation is bounded; the bounds are part of the rule.

---

## Principle 5 — Anti-complementarity hides in plain sight

The most counterintuitive lesson came from a strategy that looked, on paper, like a textbook example of how to construct a robust signal: combine two mechanistically *different* indicators that should compose into a tighter filter than either alone. The two indicators were the Hidden Markov Model bull-probability (a regime-reactive signal that tags states the market is currently in) and the funding rate (a forward-looking crowd-positioning signal). The composition rule was straightforward: go long only when **both** the HMM signals "bull state" **and** the 8-hour funding rate is negative (shorts paying longs, indicating short crowdedness). The strategy was named `HmmCarry`.

The expected result was that the AND of two independent signals would raise win rate. The actual result, on a six-month bear window across seven Hyperliquid majors, was −19.59% with an MDD of 23.86% — *worse* than either parent alone. The BTC win rate collapsed from HMM-only's 41.1% to HmmCarry's 7.7%, an anti-confirmation rather than a confirmation.

The diagnosis took some unpacking. The two signals are not, in fact, independent in the way that matters for composition. They are both *reactions to the same underlying turn*, but at different lags. The HMM is fitted on returns and is structurally reactive: it tags the bull state *after* the market has moved up enough to shift the posterior. The funding rate is structurally forward-looking: it goes negative *as* short crowdedness builds, which often precedes the turn the HMM eventually picks up. The intersection of "HMM bull" AND "funding negative" therefore fires *precisely* at the moment when the funding-driven mean-reversion has already played out and the HMM-reactive trend confirmation is arriving late — buying near tops, in other words.

The mechanistic confirmation came from a reverse-sign experiment. `HmmCarryReverse` flipped the funding condition: enter on HMM-bull AND funding-**positive** (longs paying = trend confirmation rather than short crowdedness). On BTC the win rate rehabilitated from 7.7% to 35.9%; the total return on the full common window went from catastrophic to +12.67%. The sign flip *worked* — confirming that the original anti-complementarity was real and mechanistic, not a quirk of the bear window. AVAX, however, showed the opposite sign behaviour (−9.79% on the reverse variant), meaning that bull-funding is not a universal trend confirmation across the universe; per-coin signed funding is probably the right next experiment.

But here is what matters for the principle: even the *rehabilitated* reverse-sign variant still failed K1 by a wide margin — MDD 15.09% vs K1 = 5.5%, Calmar 0.78 vs the walk-forward minimum of 2.0. The mechanism diagnosis was correct, the sign correction was directionally validated, and the strategy still cannot enter the book. The take-home is not "we found the right sign." It is **"signal-conjunction strategies are new strategies, and their kill criteria must be pre-registered before, not after, the conjunction is tested."**

Two structural lessons follow.

**First, "AND of two signals" is not a feature engineering operation; it is the construction of a new strategy.** The intuition that "two independent signals → tighter filter" is technically correct only if the signals are independent *with respect to the same time horizon at which the strategy trades*. Two signals that derive from different lags relative to the same underlying turn can compose into a *worse* filter — not just a noisier one, but an actively anti-correlated one. The relevant background literature flags this kind of pathology in different forms: Inan (2025, summarised in the project's papers folder) documents funding-rate predictability with respect to forward returns over specific horizons; Badawi (2025) shows that funding mechanics interact with 4h-bar regime context in ways that depend on which side of the funding clock the bar straddles. Neither paper guarantees that a 4h-cadence intersection of HMM and funding will compose well — and the project's empirical result is that it doesn't.

**Second, the kill criteria for a conjunction must be written before the conjunction is tested.** If `HmmCarry`'s kill rules had been pre-registered as "treat this as a new strategy, with its own MDD ceiling, its own win-rate floor, and its own out-of-sample requirements," the catastrophic bear-window result would have killed it cleanly without provoking the rescue sequence that produced `HmmCarryReverse` and `HmmCarry-per-coin-signed-funding`. The rescue sequence is not necessarily wrong (the mechanism diagnosis is real), but it functions as *post-hoc tinkering* in the Davies sense — exactly the freedom that pre-registration is designed to remove.

The principle, sharpened: **conjunction tests need their own pre-registration; treat `signal_A AND signal_B` as a strategy with its own pre-written kill criteria, not as a feature of either parent.** And do the upstream diagnostic before composing: ask whether the two signals fire at the same lag relative to the underlying turn or at different lags. If different, the conjunction is a *new* signal whose timing properties cannot be inherited from either parent; if same, the conjunction is a *redundant* signal whose marginal information must be measured (MDB-style) before it gets a strategy file of its own.

---

## Coda — What this is not

A six-layer framework, applied honestly, produces a candidate book whose individual strategies fail DSR, whose anchor strategy was killed on its first bear-window read and resurrected only by cross-cycle validation, and whose second member breaches the original kill ceiling by half a point but is justified by a portfolio metric that did not exist in the framework two months ago. The framework is doing real work — but it is also, undeniably, a framework that has co-evolved with its evidence. The honest scope statement is:

- **Laptop-scale, single venue, free data, eight months.** None of the strategies in this book are being run live against real capital yet. Decision 005 calls for a 30-day Hyperliquid paper-trade dry-run on `{T3, R∧T2}` against the pre-registered kill criteria *before* any capital allocation, and that dry-run has not happened.
- **No held-out window has been touched.** Binance perp 2026-06 → 2026-12 has not been downloaded. The protocol is to run the book on it once, document the result verbatim, and never tweak parameters. That is the strongest out-of-sample check available to the project, and it remains future work.
- **The candidate book is a snapshot, not a recommendation.** It will change as data extends and as the per-coin signed-funding, two-leg pairs, and cross-sectional momentum experiments either work or get killed. What is meant to generalise is the *framework*: the six layers, the pre-registration, the continuous shrinkage, the portfolio-aware gate, and the conjunction-as-new-strategy discipline. The numbers will move; the bar should not.

The one-line claim: **the bar for "this works" should be six layers, not one; pre-registered, not retrospective; portfolio-aware, not standalone.** Anything less is a backtest dressed up to look like an edge — which is exactly the result a laptop-scale researcher is structurally most likely to produce, and exactly the kind of result that loses money the first time it meets a regime it didn't have the data to see.
