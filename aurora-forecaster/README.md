# Aurora Forecaster

Forecasting-archetype experiment, separate from `freqtrade-experiment/`
because it isn't a Freqtrade strategy: [DecisionIntelligence/Aurora](https://huggingface.co/DecisionIntelligence/Aurora)
([arXiv:2509.22295](https://arxiv.org/abs/2509.22295)) is a pretrained
multimodal (time series + text + image) generative forecasting foundation
model, not a rule-based signal on OHLCV. See `wiki/concepts/strategy-archetypes.md`
for why this doesn't fit any existing archetype — everything else in this repo
trades a current mispricing back toward an anchor; Aurora predicts forward
returns directly.

## Status

Smoke-tested locally on Apple Silicon (M3, MPS backend) 2026-08-06: real
pretrained weights load from Hugging Face, unimodal forward pass runs, output
shape `(batch, num_samples, horizon)` as expected. Multimodal (text-context)
path not yet exercised — no text-context data source exists in this repo yet;
that's the actual design gap, not the inference call itself.

### Rolling forecast

`scripts/rolling_forecast_btc.py` (2026-08-07) wraps the proven unimodal call
in a walk-forward loop over real BTC OHLCV, appending each origin's forecast
(summary mean/std per horizon step, not raw samples) to
`artifacts/btc_unimodal_forecast_ledger.jsonl` — an append-only ledger
modeled on `evaluation-framework`'s `TrialRecord` pattern but scoped to what
a forecast has at generation time (no realized returns yet). No text context
— that's still the multimodal/source-alignment gap above.

### Scoring

`scripts/score_forecast_ledger.py` (2026-08-07) scores every record in the
forecast ledger against realized BTC prices, writing
`artifacts/btc_unimodal_forecast_scored.jsonl`. Built as a small
self-contained module in this repo, not an `evaluation-framework` extension
— that package's Sharpe/DSR/PBO stack assumes realized trade/portfolio
returns, which a probabilistic price forecast doesn't have.

- `aurora_forecaster/realized.py` aligns a `ForecastRecord` to realized
  lookback + horizon closes by timestamp (`origin_timestamp` is the last
  lookback bar, per `forecast_ledger.py`'s docstring).
- `aurora_forecaster/scoring.py` — closed-form Gaussian CRPS (the ledger
  stores mean/std, not raw samples or quantiles, so CRPS is computed
  analytically rather than empirically), MASE (Hyndman & Koehler, scaled by
  the lookback window's own lag-1 naive error), skill score vs. a
  random-walk-flat baseline, and calibration coverage from standardized
  residuals. No scipy dependency — Gaussian CDF/PDF via `math.erf`.
- `aurora_forecaster/compare.py` — Diebold & Mariano paired test. Uses a
  Bartlett/Newey-West kernel long-run variance estimator (2026-08-08) rather
  than the plain sample variance, since `h`-step-ahead rolling-forecast
  origins overlap in time and induce serial correlation the plain form
  understates — an ablation sweeping daily-cadence origins against a 96h
  horizon would otherwise report false-positive "significant" results.
- `aurora_forecaster/data/price.py::fetch_btc_ohlcv` gained an optional
  `since` (ms epoch) param with pagination past Binance's 1000-row cap, to
  reconstruct a specific historical span rather than "most recent N bars".

### Stream ablation

`aurora_forecaster/ablation.py` (2026-08-08) defines `StreamConfig` — which
text sources (`sources`) or real-image covariate sources (`vision_sources`)
feed one walk-forward run (`UNIMODAL`, `GDELT_ONLY`, `CURRENTS_ONLY`,
`GDELT_CURRENTS`, `FUNDING_ONLY`, `DXY_ONLY`, `SPY_ONLY`, `FUNDING_VISION`,
`DXY_VISION`, `SPY_VISION` in `STANDARD_CONFIGS`; Alpha Vantage is excluded
from the standing rotation, see Data sources below) — and per-config
ledger/scored-ledger file naming (`btc_{config.name}_forecast_ledger.jsonl`,
which reduces to the existing filenames for `unimodal`). Sources don't
combine with each other, with the news sources, or with their own
text/vision variant yet — single-source-first, same incremental approach
used for `gdelt`/`currents` before `gdelt+currents` was added.
`rolling_forecast_btc.py` and `score_forecast_ledger.py` both read a
`STREAM_CONFIG` module constant (default `UNIMODAL`) — edit it and rerun
both scripts to build a non-default config's ledger, same "edit the
constant, rerun" convention used for `LOOKBACK`/`HORIZON` elsewhere in this
file.

`aurora_forecaster/ablation_core.py` holds the actual N-way comparison logic
(per-config summary stats, all-pairs Diebold-Mariano, markdown report) with
zero aurora-specific types — the literal promotion candidate for
`time-series/forecast_eval/` once a second project needs stream ablation
(see `wiki/decisions-archive.md`'s eval-package-boundary decision,
2026-08-08).

`scripts/run_ablation.py` builds the report across every `STANDARD_CONFIGS`
config that has a scored ledger yet, printing it and writing
`artifacts/btc_ablation_report.md`. Pure local file I/O, no network/model.

**First real result (4 BTC origins, 2026-07-19 to 2026-07-31, 96h horizon,
scored 2026-08-07):** skill vs. naive-flat is mixed (−0.26 to +0.41 across
the 4 origins — no consistent edge yet at this sample size), but
**calibration is badly overconfident**: nominal 50/80/95% central intervals
achieve only ~20/28/38% empirical coverage, and mean standardized residual
is −1.8 (not ~0). The model's stated uncertainty (`sample_std`, from only
10 samples) understates real 96-hour-ahead uncertainty substantially. Only
4 origins — treat as a first signal to watch, not a settled result; revisit
once more origins accumulate.

## Compute target

Local (Apple Silicon, CPU/MPS) first — the model is 0.2B params (~800MB F32),
small enough that a GPU cluster is unnecessary for development and smoke
testing. A university Slurm GPU cluster is available if/when local becomes a
real bottleneck (e.g. sweeping many text-context variants, or running the
full backtest history in parallel) — not needed yet.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Version pins

The Hugging Face model card recommends `torch==2.4.0` /
`transformers[torch]`, but `torch==2.4.0` has no wheel for Python 3.13, so
this project uses `torch>=2.6` instead. That surfaced a real incompatibility:
`transformers>=5` changed its internal weight-tying API
(`all_tied_weights_keys`) in a way `aurora-model==0.2.0`'s `from_pretrained`
doesn't handle, crashing on load. Pinned `transformers<5,>=4.44` (the range
contemporaneous with the model card's own torch pin) — confirmed working via
`scripts/smoke_test.py`.

## Tests

```bash
pytest -q
```

Fast unit tests only (`tests/`) — no network or model weights required.
`scripts/smoke_test.py` is a separate manual script: it downloads real
weights from Hugging Face and runs one forward pass, so it's excluded from
the automated suite by design.

```bash
python3 scripts/smoke_test.py
```

## Layout

```text
aurora-forecaster/
├── aurora_forecaster/   # device selection, (future) walk-forward eval wrapper
├── tests/                # fast unit tests, no network/weights
├── scripts/              # manual scripts needing network/weights/compute
└── pyproject.toml
```

## Target securities

BTC and SPY — chosen over the actual Hyperliquid book (`WLFI`/`VVV`/`XPL`
etc.) because they're in-distribution for Aurora's own pretraining domain
(TimeMMD pairs time series with macro/economy-style expert reports, not
asset-specific chatter) and have genuinely deep price and text history. This
is a feasibility test — does multimodal beat unimodal at all — before ever
pointing this at the illiquid book.

## Data sources

- **Price:** `aurora_forecaster/data/price.py` — `fetch_btc_ohlcv` (ccxt/Binance,
  per `wiki/concepts/data-sourcing.md`'s default order) and `fetch_spy_ohlcv`
  (yfinance). Both confirmed working against real endpoints 2026-08-06.
- **Text — GDELT** (`aurora_forecaster/data/text_gdelt.py`): free, no API
  key, global news/event database. Domain-matches Aurora's pretraining style.
  Confirmed working 2026-08-06 (`{"articles": [...]}`). Not ticker-tagged —
  needs keyword/entity filtering to isolate BTC- or SPY-relevant events.
- **Text — Alpha Vantage `NEWS_SENTIMENT`**
  (`aurora_forecaster/data/text_alphavantage.py`): free tier, API key
  required, directly ticker-tagged with a sentiment score. Confirmed working
  2026-08-06 via `scripts/alpha_vantage_smoke_test.py` (key loaded from repo
  root `.env`, never printed) — real BTC articles returned. **Free tier is
  25 requests/day, 1 req/sec** — hit mid-script on the SPY call. Too tight
  to build a walk-forward loop around directly; kept in the comparison for
  its sentiment field, not as a primary source.
- **Text — Currents API** (`aurora_forecaster/data/text_currents.py`): free
  tier, API key required (no credit card), 1,000 requests/day, commercial
  use allowed. Confirmed working 2026-08-06 via
  `scripts/currents_smoke_test.py` — 20 real articles each for BTC and SPY
  keyword queries. Metadata-only (no sentiment), which is fine since we
  tokenize raw text, not a sentiment score.
- **Text — Guardian Open Platform**
  (`aurora_forecaster/data/text_guardian.py`): free tier, API key required
  (non-commercial), 5,000 requests/day. Confirmed working 2026-08-06 via
  `scripts/guardian_smoke_test.py` — 10 real, on-topic business-section
  articles each for BTC and SPY queries. Single-publisher (Guardian's own
  journalism only), but professionally curated business/economics coverage —
  domain-matches Aurora's TimeMMD pretraining style arguably better than any
  of the other three. Kept ready-but-unused per standing decision: verified
  it works, not yet wired into any pipeline — actually use it once the
  GDELT/Alpha Vantage/Currents comparison shows a need for it.
- **Funding rate — Hyperliquid** (`aurora_forecaster/data/text_funding.py`):
  BTC perp funding rate via Hyperliquid's free `/info` endpoint, no API key,
  no documented daily cap (informal throttling only — same 6-attempt/3s-base
  backoff as `text_gdelt.py`). Fetches a single nearest-at-or-before value
  per origin (no lookahead), not full history. Suggested by Ethan
  (2026-08-08) as a natural non-price series worth testing.
- **DXY** (`aurora_forecaster/data/price.py::fetch_dxy_ohlcv`, ticker
  `DX-Y.NYB`): dollar index via yfinance, same pattern as `fetch_spy_ohlcv`
  (shared `_fetch_yfinance_ohlcv` helper). Also suggested by Ethan.
- **SPY** (`aurora_forecaster/data/price.py::fetch_spy_ohlcv`): already
  existed as a possible target-security series (see Target securities
  above); now also wired as an `"spy"` text-covariate source for BTC
  forecasts.

Funding/DXY/SPY enter through the text-context or vision-context path (see
below), not as extra numeric channels — confirmed 2026-08-08 by reading
`aurora-model==0.2.0`'s source: `ts_generation_mixin.py` hard-enforces
`inputs.shape == [batch_size, seq_len]` (2-D, no channel dimension) and
`AuroraConfig` has no `num_channels`/`num_variates` field, so Aurora has no
multivariate numeric input path. "Multimodal" in Aurora's own framing means
time series + text + image, not multiple numeric series.

All seven text sources (four news, three covariate) are being kept and
compared side by side (user decision, 2026-08-06, extended 2026-08-08)
rather than picking one upfront — the source choice itself is part of what
this feasibility test is meant to answer.

## Vision covariates

Real-image alternative to the funding/DXY/SPY text snippets above (user
idea, 2026-08-08): render the same covariate series as a chart instead of a
sentence, to test whether image-encoding vs. text-encoding of the same
information changes forecast quality — not a new information source, a
different encoding of the same one. `FUNDING_VISION`/`DXY_VISION`/
`SPY_VISION` in `aurora_forecaster/ablation.py`'s `STANDARD_CONFIGS`.

Distinct from Aurora's own always-on "pseudo" vision (`AuroraModel.forward`
auto-derives an image from the primary time series whenever no real image
is given via a period-detected reshape into a 2D grid — architecturally
separate, already active on every call this project makes, real image or
not).

- `aurora_forecaster/vision.py::render_line_chart` — white-background line
  chart via Pillow's `ImageDraw`. No plotting library (matplotlib/plotly) is
  installed in this project's venv; hand-drawing avoided adding one for a
  single chart type.
- `aurora_forecaster/vision_fetch.py::build_vision_context` — mirrors
  `text_fetch.py::build_text_context`'s dispatch shape, reusing the same
  underlying fetchers (`fetch_dxy_ohlcv`/`fetch_spy_ohlcv`/
  `post_funding_history`) already built for the text path; only the render
  step differs.
- **`vision_inputs` must be a raw PIL Image (`[image]`), never
  preprocessed** — confirmed the hard way 2026-08-08: Aurora's own
  `VisionEncoder`/`UnifiedImageProcessor.process_real_image` runs its own
  internal `ViTImageProcessor` pass, so pre-normalizing crashes it
  (`ValueError: ... values outside the range [0, 1], got [-1.0, 1.0]`).
- **Real Aurora limitation, not a usage mistake: `vision_inputs` only works
  on `device="cpu"`.** The internal `ViTImageProcessor` output never gets
  moved off CPU before the ViT conv layers, so MPS/CUDA raise `RuntimeError:
  ... must be on the same device`. `rolling_forecast_btc.py` forces
  `device="cpu"` whenever `STREAM_CONFIG.vision_sources` is set.
- Confirmed end-to-end 2026-08-08 via `scripts/vision_smoke_test.py`: real
  BTC OHLCV + a real rendered Hyperliquid funding-rate chart through the
  full `vision_inputs` path, output shape `(1, 10, 96)`.

## Known library bug: batch-collapsing at batch size 1

`aurora-model==0.2.0`'s `generate(text_inputs=...)` convenience path
(`aurora/ts_generation_mixin.py`) calls `.squeeze(0)` on the tokenizer
output, which collapses the batch dimension whenever batch size is 1 — our
case, since forecasting is per-asset. Crashes with `not enough values to
unpack (expected 2, got 1)` inside BERT encoding. Confirmed real (not a
usage mistake) by reading the installed package source and bypassing it in
isolation. Fix: `aurora_forecaster/multimodal.py::tokenize_text_context`
pre-tokenizes text ourselves and the caller passes
`text_input_ids`/`text_attention_mask`/`text_token_type_ids` directly to
`generate()` instead of `text_inputs` — see `scripts/multimodal_smoke_test.py`
for the working pattern. Confirmed end-to-end 2026-08-06: real BTC OHLCV +
text through the full multimodal path, output shape `(1, 10, 96)`.

## Open design questions

- How to align/merge GDELT's un-tagged event stream and Alpha Vantage's
  ticker-tagged feed into one per-timestep text-context input Aurora expects.
- Whether/when this needs to register into the cross-project `TrialLedger`
  registry as a third `project` value alongside `hmm-slope-experiment` and
  `mean-variance-paper`. Deferred: `ScoredForecastRecord` (see Scoring above)
  deliberately doesn't attempt this mapping yet — build it only once there's
  a concrete reason to compare a forecast's score against a strategy's
  Sharpe in one registry.
- `time-series/forecast_eval/compare.py` still has the old plain
  (non-HAC) Diebold-Mariano implementation that `aurora_forecaster/compare.py`
  had until 2026-08-08 — known follow-up, not fixed by this project's pass.
