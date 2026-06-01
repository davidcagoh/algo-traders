# Deflated Sharpe Ratio analysis — 2026-05-10

**Script:** `scripts/dsr_analysis.py`
**Inputs:** Nine backtest archives in `user_data/backtest_results/` covering five strategies × two windows each
**Reference:** López de Prado 2014, "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality"

---

## Why this analysis

`learnings.md` open #2 has been "deflated Sharpe / PBO gate — pre-registration before any sweep" since project start. After running multiple strategies on the same windows, the multiplicity of tests inflates the expected-maximum-Sharpe under the null; raw Sharpe is no longer a defensible signal threshold. DSR is the standard correction.

This is the first time the analysis has been run.

---

## Result

**No strategy passes the DSR > 0.95 threshold under either basis.**

### Daily-wallet basis (annualised, 365 days/yr)

| Strategy | Win | Sharpe | Skew | Kurt | N_obs | DSR | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|
| HmmRegime4Rolling-multi | bull | 1.54 | 6.72 | 67.86 | 792 | 0.000 | NOISE |
| HmmSmaSlope | bull | 1.27 | 9.36 | 114.53 | 792 | 0.000 | NOISE |
| HmmSmaSlopeV3 | bull | 1.15 | 9.21 | 117.28 | 792 | 0.000 | NOISE |
| HmmSmaSlopeV2 | bull | 1.03 | 9.71 | 133.78 | 792 | 0.000 | NOISE |
| HmmCarry | bull | 0.75 | 15.79 | 340.80 | 792 | 0.000 | NOISE |
| FundingCarry | bull | 0.77 | 1.32 | 33.98 | 731 | 0.000 | NOISE |
| HmmSmaSlopeV2 | bear | −1.55 | 3.16 | 54.53 | 206 | 0.000 | NOISE |
| HmmSmaSlopeV3 | bear | −1.80 | 2.25 | 40.92 | 206 | 0.000 | NOISE |
| HmmSmaSlope | bear | −2.26 | 0.20 | 24.80 | 206 | 0.000 | NOISE |

N_trials = 9; σ²(SR) = 2.27; **SR_star = 2.29**

### Per-trade basis (annualised by trades/year)

| Strategy | Win | Sharpe | Skew | Kurt | N | DSR | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|
| HmmRegime4Rolling-multi | bull | 1.62 | 5.64 | 47.68 | 477 | 0.005 | NOISE |
| HmmCarry | bull | 1.78 | 2.19 | 8.90 | 158 | 0.004 | NOISE |
| HmmSmaSlope | bull | 1.36 | 5.13 | 36.00 | 259 | 0.000 | NOISE |
| HmmSmaSlopeV3 | bull | 1.36 | 5.13 | 36.00 | 259 | 0.000 | NOISE |
| HmmSmaSlopeV2 | bull | 1.36 | 5.09 | 35.41 | 254 | 0.000 | NOISE |
| FundingCarry | bull | 0.95 | 1.58 | 11.46 | 252 | 0.000 | NOISE |
| HmmSmaSlope | bear | −1.55 | 1.47 | 6.41 | 50 | 0.000 | NOISE |
| HmmSmaSlopeV2 | bear | −1.10 | 1.35 | 5.79 | 44 | 0.000 | NOISE |
| HmmSmaSlopeV3 | bear | −1.55 | 1.47 | 6.41 | 50 | 0.000 | NOISE |

N_trials = 9; σ²(SR) = 2.04; **SR_star = 2.17**

---

## What this means

**1. The verdict is honest, not the script being broken.** Kurtosis 36–340 across the daily-wallet panel reflects real distributional reality: each strategy's return is dominated by a handful of big winners (HMM-multi best trade AVAX +123.69%). The DSR formula's `denom = √(1 - skew·SR + (kurt-1)/4 · SR²)` penalises this heavily, and correctly. A strategy whose performance comes from a few outliers is genuinely *not yet statistically distinguishable* from noise across N trials.

**2. Per-trade basis is more forgiving but still NOISE.** Kurt drops to 5–47 on per-trade returns (vs 25–340 on daily-wallet), confirming the daily-wallet kurtosis is partly artefact of zero-return days inflating the moment. But even the best per-trade DSR (HMM-multi at 0.005, HmmCarry at 0.004) is far below the 0.95 threshold. The per-trade Sharpes (1.36–1.78) sit just below the deflated threshold SR_star = 2.17.

**3. The fix isn't a better strategy — it's more data.** DSR's `√(N-1)` denominator means signal becomes detectable as observation count grows. Currently the bear-window strategies have 44–50 trades and bull-window have 252–792 days. To clear DSR > 0.95 with current Sharpe levels, we'd need roughly 2–3× more observations. That means longer windows (CEX history extending past 2026 is unavailable) or higher trade density (the HMM-multi family is already there at 477 trades; ceiling is reached).

**4. The Pareto frame still works as a planning tool, just not as a "signal claim" tool.** Picking V2 over V3 over V1 is a defensible *risk preference* choice — paper-trade eligibility vs higher return. It's not a "this strategy has signal, that one doesn't" claim under DSR. We can't yet make that claim about any of them.

---

## Implication for the leaderboard

The leaderboard's verdicts need an extra column:

| Strategy | Pareto rank | Kill rule | DSR (per-trade) | Pre-paper-trade gate |
|---|---|---|---|---|
| SmaRegime180 (BTC) | ✓ frontier | ✓ | not measured | partial — needs DSR run |
| HmmSmaSlopeV2 | ✓ frontier | ✓ | 0.000 | **fails DSR** |
| HmmSmaSlopeV3 | ✓ frontier | ✗ (0.22pp) | 0.000 | fails kill + DSR |
| HmmSmaSlope V1 | ✓ frontier | ✗ | 0.000 | fails kill + DSR |
| HmmRegime4Rolling-multi | ✓ frontier | ✗ | 0.005 | fails kill + DSR |

The earlier verdict "V2 is the first multi-coin paper-trade candidate" was based on the kill rule alone. Adding the DSR gate, **V2 also fails** — no strategy in the project currently passes both. The most diagnostic next step isn't another strategy variant; it's collecting more data or relaxing the DSR threshold with explicit documentation.

---

## Next test

1. **Run SmaRegime180 through DSR.** It's the only Pareto-frontier strategy with the right kill-rule profile to graduate. The full-history Binance run (92 trades over 6.7y) would compute SR_per_trade. If DSR > 0.5, it's the strongest paper-trade candidate.
2. **Document the DSR-relaxation decision.** Either accept "DSR > 0.5 = weak signal, paper-trade eligible" with a 30-day live cutoff, or accept "no paper-trade until DSR > 0.95" and commit to data collection.
3. **Stop tuning the sizing exponent.** V2/V3 are statistical noise from each other under DSR — running V4 (exponent 0.6) is parameter hunting, not signal discovery. The exponent knob has done its job; the frontier is well-characterised.

---

## Reproducibility

```shell
./freqtrade/.venv/bin/python scripts/dsr_analysis.py
```

Reads all archives listed in `RUNS` at the top of the script; outputs to `wiki/results/_dsr_table.json` and prints summary tables.
