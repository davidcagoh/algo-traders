"""Walk-forward windowing and the unimodal forecast call, factored out of
the one-shot smoke tests so they're reusable across many origins.
"""

from __future__ import annotations

import numpy as np
import torch


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
