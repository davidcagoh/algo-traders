import numpy as np
import torch

from aurora_forecaster.rolling import forecast_origins, run_unimodal_forecast


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
