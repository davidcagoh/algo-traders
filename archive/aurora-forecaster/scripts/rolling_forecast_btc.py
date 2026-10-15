"""
Manual script: walk-forward forecast loop over real BTC OHLCV, unimodal or
multimodal depending on `STREAM_CONFIG`.

Wraps the single-shot calls already proven in `scripts/smoke_test.py` /
`scripts/multimodal_smoke_test.py` in a loop over multiple origins, appending
each forecast's summary stats to a per-config ledger (see
`aurora_forecaster.ablation.ledger_path`). Needs network access and real
weights, so it's excluded from `tests/` by design.

Usage: python scripts/rolling_forecast_btc.py
To run a non-default stream config, edit STREAM_CONFIG below and rerun --
same "edit the module constant, rerun" convention already used for
LOOKBACK/HORIZON/etc. in this file.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from aurora.modeling_aurora import AuroraForPrediction
from dotenv import load_dotenv

from aurora_forecaster.ablation import UNIMODAL, StreamConfig, ledger_path, warn_infeasible_sources
from aurora_forecaster.data.price import fetch_btc_ohlcv
from aurora_forecaster.device import current_device
from aurora_forecaster.forecast_ledger import ForecastRecord, append_forecast
from aurora_forecaster.rolling import (
    forecast_origins,
    run_multimodal_forecast,
    run_unimodal_forecast,
)
from aurora_forecaster.text_fetch import build_text_context
from aurora_forecaster.vision_fetch import build_vision_context

MODEL_ID = "DecisionIntelligence/Aurora"
LOOKBACK = 528
HORIZON = 96
STRIDE = 96
NUM_SAMPLES = 10
# Pinned rather than "most recent N bars": fetch_btc_ohlcv(limit=...) with no
# `since` anchors to "now", so origin_timestamps drift depending on which
# calendar day/hour a config's script run happens on -- confirmed 2026-08-08,
# where a unimodal ledger built a day earlier than the gdelt/currents ledgers
# had zero overlapping origins with either, making cross-config Diebold-
# Mariano comparison impossible (ablation_core.align_common_origins requires
# >=2 shared origins). Pinning `since` guarantees every config's walk-forward
# loop lands on the identical origin set regardless of run day.
# FETCH_LIMIT bumped 1000->1700 (n=4->12 origins) 2026-08-09 to stress-test
# the funding-vision result (p=0.000 vs unimodal at n=4, 36 pairwise tests,
# no multiple-comparison correction -- needs more data before trusting it).
# Anchor moved earlier (2026-04-01, was 2026-06-28) since the old anchor was
# already only ~1008h before "now", leaving no room to extend FETCH_LIMIT
# further without fetching future (nonexistent) bars.
FETCH_SINCE_MS = 1775001600000  # 2026-04-01T00:00:00+00:00
FETCH_LIMIT = 1700
TEXT_QUERY = "bitcoin"
TEXT_FETCH_DELAY_SECONDS = 10.0  # was 5.0 -- 3x more GDELT calls per config now

STREAM_CONFIG: StreamConfig = UNIMODAL  # edit this constant to run a different config

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"
LEDGER_PATH = ledger_path(ARTIFACTS_DIR, STREAM_CONFIG)
REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


def _gdelt_timestamp(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M%S")


def _load_api_keys() -> dict[str, str]:
    load_dotenv(REPO_ROOT_ENV)
    keys = {}
    if "ALPHA_VANTAGE_API_KEY" in os.environ:
        keys["alphavantage"] = os.environ["ALPHA_VANTAGE_API_KEY"]
    if "CURRENTS_API_KEY" in os.environ:
        keys["currents"] = os.environ["CURRENTS_API_KEY"]
    return keys


def main() -> None:
    device = current_device()
    if STREAM_CONFIG.vision_sources:
        # Known real Aurora limitation, not a usage mistake (confirmed
        # 2026-08-08 via a real traceback): the internal ViTImageProcessor
        # always returns a CPU tensor and extract_vit_features never moves
        # it to the model's device -- vision_inputs only works on CPU.
        device = "cpu"
    print(f"device: {device}")
    print(f"stream config: {STREAM_CONFIG.name} (modality={STREAM_CONFIG.modality})")

    price_df = fetch_btc_ohlcv(timeframe="1h", limit=FETCH_LIMIT, since=FETCH_SINCE_MS)
    closes = price_df["close"].to_numpy()
    timestamps = price_df["timestamp"].to_numpy()
    print(f"price rows fetched: {len(price_df)}")

    origins = forecast_origins(len(closes), LOOKBACK, HORIZON, STRIDE)
    print(f"walk-forward origins: {len(origins)}")
    if not origins:
        print("not enough history for a single origin; increase FETCH_LIMIT")
        return

    for warning in warn_infeasible_sources(STREAM_CONFIG, len(origins)):
        print(f"warning: {warning}")

    api_keys = _load_api_keys() if STREAM_CONFIG.sources else {}
    covariate_encoding = "vision" if STREAM_CONFIG.vision_sources else "text"

    model = AuroraForPrediction.from_pretrained(MODEL_ID)
    model.to(device)
    model.eval()

    for origin in origins:
        window_closes = closes[:origin]
        origin_ts = datetime.fromtimestamp(timestamps[origin - 1] / 1000, tz=UTC)

        if STREAM_CONFIG.modality == "unimodal":
            output = run_unimodal_forecast(
                model, device, window_closes, LOOKBACK, HORIZON, NUM_SAMPLES
            )
        elif STREAM_CONFIG.vision_sources:
            window_start_ms = int(timestamps[origin - LOOKBACK])
            origin_ms = int(timestamps[origin - 1])
            vision_image = build_vision_context(
                STREAM_CONFIG.vision_sources, start_ms=window_start_ms, end_ms=origin_ms
            )
            output = run_multimodal_forecast(
                model, device, window_closes, LOOKBACK, HORIZON, NUM_SAMPLES,
                vision_image=vision_image,
            )
        else:
            if "gdelt" in STREAM_CONFIG.sources:
                # Proactive spacing, not just reactive retry: back-to-back
                # origins triggered GDELT 429s even with per-call backoff
                # (2026-08-08 session-log) -- spread the calls out up front.
                time.sleep(TEXT_FETCH_DELAY_SECONDS)
            window_start_ts = datetime.fromtimestamp(timestamps[origin - LOOKBACK] / 1000, tz=UTC)
            text_context = build_text_context(
                sources=STREAM_CONFIG.sources,
                query=TEXT_QUERY,
                start=_gdelt_timestamp(window_start_ts),
                end=_gdelt_timestamp(origin_ts),
                api_keys=api_keys,
            )
            output = run_multimodal_forecast(
                model, device, window_closes, LOOKBACK, HORIZON, NUM_SAMPLES, text_context
            )

        mean = output.squeeze(0).mean(dim=0)
        std = output.squeeze(0).std(dim=0)

        record = ForecastRecord(
            forecast_id=str(uuid.uuid4()),
            created_at=datetime.now(UTC).isoformat(),
            asset="BTC",
            modality=STREAM_CONFIG.modality,
            model_id=MODEL_ID,
            origin_timestamp=origin_ts.isoformat(),
            lookback=LOOKBACK,
            horizon=HORIZON,
            num_samples=NUM_SAMPLES,
            sample_mean=mean.tolist(),
            sample_std=std.tolist(),
            text_config=STREAM_CONFIG.name,
            covariate_encoding=covariate_encoding,
        )
        append_forecast(LEDGER_PATH, record)
        print(f"origin {origin} ({origin_ts.isoformat()}): forecast appended")

    print(f"done. ledger: {LEDGER_PATH}")


if __name__ == "__main__":
    main()
