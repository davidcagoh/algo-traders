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

All four text sources are being kept and compared side by side (user
decision, 2026-08-06) rather than picking one upfront — the text-source
choice itself is part of what this feasibility test is meant to answer.

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
- How to wrap `model.generate(...)`'s distributional output into a
  walk-forward loop comparable to `evaluation-framework`'s existing metrics,
  which currently assume realized trade/portfolio returns, not a
  probabilistic forecast.
- Whether/when this needs to register into the cross-project `TrialLedger`
  registry as a third `project` value alongside `hmm-slope-experiment` and
  `mean-variance-paper`.
