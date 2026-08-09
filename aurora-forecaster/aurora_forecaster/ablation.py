"""Aurora-specific glue for stream ablation: the `StreamConfig` value type
(which text sources feed one walk-forward run), per-config ledger/scored-
ledger file naming, and the `ScoredForecastRecord -> LossSeries` adapter.

Only this file (plus `text_fetch.py`/`text_adapter.py`) would need to change
if `ablation_core.py` is ever promoted to `time-series/forecast_eval/` --
everything here stays in `aurora_forecaster`.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from aurora_forecaster.ablation_core import (
    ConfigSummary,
    LossSeries,
    PairwiseComparison,
    format_ablation_report,
    pairwise_compare,
    summarize_loss_series,
)
from aurora_forecaster.scored_ledger import ScoredForecastRecord
from aurora_forecaster.text_adapter import TextSource, VisionSource

RATE_LIMITS_PER_DAY: dict[TextSource, int | None] = {
    "gdelt": None,  # no published hard cap
    "alphavantage": 25,  # free tier
    "currents": 1000,  # free tier
    "funding": None,  # Hyperliquid /info: no documented daily cap, informal
    # throttling only -- text_funding.py's backoff handles it (see gdelt)
    "dxy": None,  # yfinance: same informal-risk-only situation
    "spy": None,
}


@dataclass(frozen=True)
class StreamConfig:
    name: str  # stable id: ledger filename + report label
    sources: tuple[TextSource, ...] = ()
    vision_sources: tuple[VisionSource, ...] = ()

    @property
    def modality(self) -> Literal["unimodal", "multimodal"]:
        return "unimodal" if not (self.sources or self.vision_sources) else "multimodal"


UNIMODAL = StreamConfig(name="unimodal")
GDELT_ONLY = StreamConfig(name="gdelt", sources=("gdelt",))
CURRENTS_ONLY = StreamConfig(name="currents", sources=("currents",))
GDELT_CURRENTS = StreamConfig(name="gdelt+currents", sources=("gdelt", "currents"))
FUNDING_ONLY = StreamConfig(name="funding", sources=("funding",))
DXY_ONLY = StreamConfig(name="dxy", sources=("dxy",))
SPY_ONLY = StreamConfig(name="spy", sources=("spy",))
FUNDING_VISION = StreamConfig(name="funding-vision", vision_sources=("funding",))
DXY_VISION = StreamConfig(name="dxy-vision", vision_sources=("dxy",))
SPY_VISION = StreamConfig(name="spy-vision", vision_sources=("spy",))

# Alpha Vantage (25 req/day, 1 req/sec) can't sustain a real walk-forward
# loop (one fetch per origin) -- see README's Data sources section. Excluded
# from the standing rotation by construction, not a hardcoded skip list:
# nothing stops StreamConfig(name="alphavantage", sources=("alphavantage",))
# from being built and run manually/rarely; warn_infeasible_sources flags it
# at run time instead of a blanket ban.
# funding/dxy/spy don't combine with each other, with the news sources, or
# with their own vision variant yet -- single-source-first, same incremental
# approach used for gdelt vs. currents before gdelt+currents was added.
STANDARD_CONFIGS: tuple[StreamConfig, ...] = (
    UNIMODAL,
    GDELT_ONLY,
    CURRENTS_ONLY,
    GDELT_CURRENTS,
    FUNDING_ONLY,
    DXY_ONLY,
    SPY_ONLY,
    FUNDING_VISION,
    DXY_VISION,
    SPY_VISION,
)


def warn_infeasible_sources(config: StreamConfig, num_origins: int) -> list[str]:
    """Human-readable warnings (not exceptions) when `num_origins` would
    exceed a source's known free-tier daily cap. Doesn't block the run --
    call before a walk-forward loop starts and print/log the result. Checks
    both `sources` and `vision_sources` -- the underlying API call volume is
    identical regardless of encoding, only the render step differs."""
    warnings = []
    for source in (*config.sources, *config.vision_sources):
        limit = RATE_LIMITS_PER_DAY.get(source)
        if limit is not None and num_origins > limit:
            warnings.append(
                f"{config.name}: {num_origins} origins would exceed '{source}'s "
                f"free-tier cap of {limit} requests/day"
            )
    return warnings


def ledger_path(artifacts_dir: Path, config: StreamConfig) -> Path:
    return artifacts_dir / f"btc_{config.name}_forecast_ledger.jsonl"


def scored_ledger_path(artifacts_dir: Path, config: StreamConfig) -> Path:
    return artifacts_dir / f"btc_{config.name}_forecast_scored.jsonl"


def loss_series_from_scored_records(
    config_name: str,
    records: Sequence[ScoredForecastRecord],
    loss_field: str = "crps_mean",
) -> LossSeries:
    """Sorts `records` by origin_timestamp and extracts `loss_field` (e.g.
    `crps_mean`, `mase`, `skill_score_vs_naive`) via `getattr`. Raises
    `AttributeError` (fail loud) if `loss_field` isn't a real field."""
    ordered = sorted(records, key=lambda r: r.origin_timestamp)
    return LossSeries(
        config_name=config_name,
        origin_timestamps=tuple(r.origin_timestamp for r in ordered),
        losses=tuple(getattr(r, loss_field) for r in ordered),
    )


def load_scored_ledger(path: Path) -> list[ScoredForecastRecord]:
    """Same read pattern as `scripts/score_forecast_ledger.py`'s forecast
    loader, but for `ScoredForecastRecord`, tolerant of a missing file."""
    if not path.exists():
        return []
    records = []
    for line in path.read_text().splitlines():
        if line.strip():
            records.append(ScoredForecastRecord.from_dict(json.loads(line)))
    return records


def compute_ablation_results(
    artifacts_dir: Path,
    configs: Sequence[StreamConfig] = STANDARD_CONFIGS,
    loss_field: str = "crps_mean",
    max_lag: int | None = None,
) -> tuple[list[ConfigSummary], list[PairwiseComparison], list[str], list[str]]:
    """Loads each config's scored ledger (noting configs with none yet),
    builds a `LossSeries` per config with records, and delegates to
    `ablation_core` for summaries + pairwise DM comparison. Returns
    `(summaries, comparisons, skipped_pairs, missing_configs)` -- the
    structured results, for callers (e.g. a dashboard) that want more than
    `run_ablation_report`'s markdown string."""
    series_list: list[LossSeries] = []
    missing: list[str] = []
    for config in configs:
        records = load_scored_ledger(scored_ledger_path(artifacts_dir, config))
        if not records:
            missing.append(config.name)
            continue
        series_list.append(loss_series_from_scored_records(config.name, records, loss_field))

    summaries = [summarize_loss_series(s) for s in series_list]
    comparisons, skipped = pairwise_compare(series_list, max_lag=max_lag)
    return summaries, comparisons, skipped, missing


def run_ablation_report(
    artifacts_dir: Path,
    configs: Sequence[StreamConfig] = STANDARD_CONFIGS,
    loss_field: str = "crps_mean",
    max_lag: int | None = None,
) -> str:
    """Markdown report over `compute_ablation_results`."""
    summaries, comparisons, skipped, missing = compute_ablation_results(
        artifacts_dir, configs, loss_field, max_lag
    )
    report = format_ablation_report(summaries, comparisons, skipped=skipped)

    if missing:
        report += "\n\n### Configs with no scored ledger yet\n\n"
        report += "\n".join(f"- {name}" for name in missing)

    return report
