"""Append-only forecast ledger.

Modeled on `evaluation-framework/evaluation/ledger.py`'s `TrialRecord`
(append-only JSONL, frozen dataclass, `to_json_line`/`from_dict`), but scoped
to what a forecast actually has at generation time: no `sharpe` or
`returns_artifact` fields, since nothing has been realized yet. Once
`evaluation-framework` defines how to score a probabilistic forecast, a
separate scoring pass can read this ledger and produce `TrialRecord`s from
it — this file doesn't guess at that schema.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

Modality = Literal["unimodal", "multimodal"]

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ForecastRecord:
    forecast_id: str
    created_at: str  # ISO 8601
    asset: str
    modality: Modality
    model_id: str
    origin_timestamp: str  # ISO 8601, timestamp of the last lookback bar
    lookback: int
    horizon: int
    num_samples: int
    sample_mean: list[float]  # len == horizon
    sample_std: list[float]  # len == horizon
    schema_version: int = SCHEMA_VERSION

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, default=str)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ForecastRecord:
        return cls(**dict(d))


def append_forecast(path: Path, record: ForecastRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(record.to_json_line() + "\n")
