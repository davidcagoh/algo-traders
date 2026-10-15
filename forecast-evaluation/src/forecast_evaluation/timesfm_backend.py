"""Lazy adapter for the pinned TimesFM 3.0 PyTorch checkpoint."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import numpy as np


MODEL_ID = "google/timesfm-3.0-pytorch"
MODEL_REVISION = "43046b85ec22d584a13f8098c2ed39c889e129c2"
PACKAGE_VERSION = "3.0.2"


class TimesFM3Adapter:
    """Expose the evaluation runner's narrow predictor interface."""

    def __init__(self, *, device: str = "cpu", cache_dir: str | None = None) -> None:
        try:
            installed = version("timesfm")
        except PackageNotFoundError as exc:
            raise RuntimeError(
                "TimesFM is not installed; install forecast-evaluation[model] first"
            ) from exc
        if installed != PACKAGE_VERSION:
            raise RuntimeError(
                f"expected timesfm=={PACKAGE_VERSION}, found {installed}; use the pinned environment"
            )
        try:
            from timesfm3 import TimesFM3Forecaster
        except ImportError as exc:
            raise RuntimeError("the installed TimesFM package has no timesfm3 API") from exc
        kwargs = {
            "revision": MODEL_REVISION,
            "device": device,
            "per_core_batch_size": 1,
        }
        if cache_dir is not None:
            kwargs["cache_dir"] = cache_dir
        self.model = TimesFM3Forecaster.from_pretrained(MODEL_ID, **kwargs)
        self.device = device

    def predict(self, targets: np.ndarray, *, horizon: int) -> tuple[np.ndarray, np.ndarray]:
        output = self.model.predict(
            targets,
            horizon=horizon,
            return_quantiles=True,
            make_positive=False,
            sort_quantiles=True,
            use_symmetric_averaging=False,
            use_znorm=False,
            padding_mode="none",
        )
        if output.quantiles is None:
            raise RuntimeError("TimesFM did not return quantile forecasts")
        return np.asarray(output.forecast), np.asarray(output.quantiles)
