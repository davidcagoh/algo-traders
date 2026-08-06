"""
Manual smoke test: pulls DecisionIntelligence/Aurora weights from Hugging Face
and runs one unimodal forward pass on synthetic data. Not a pytest test —
needs network access and real weights, so it's excluded from tests/.

Usage: python scripts/smoke_test.py
"""

import torch
from aurora.modeling_aurora import AuroraForPrediction

from aurora_forecaster.device import current_device

MODEL_ID = "DecisionIntelligence/Aurora"
LOOKBACK = 528


def main() -> None:
    device = current_device()
    print(f"device: {device}")

    model = AuroraForPrediction.from_pretrained(MODEL_ID)
    model.to(device)
    model.eval()

    seqs = torch.randn(1, LOOKBACK).to(device)

    with torch.no_grad():
        output = model.generate(
            inputs=seqs,
            max_output_length=96,
            num_samples=10,
            inference_token_len=48,
        )

    print(f"output shape: {tuple(output.shape)}")


if __name__ == "__main__":
    main()
