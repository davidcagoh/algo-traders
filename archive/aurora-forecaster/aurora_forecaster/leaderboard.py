"""Append-only leaderboard history: one `LeaderboardEntry` per config per
`scripts/render_dashboard.py` run, so config performance can be tracked
across runs rather than only viewing the latest snapshot (which is all
`run_ablation_report` gives -- it recomputes from the current scored
ledgers but doesn't remember past results).

Same append-only JSONL pattern as `forecast_ledger.py`/`scored_ledger.py`.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from aurora_forecaster.ablation_core import ConfigSummary

LEADERBOARD_FILENAME = "leaderboard_history.jsonl"


@dataclass(frozen=True)
class LeaderboardEntry:
    run_at: str  # ISO 8601
    config_name: str
    n_origins: int
    mean_loss: float
    std_loss: float

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, default=str)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LeaderboardEntry:
        return cls(**dict(d))


def record_leaderboard_entry(
    artifacts_dir: Path, summaries: Sequence[ConfigSummary], run_at: str
) -> None:
    """Appends one `LeaderboardEntry` per config summary."""
    path = artifacts_dir / LEADERBOARD_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        for summary in summaries:
            entry = LeaderboardEntry(
                run_at=run_at,
                config_name=summary.config_name,
                n_origins=summary.n_origins,
                mean_loss=summary.mean_loss,
                std_loss=summary.std_loss,
            )
            f.write(entry.to_json_line() + "\n")


def load_leaderboard_history(artifacts_dir: Path) -> list[LeaderboardEntry]:
    """Tolerant of a missing file (returns [])."""
    path = artifacts_dir / LEADERBOARD_FILENAME
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        if line.strip():
            entries.append(LeaderboardEntry.from_dict(json.loads(line)))
    return entries
