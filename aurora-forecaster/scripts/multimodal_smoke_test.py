"""
Manual smoke test: one real multimodal forward pass — real BTC OHLCV close
prices (ccxt/Binance) as the time series leg, real GDELT article titles as
the text leg. Confirms Aurora's multimodal `generate(inputs=..., text_inputs=...)`
path actually runs before any walk-forward or source-merging work.

Usage: python scripts/multimodal_smoke_test.py
"""

import torch
from aurora.modeling_aurora import AuroraForPrediction

from aurora_forecaster.data.price import fetch_btc_ohlcv
from aurora_forecaster.data.text_gdelt import fetch_gdelt_events
from aurora_forecaster.device import current_device
from aurora_forecaster.multimodal import tokenize_text_context

MODEL_ID = "DecisionIntelligence/Aurora"
LOOKBACK = 528
FALLBACK_TEXT = "Bitcoin ETF inflows slow as investors rotate into AI-linked assets."


def main() -> None:
    device = current_device()
    print(f"device: {device}")

    price_df = fetch_btc_ohlcv(timeframe="1h", limit=LOOKBACK)
    print(f"price rows fetched: {len(price_df)}")
    closes = torch.tensor(price_df["close"].values, dtype=torch.float32).unsqueeze(0)

    try:
        gdelt = fetch_gdelt_events(
            query="bitcoin", start="20260805000000", end="20260806000000", max_records=10
        )
        titles = [a.get("title", "") for a in gdelt.get("articles", []) if a.get("title")]
        text_context = " ".join(titles) if titles else FALLBACK_TEXT
        print(f"gdelt titles used: {len(titles)}")
    except Exception as exc:
        print(f"gdelt fetch failed ({exc}); using fallback text")
        text_context = FALLBACK_TEXT

    model = AuroraForPrediction.from_pretrained(MODEL_ID)
    model.to(device)
    model.eval()

    inputs = closes.to(device)
    tokenized = tokenize_text_context(text_context)

    with torch.no_grad():
        unimodal_output = model.generate(
            inputs=inputs, max_output_length=96, num_samples=10, inference_token_len=48
        )
        # Note: generate(text_inputs=...) has a batch-collapsing bug at batch
        # size 1 (see aurora_forecaster/multimodal.py) — pass pre-tokenized
        # tensors directly to bypass it.
        multimodal_output = model.generate(
            inputs=inputs,
            text_input_ids=tokenized["input_ids"].to(device),
            text_attention_mask=tokenized["attention_mask"].to(device),
            text_token_type_ids=tokenized["token_type_ids"].to(device),
            max_output_length=96,
            num_samples=10,
            inference_token_len=48,
        )

    print(f"unimodal output shape:   {tuple(unimodal_output.shape)}")
    print(f"multimodal output shape: {tuple(multimodal_output.shape)}")


if __name__ == "__main__":
    main()
