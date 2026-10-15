"""Generic N-way config comparison over paired (origin, loss) series:
per-config summary stats + all-pairs Diebold-Mariano significance testing +
a markdown report.

No knowledge of forecasts, ledgers, text sources, or any other
aurora-forecaster type -- the only import is `aurora_forecaster.compare`,
which is itself asset/project-agnostic (plain float sequences in, matching
`time-series/forecast_eval/compare.py`'s identical signature). This module
is the literal promotion candidate for `forecast_eval` once a second project
needs stream-ablation comparison (see `wiki/decisions-archive.md`'s
eval-package-boundary decision, 2026-08-08) -- promoting it is expected to
require changing only the `compare` import.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations

from aurora_forecaster.compare import DieboldMarianoResult, diebold_mariano


@dataclass(frozen=True)
class LossSeries:
    config_name: str
    origin_timestamps: tuple[str, ...]
    losses: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.origin_timestamps) != len(self.losses):
            raise ValueError("origin_timestamps and losses must be equal length")
        if len(self.origin_timestamps) != len(set(self.origin_timestamps)):
            raise ValueError(f"duplicate origin_timestamp in config {self.config_name!r}")


@dataclass(frozen=True)
class ConfigSummary:
    config_name: str
    n_origins: int
    mean_loss: float
    std_loss: float


def summarize_loss_series(series: LossSeries) -> ConfigSummary:
    n = len(series.losses)
    mean_loss = sum(series.losses) / n
    if n < 2:
        std_loss = 0.0
    else:
        std_loss = math.sqrt(sum((x - mean_loss) ** 2 for x in series.losses) / (n - 1))
    return ConfigSummary(
        config_name=series.config_name, n_origins=n, mean_loss=mean_loss, std_loss=std_loss
    )


def align_common_origins(
    a: LossSeries, b: LossSeries
) -> tuple[list[float], list[float], list[str]]:
    """Inner join on origin_timestamp, sorted ascending. Raises `ValueError`
    if fewer than 2 origins are common (`diebold_mariano`'s own minimum)."""
    a_by_ts = dict(zip(a.origin_timestamps, a.losses))
    b_by_ts = dict(zip(b.origin_timestamps, b.losses))
    common = sorted(set(a_by_ts) & set(b_by_ts))
    if len(common) < 2:
        raise ValueError(
            f"{a.config_name!r} vs {b.config_name!r}: only {len(common)} common origins, "
            "need at least 2"
        )
    return [a_by_ts[ts] for ts in common], [b_by_ts[ts] for ts in common], common


@dataclass(frozen=True)
class PairwiseComparison:
    config_a: str
    config_b: str
    n_common_origins: int
    dm: DieboldMarianoResult


def pairwise_compare(
    series: Sequence[LossSeries],
    max_lag: int | None = None,
) -> tuple[list[PairwiseComparison], list[str]]:
    """All C(n,2) unordered pairs from `series`, sorted by (config_a,
    config_b) name for reproducible report ordering. A pair with fewer than
    2 common origins is skipped (its reason collected into the second
    return value) rather than raised, so one gappy config doesn't crash the
    whole report."""
    ordered = sorted(series, key=lambda s: s.config_name)
    comparisons: list[PairwiseComparison] = []
    skipped: list[str] = []
    for a, b in combinations(ordered, 2):
        try:
            losses_a, losses_b, common = align_common_origins(a, b)
        except ValueError as e:
            skipped.append(str(e))
            continue
        dm = diebold_mariano(losses_a, losses_b, max_lag=max_lag)
        comparisons.append(
            PairwiseComparison(
                config_a=a.config_name,
                config_b=b.config_name,
                n_common_origins=len(common),
                dm=dm,
            )
        )
    return comparisons, skipped


def format_ablation_report(
    summaries: Sequence[ConfigSummary],
    comparisons: Sequence[PairwiseComparison],
    skipped: Sequence[str] = (),
) -> str:
    lines = ["### Config summary", "", "| Config | N origins | Mean loss | Std loss |", "|---|---:|---:|---:|"]
    for s in summaries:
        lines.append(f"| {s.config_name} | {s.n_origins} | {s.mean_loss:.4f} | {s.std_loss:.4f} |")

    lines += [
        "",
        "### Pairwise Diebold-Mariano",
        "",
        (
            "Negative statistic + small p-value means `config_a`'s loss is significantly "
            "lower (better) than `config_b`'s."
        ),
        "",
        "| config_a | config_b | statistic | p_value | n_common_origins | max_lag |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for c in comparisons:
        lines.append(
            f"| {c.config_a} | {c.config_b} | {c.dm.statistic:.4f} | {c.dm.p_value:.3f} | "
            f"{c.n_common_origins} | {c.dm.max_lag} |"
        )

    if skipped:
        lines += ["", "### Skipped pairs", ""]
        lines += [f"- {reason}" for reason in skipped]

    return "\n".join(lines)
