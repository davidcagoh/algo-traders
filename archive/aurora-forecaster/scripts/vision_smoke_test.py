"""
Manual smoke test: one real vision forward pass — real BTC OHLCV close
prices (ccxt/Binance) as the time series leg, a real chart of Hyperliquid's
BTC perp funding rate (rendered via `aurora_forecaster.vision`) as the real
`vision_inputs` leg. Confirms Aurora's `generate(inputs=..., vision_inputs=...)`
path actually runs before any walk-forward wiring.

Distinct from `multimodal_smoke_test.py`'s text leg -- this is the vision-
covariate encoding alternative (2026-08-08), testing whether encoding the
same funding-rate information as an image instead of text changes forecast
quality. `vision_inputs` is passed as a raw PIL Image list, NOT preprocessed
-- Aurora runs its own internal ViTImageProcessor pass and double-processing
crashes it. Forces `device="cpu"`: a real, confirmed Aurora limitation
(not a usage mistake) -- the internal ViTImageProcessor output never gets
moved off CPU before the ViT conv layers, so MPS/CUDA raise a device
mismatch. See `aurora_forecaster/vision.py`'s module docstring.

Usage: python scripts/vision_smoke_test.py
"""

from datetime import UTC, datetime, timedelta

import torch
from aurora.modeling_aurora import AuroraForPrediction

from aurora_forecaster.data.price import fetch_btc_ohlcv
from aurora_forecaster.data.text_funding import post_funding_history
from aurora_forecaster.vision import render_line_chart

MODEL_ID = "DecisionIntelligence/Aurora"
LOOKBACK = 528


def main() -> None:
    device = "cpu"  # vision_inputs only works on CPU, see module docstring
    print(f"device: {device}")

    price_df = fetch_btc_ohlcv(timeframe="1h", limit=LOOKBACK)
    print(f"price rows fetched: {len(price_df)}")
    closes = torch.tensor(price_df["close"].values, dtype=torch.float32).unsqueeze(0)

    end = datetime.now(UTC)
    start = end - timedelta(hours=LOOKBACK)
    records = post_funding_history(
        "BTC", start_ms=int(start.timestamp() * 1000), end_ms=int(end.timestamp() * 1000)
    )
    values = [float(r["fundingRate"]) for r in sorted(records, key=lambda r: int(r["time"]))]
    print(f"funding records used: {len(values)}")

    chart = render_line_chart(values)

    model = AuroraForPrediction.from_pretrained(MODEL_ID)
    model.to(device)
    model.eval()

    inputs = closes.to(device)

    with torch.no_grad():
        unimodal_output = model.generate(
            inputs=inputs, max_output_length=96, num_samples=10, inference_token_len=48
        )
        vision_output = model.generate(
            inputs=inputs,
            vision_inputs=[chart],
            max_output_length=96,
            num_samples=10,
            inference_token_len=48,
        )

    print(f"unimodal output shape: {tuple(unimodal_output.shape)}")
    print(f"vision output shape:   {tuple(vision_output.shape)}")


if __name__ == "__main__":
    main()
