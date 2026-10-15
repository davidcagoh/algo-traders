import numpy as np
import torch

from aurora_forecaster.rolling import (
    forecast_origins,
    run_multimodal_forecast,
    run_unimodal_forecast,
)


def test_forecast_origins_single_window_exact_fit():
    assert forecast_origins(n_rows=10, lookback=5, horizon=5, stride=1) == [5]


def test_forecast_origins_strided_walk_forward():
    assert forecast_origins(n_rows=20, lookback=5, horizon=5, stride=5) == [5, 10, 15]


def test_forecast_origins_too_few_rows_returns_empty():
    assert forecast_origins(n_rows=8, lookback=5, horizon=5, stride=1) == []


def test_forecast_origins_rejects_non_positive_stride():
    import pytest

    with pytest.raises(ValueError):
        forecast_origins(n_rows=20, lookback=5, horizon=5, stride=0)


class FakeModel:
    def __init__(self):
        self.calls = []

    def generate(self, inputs, max_output_length, num_samples, inference_token_len):
        self.calls.append(
            {
                "inputs_shape": tuple(inputs.shape),
                "max_output_length": max_output_length,
                "num_samples": num_samples,
                "inference_token_len": inference_token_len,
            }
        )
        return torch.zeros(1, num_samples, max_output_length)


def test_run_unimodal_forecast_uses_last_lookback_window():
    model = FakeModel()
    closes = np.arange(20, dtype=np.float32)

    output = run_unimodal_forecast(
        model, device="cpu", closes=closes, lookback=5, horizon=6, num_samples=10
    )

    assert output.shape == (1, 10, 6)
    call = model.calls[0]
    assert call["inputs_shape"] == (1, 5)
    assert call["max_output_length"] == 6
    assert call["inference_token_len"] == 3


class FakeMultimodalModel:
    def __init__(self):
        self.calls = []

    def generate(self, inputs, max_output_length, num_samples, inference_token_len, **kwargs):
        call = {
            "inputs_shape": tuple(inputs.shape),
            "max_output_length": max_output_length,
            "num_samples": num_samples,
            "inference_token_len": inference_token_len,
        }
        for key, value in kwargs.items():
            call[f"{key}_shape"] = tuple(value.shape) if hasattr(value, "shape") else value
        self.calls.append(call)
        return torch.zeros(1, num_samples, max_output_length)


def test_run_multimodal_forecast_uses_last_lookback_window_and_tokenizes_text():
    model = FakeMultimodalModel()
    closes = np.arange(20, dtype=np.float32)

    output = run_multimodal_forecast(
        model,
        device="cpu",
        closes=closes,
        lookback=5,
        horizon=6,
        num_samples=10,
        text_context="Bitcoin rallies on ETF inflows.",
    )

    assert output.shape == (1, 10, 6)
    call = model.calls[0]
    assert call["inputs_shape"] == (1, 5)
    assert call["max_output_length"] == 6
    assert call["inference_token_len"] == 3
    # regression guard for the documented squeeze(0) batch-collapse bug:
    # this call path must pass pre-tokenized tensors with batch dim 1, never
    # go through generate(text_inputs=...)
    assert call["text_input_ids_shape"][0] == 1
    assert call["text_attention_mask_shape"][0] == 1
    assert call["text_token_type_ids_shape"][0] == 1
    assert "vision_inputs_shape" not in call


def test_run_multimodal_forecast_vision_only_omits_text_kwargs():
    from PIL import Image

    model = FakeMultimodalModel()
    closes = np.arange(20, dtype=np.float32)
    image = Image.new("RGB", (50, 50), color="white")

    output = run_multimodal_forecast(
        model, device="cpu", closes=closes, lookback=5, horizon=6, num_samples=10,
        vision_image=image,
    )

    assert output.shape == (1, 10, 6)
    call = model.calls[0]
    # vision_image is passed as a raw PIL Image, NOT preprocessed -- Aurora
    # runs its own internal ViTImageProcessor pass and double-processing
    # crashes it (confirmed 2026-08-08, see aurora_forecaster/vision.py).
    assert call["vision_inputs_shape"] == [image]
    assert "text_input_ids_shape" not in call
    assert "text_attention_mask_shape" not in call
    assert "text_token_type_ids_shape" not in call
