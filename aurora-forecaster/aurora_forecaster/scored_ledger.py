"""Append-only scored-forecast ledger.

Modeled 1:1 on `forecast_ledger.py`'s `ForecastRecord`/`append_forecast`.
One `ScoredForecastRecord` per `ForecastRecord` scored against realized
prices (see `realized.py` for the alignment step and `scoring.py` for the
metrics). Kept separate from `ForecastRecord` rather than adding score
fields to it, since a forecast can exist unscored (no realized prices yet)
but a score can never exist without its forecast.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

Modality = Literal["unimodal", "multimodal"]

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ScoredForecastRecord:
    forecast_id: str
    scored_at: str  # ISO 8601
    asset: str
    modality: Modality
    model_id: str
    origin_timestamp: str  # ISO 8601, matches the source ForecastRecord
    crps_per_step: list[float]  # len == horizon
    crps_mean: float
    mase: float
    skill_score_vs_naive: float
    z_scores: list[float]  # standardized residuals per horizon step
    schema_version: int = SCHEMA_VERSION

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, default=str)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ScoredForecastRecord:
        return cls(**dict(d))


def append_scored(path: Path, record: ScoredForecastRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(record.to_json_line() + "\n")
