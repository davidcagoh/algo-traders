"""Walk-forward windowing and the unimodal forecast call, factored out of
the one-shot smoke tests so they're reusable across many origins.
"""

from __future__ import annotations

import numpy as np
import torch
from PIL import Image

from aurora_forecaster.multimodal import tokenize_text_context


def forecast_origins(n_rows: int, lookback: int, horizon: int, stride: int) -> list[int]:
    """Row indices marking the end of each lookback window.

    An origin at index `i` uses rows `[i - lookback, i)` as history and
    would need rows `[i, i + horizon)` to score against — this function only
    computes valid origins, it doesn't require the horizon rows to exist yet.
    """
    if stride <= 0:
        raise ValueError("stride must be positive")
    last_origin = n_rows - horizon
    if last_origin < lookback:
        return []
    return list(range(lookback, last_origin + 1, stride))


def run_unimodal_forecast(
    model,
    device: str,
    closes: np.ndarray,
    lookback: int,
    horizon: int,
    num_samples: int,
) -> torch.Tensor:
    """One unimodal `generate()` call over the last `lookback` closes.

    Mirrors the call already proven in `scripts/smoke_test.py`; factored out
    so a walk-forward loop can call it once per origin.
    """
    window = closes[-lookback:]
    inputs = torch.tensor(window, dtype=torch.float32).unsqueeze(0).to(device)

    with torch.no_grad():
        return model.generate(
            inputs=inputs,
            max_output_length=horizon,
            num_samples=num_samples,
            inference_token_len=horizon // 2,
        )


def run_multimodal_forecast(
    model,
    device: str,
    closes: np.ndarray,
    lookback: int,
    horizon: int,
    num_samples: int,
    text_context: str | None = None,
    vision_image: Image.Image | None = None,
) -> torch.Tensor:
    """Multimodal sibling of `run_unimodal_forecast`: same windowing, but
    also passes a text covariate, a real-image covariate, or both --
    `text_context` and `vision_image` are independently optional since
    Aurora's forward pass computes each branch independently (confirmed
    2026-08-08: `AuroraModel.forward`'s `if vision_ids is not None` / `if
    text_input_ids is not None` are separate, non-exclusive branches).

    Text uses the proven `text_input_ids`/`text_attention_mask`/
    `text_token_type_ids` bypass for Aurora's batch-collapse bug at batch
    size 1 (see `aurora_forecaster/multimodal.py`). `vision_image` is passed
    as a raw PIL Image (`vision_inputs=[vision_image]`), NOT preprocessed --
    Aurora's own `VisionEncoder` runs its own internal `ViTImageProcessor`
    pass; pre-normalizing here double-processes the image and crashes
    (confirmed 2026-08-08, see `aurora_forecaster/vision.py`'s docstring).

    Known real Aurora limitation, not a usage mistake (confirmed 2026-08-08
    via a real traceback): the internal `ViTImageProcessor` always returns a
    CPU tensor, and `extract_vit_features` never moves it to the model's
    device before the ViT conv layers -- `vision_image` only works when
    `device="cpu"`; MPS/CUDA raise `RuntimeError: ... must be on the same
    device`. Callers passing `vision_image` must pass `device="cpu"`.
    """
    window = closes[-lookback:]
    inputs = torch.tensor(window, dtype=torch.float32).unsqueeze(0).to(device)

    kwargs = {}
    if text_context is not None:
        tokenized = tokenize_text_context(text_context)
        kwargs["text_input_ids"] = tokenized["input_ids"].to(device)
        kwargs["text_attention_mask"] = tokenized["attention_mask"].to(device)
        kwargs["text_token_type_ids"] = tokenized["token_type_ids"].to(device)
    if vision_image is not None:
        kwargs["vision_inputs"] = [vision_image]

    with torch.no_grad():
        return model.generate(
            inputs=inputs,
            max_output_length=horizon,
            num_samples=num_samples,
            inference_token_len=horizon // 2,
            **kwargs,
        )
