# Autonomous Quant Research Loop — Pattern Notes

Observed across two independent projects (`feishu/`, `backtesting/`) using Claude agents
and scheduled tasks. Both were quant trading tasks. Both converged on the same structural
pattern without being designed together, and both independently discovered the same failure
modes and solutions. Written May 2026.

---

## What was built

### feishu/ — Chinese A-share competition

**Task:** Build an algorithmic trading strategy for the Feishu/Lark Quant Competition.
Universe: Chinese A-shares. Execution: buy at `vwap_0930_0935`, sell at open next day.
In-sample period D001–D484 (~484 days). OOS period D485–D726 (~242 days, data released
May 28 2026, submission deadline June 1 2026). Score formula:
`0.45 × CAGR_pct + 0.30 × SR_pct + 0.25 × MDD_pct`.

**What the agent did autonomously:**
- Indexed 20 academic papers; wrote structured summaries to `wiki/papers/`
- Built 7 concept articles (`wiki/concepts/`) and 6 course articles (`wiki/course/`)
- Catalogued 31 signal ideas; implemented 24 of them in `signals/`
- Built a full competition-mechanics backtester (`eval/backtest.py`) with T+1, lot-size, costs
- Ran parameter sweeps (N, threshold, window, weighting) and documented all results
- Wrote result cards, updated the leaderboard, flagged ruled-out directions

**Current best (IS):** `trend_vol_v4` — Score=0.4024, CAGR=11.75%, SR=1.207, MDD=7.98%.
Primary signal: 60d min-vol selection + 35d trend filter (negative screen) + ERC weights (1/σᵢ).
OOS contingency: `trend_vol_v5` — regime-adaptive wrapper (N=30, threshold=0.00 on detected
bull days; v4 defaults otherwise). Score=0.4026.

**Key discoveries:**
- IC/IR metrics are useless here. Buy at `vwap_0930_0935` happens after the overnight gap
  closes. Reversal alpha is close-to-open; by execution time the opportunity is gone.
  Composite signal with IR=9.64 → CAGR=−54% in actual portfolio backtest.
- All momentum-adjacent signals fail. Any signal that rewards "recently went up" buys
  stocks that then reverse. The only viable direction-agnostic signals are volatility-based.
- `low_vol` (60d, N=20, sell-at-open) was the only signal with positive execution IC (+0.054)
  and positive portfolio return (+8.81% CAGR baseline).
- ERC weighting (+2.7% relative Score) and a softened trend threshold (−0.025 vs 0.00,
  +1.1% Score, MDD 11%→8%) are the two substantive improvements above the baseline.
- IS parameter space is now exhausted. Further tuning is overfitting risk.

**Weekly paper-search agent:** `trig_0172Cps6UTTyFq5uSKY3e5UP` (Wednesdays 5pm ET).

---

### backtesting/ — Hyperliquid crypto perps

**Task:** Build and validate crypto trading strategies on Hyperliquid BTC perpetuals using
Freqtrade as the backtesting engine. Targeting personal crypto holdings; revived April 2026.

**What the agent did autonomously:**
- Indexed 6 papers; wrote summaries to `wiki/papers/`
- Built a custom Hyperliquid OHLCV downloader (`scripts/download_hyperliquid.py`) because
  Freqtrade's built-in `download-data` is disabled for Hyperliquid (`ohlcv_has_history=False`)
- Implemented 4 Freqtrade strategies with full result cards
- Ran H7 bull-window validation for the SmaRegime family (4h data, Feb 2024→Apr 2026)
- Applied full cost modeling: fetched 19,733 historical funding rate periods, applied
  per-trade to all 32 SmaRegime180 trades
- Discovered and documented the fee config bug (see below)

**Current best:** `SmaRegime180` — 4h SMA180 + slope gate. Post-all-costs: +5.18% return,
est. Calmar ~7.2, SQN 1.02, 32 trades, MDD 1.74%, win rate 21.9%.

**Key discoveries:**
- Freqtrade silently ignores the `"fee"` key in `config.json`'s exchange block. The backtester
  uses ccxt's hardcoded Hyperliquid default (0.045%/side) unless you pass `--fee FLOAT` as a
  CLI flag. Use `--fee 0.00035` for actual Hyperliquid taker.
- Funding drag on winning BTC long trades is 5.4× larger than taker fees in dollar terms
  and adversely selected: 85% of funding drag falls on the 7 winning trades (avg hold 25.9d)
  during bull-run periods. Strategy still survives at est. Calmar ~7.2 post-all-costs.
- `TrendFilter200` (SMA200 on 1h = ~8 days) → Calmar −6.84, 90 trades, 12.2% win rate.
  Mechanism: 8 days is too short to define a regime in crypto; every bear-market bounce
  triggers a bull-trap entry.
- `SmaRegime720` (30-day SMA + slope gate, 1h) → Calmar 28.96, but N=6 — statistically
  meaningless. SmaRegime180 (30-day equivalent on 4h) with N=32 is the real data point.

**Weekly paper-search agent:** `trig_013s3hXkiYrSnYh2Qes1KPws` (Sundays 4am ET).

---

## What both projects discovered independently

### 1. Same core strategy pattern

Both best strategies are: **select low-risk characteristic → use regime signal as a negative
screen, not a positive selector.**

- feishu: pick lowest-vol stocks → remove any that are declining (35d trend gate)
- backtesting: hold BTC → only when SMA slope confirms the trend is rising

In both cases, the low-risk characteristic does the actual selection. The regime filter
only prunes. A "positive selector" (pick recent winners, enter when regime flips bull)
failed in both projects.

### 2. Same failure mode on first attempt

Both tried a naive regime filter and had it destroyed by whipsawing:

