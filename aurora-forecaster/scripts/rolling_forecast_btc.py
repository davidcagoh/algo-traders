"""
Manual script: walk-forward unimodal forecast loop over real BTC OHLCV.

Wraps the single-shot call already proven in `scripts/smoke_test.py` in a
loop over multiple origins, appending each forecast's summary stats to
`artifacts/btc_unimodal_forecast_ledger.jsonl`. No text context — that's the
multimodal path, still blocked on aligning the four text sources. Needs
network access and real weights, so it's excluded from `tests/` by design.

Usage: python scripts/rolling_forecast_btc.py
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from aurora.modeling_aurora import AuroraForPrediction

from aurora_forecaster.data.price import fetch_btc_ohlcv
from aurora_forecaster.device import current_device
from aurora_forecaster.forecast_ledger import ForecastRecord, append_forecast
from aurora_forecaster.rolling import forecast_origins, run_unimodal_forecast

MODEL_ID = "DecisionIntelligence/Aurora"
LOOKBACK = 528
HORIZON = 96
STRIDE = 96
NUM_SAMPLES = 10
FETCH_LIMIT = 1000

LEDGER_PATH = Path(__file__).resolve().parents[1] / "artifacts" / "btc_unimodal_forecast_ledger.jsonl"


def main() -> None:
    device = current_device()
    print(f"device: {device}")

    price_df = fetch_btc_ohlcv(timeframe="1h", limit=FETCH_LIMIT)
    closes = price_df["close"].to_numpy()
    timestamps = price_df["timestamp"].to_numpy()
    print(f"price rows fetched: {len(price_df)}")

    origins = forecast_origins(len(closes), LOOKBACK, HORIZON, STRIDE)
    print(f"walk-forward origins: {len(origins)}")
    if not origins:
        print("not enough history for a single origin; increase FETCH_LIMIT")
        return

    model = AuroraForPrediction.from_pretrained(MODEL_ID)
    model.to(device)
    model.eval()

    for origin in origins:
        window_closes = closes[:origin]
        output = run_unimodal_forecast(
            model, device, window_closes, LOOKBACK, HORIZON, NUM_SAMPLES
        )
        mean = output.squeeze(0).mean(dim=0)
        std = output.squeeze(0).std(dim=0)

        origin_ts = datetime.fromtimestamp(timestamps[origin - 1] / 1000, tz=UTC)
        record = ForecastRecord(
            forecast_id=str(uuid.uuid4()),
            created_at=datetime.now(UTC).isoformat(),
            asset="BTC",
            modality="unimodal",
            model_id=MODEL_ID,
            origin_timestamp=origin_ts.isoformat(),
            lookback=LOOKBACK,
            horizon=HORIZON,
            num_samples=NUM_SAMPLES,
            sample_mean=mean.tolist(),
            sample_std=std.tolist(),
        )
        append_forecast(LEDGER_PATH, record)
        print(f"origin {origin} ({origin_ts.isoformat()}): forecast appended")

    print(f"done. ledger: {LEDGER_PATH}")


if __name__ == "__main__":
    main()
