"""Canonical output shared by all execution backends."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class BacktestResult:
    returns: pd.DataFrame
    equity: pd.Series
    targets: pd.DataFrame
    executed_weights: pd.DataFrame
    ending_weights: pd.DataFrame
    turnover: pd.Series
    trades: pd.DataFrame
    costs: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self.returns.to_parquet(directory / "returns.parquet")
        self.equity.rename("equity").to_frame().to_parquet(directory / "equity.parquet")
        self.targets.to_parquet(directory / "targets.parquet")
        self.executed_weights.to_parquet(directory / "executed_weights.parquet")
        self.ending_weights.to_parquet(directory / "ending_weights.parquet")
        self.turnover.rename("turnover").to_frame().to_parquet(directory / "turnover.parquet")
        self.trades.to_parquet(directory / "trades.parquet", index=False)
        self.costs.to_parquet(directory / "costs.parquet")
        (directory / "metadata.json").write_text(
            json.dumps(self.metadata, indent=2, default=str) + "\n"
        )