- feishu: `hmm_regime_vol` (2-state HMM) over-blanked. Score dropped to 0.2937 vs 0.3045
  baseline. Too conservative — blanked too many valid rebalance days.
- backtesting: `TrendFilter200` (SMA200 on 1h). Calmar −6.84, 26 consecutive losses.
  Short window → every bounce in a bear market looks like an uptrend.

Both fixed it the same way: longer window + confirmation gate (slope, threshold, second
condition) that requires the regime signal to be sustained, not just crossed.

### 3. Same IS regime problem

Both IS periods are bear-dominated:
- feishu: D001–D484 is a Chinese equity bear market (~−18% random selection baseline)
- backtesting: Oct 2025→Apr 2026 BTC window is −37.2% buy-and-hold

A strategy that survives IS may simply have been rewarded for *avoiding exposure* in a
down-regime, not for genuine alpha. Both projects flag this as the primary OOS risk.
Both have contingency plans for a bull OOS: feishu has `trend_vol_v5` (expand N on bull days);
backtesting requires H7 — positive Calmar in both bull and bear sub-windows.

### 4. Execution/cost model beats signal refinement

Both projects reached a point where signal refinement stopped mattering because execution
costs dominated:

- feishu: improving IC from IR=5 to IR=9.64 (via PCA whitening, Kalman, LOB features)
  had zero effect on portfolio return. The IC metric was measuring the wrong thing.
  Execution gap explained everything.
- backtesting: funding drag is 21.7% of gross return and is adversely selected to the best
  trades. Reducing the fee assumption from 0.045% to 0.035% changed Calmar by less than
  the funding model did.

The lesson in both cases: get the cost model right before refining the signal.

### 5. Single metric is unreliable at small N; co-primary metrics are mandatory

- feishu added SR and MDD alongside CAGR after discovering a signal could have great CAGR
  with catastrophic drawdown (low_beta: CAGR −16.1%, MDD 39%).
- backtesting added SQN alongside Calmar after `SmaRegime720` produced Calmar 28.96 on
  N=6 trades — statistically meaningless. SQN explicitly penalises thin samples.

Both projects converged on 2–3 co-primary metrics rather than optimising a single number.

### 6. Regime detection is the shared open problem

As of May 2026:
- feishu: OOS D485+ is likely a bull period (Chinese A-share "slow bull" since mid-2025).
  `trend_vol_v5` adds a regime-adaptive layer but the IS bull sample is only 46 days (9.5%).
- backtesting: `HmmRegime4` (4-state GaussianHMM) just implemented. Win rate of SmaRegime180
  is 21.9% — the hypothesis is that a probabilistic regime posterior can improve this.

Both are asking the same underlying question: *can you reliably detect market regime from
price and volume alone, in advance, without look-ahead?*

---

## What made the autonomous loop work

### Wiki as cross-session memory

The agent doesn't need conversation history to resume. Reading `_index.md` + `learnings.md`
gives full project state in 2 minutes. Every session starts from the same baseline.

### learnings.md as a self-correction mechanism

Every ruled-out direction records *why* it failed — the mechanism, not just the metric.
"LOB imbalance failed (IC −0.005)" is useless for future sessions. "LOB imbalance is
contrarian because Chinese retail piles into bids at EOD (FOMO/closing auction effect);
after inversion IC is still weak and doesn't survive execution" is actionable — it prevents
re-exploring variants.

### Session Start Routine as a forcing function

Both CLAUDE.md files mandate: `git pull → read wiki → run baseline eval → report status`
before any substantive work. This catches drift (e.g. the paper-search agent pushing new
content overnight) and ensures the agent's first action is orientation, not assumption.

### Leaderboard with co-primary metrics + dated result cards

Leaderboard is a pointer, not a data store. Each row links to a dated result card in
`results/`. The leaderboard stays readable; full detail lives in the card. This separation
makes it easy to add new strategies without the index bloating.

### Scheduled paper-search agents with curated search scope

Both paper-search agents have explicit "Do NOT search for" sections in their prompts —
directions that are ruled out or already addressed. This prevents the agent from retreading
ground and keeps each weekly run genuinely incremental.

---

## Reusable skeleton for a new project

```
project/
  CLAUDE.md                    # Session Start Routine + behavioral guidelines
  wiki/
    _index.md                  # State dashboard + leaderboard
    learnings.md               # Confirmed / hypotheses / ruled-out + next priorities
    agent-config/
      paper-search-trigger.md  # Prompt + trigger ID for the weekly paper-search agent
    results/                   # Dated experiment cards (linked from leaderboard)
    papers/                    # Paper summaries (populated by scheduled agent)
    reference/                 # Stable canonical references (strategy archetypes, etc.)
  scripts/                     # Data fetching, eval runners
  signals/ (or strategies/)    # Implemented strategies
  eval/                        # Backtester / scoring infrastructure
```

**Key CLAUDE.md instructions:**
1. Session Start Routine: git pull → read wiki → run baseline eval → report status
2. Read `wiki/_index.md` and `wiki/learnings.md` before substantive work; update them
   when facts change
3. Add a result card in `results/` before updating the leaderboard
4. Update `learnings.md` "Ruled Out" whenever a direction is closed — include the mechanism

**Key learnings.md structure:**
- Confirmed Facts (infrastructure, data, scoring discoveries)
- Open Hypotheses (ordered by how much the answer changes next action)
- Ruled Out (mechanism required, not just metric)
- What the Next Experiments Should Prioritise (feeds into paper-search agent prompt)
- What the Next Paper Search Should Prioritise (explicit "Do NOT search for" list)

**Leaderboard design:**
- Co-primary metrics from the start (not a single optimisation target)
- Include N (trade count / sample size) in every row
- Link every row to a dated result card
- Add a footnote explaining why thin-N rows are unreliable
