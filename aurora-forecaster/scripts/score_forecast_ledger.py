"""
Manual script: score every record in `btc_unimodal_forecast_ledger.jsonl`
against realized BTC prices.

Fetches one contiguous OHLCV span covering every ledger origin's lookback
start through horizon end, aligns each record to it (`realized.py`), scores
it (`scoring.py`), and appends the result to
`artifacts/btc_unimodal_forecast_scored.jsonl`. Needs network access, so
it's excluded from `tests/` by design (same convention as
`rolling_forecast_btc.py`).

Usage: python scripts/score_forecast_ledger.py
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from aurora_forecaster.data.price import fetch_btc_ohlcv
from aurora_forecaster.forecast_ledger import ForecastRecord
from aurora_forecaster.realized import RealizedDataError, align_forecast_to_prices
from aurora_forecaster.scored_ledger import ScoredForecastRecord, append_scored
from aurora_forecaster.scoring import calibration_coverage, crps_gaussian, mase, skill_score

TIMEFRAME = "1h"
TIMEFRAME_MS = 3_600_000

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"
FORECAST_LEDGER_PATH = ARTIFACTS_DIR / "btc_unimodal_forecast_ledger.jsonl"
SCORED_LEDGER_PATH = ARTIFACTS_DIR / "btc_unimodal_forecast_scored.jsonl"


def _load_forecasts(path: Path) -> list[ForecastRecord]:
    with open(path) as f:
        return [ForecastRecord.from_dict(json.loads(line)) for line in f if line.strip()]


def _naive_insample_errors(lookback_closes: list[float]) -> list[float]:
    """Lag-1 naive absolute errors within the lookback window (MASE scale)."""
    return [abs(lookback_closes[i] - lookback_closes[i - 1]) for i in range(1, len(lookback_closes))]


def _naive_forecast_loss(lookback_closes: list[float], realized_closes: list[float]) -> float:
    """Random-walk baseline: hold the last lookback close flat across the horizon."""
    last_close = lookback_closes[-1]
    errors = [abs(y - last_close) for y in realized_closes]
    return sum(errors) / len(errors)


def score_record(record: ForecastRecord, price_df) -> ScoredForecastRecord:
    window = align_forecast_to_prices(record, price_df)

    crps_per_step = [
        crps_gaussian(mu, sigma, y)
        for mu, sigma, y in zip(record.sample_mean, record.sample_std, window.realized_closes)
    ]
    crps_mean = sum(crps_per_step) / len(crps_per_step)

    abs_errors = [abs(y - mu) for mu, y in zip(record.sample_mean, window.realized_closes)]
    naive_errors = _naive_insample_errors(window.lookback_closes)
    mase_value = mase(abs_errors, naive_errors)

    model_loss = sum(abs_errors) / len(abs_errors)
    naive_loss = _naive_forecast_loss(window.lookback_closes, window.realized_closes)
    skill = skill_score(model_loss, naive_loss)

    z_scores = [
        (y - mu) / sigma
        for mu, sigma, y in zip(record.sample_mean, record.sample_std, window.realized_closes)
    ]

    return ScoredForecastRecord(
        forecast_id=record.forecast_id,
        scored_at=datetime.now(UTC).isoformat(),
        asset=record.asset,
        modality=record.modality,
        model_id=record.model_id,
        origin_timestamp=record.origin_timestamp,
        crps_per_step=crps_per_step,
        crps_mean=crps_mean,
        mase=mase_value,
        skill_score_vs_naive=skill,
        z_scores=z_scores,
    )


def main() -> None:
    forecasts = _load_forecasts(FORECAST_LEDGER_PATH)
    print(f"forecasts to score: {len(forecasts)}")
    if not forecasts:
        print("nothing to score")
        return

    earliest_origin_ms = min(
        int(datetime.fromisoformat(r.origin_timestamp).timestamp() * 1000) for r in forecasts
    )
    max_lookback = max(r.lookback for r in forecasts)
    max_horizon = max(r.horizon for r in forecasts)
    span_start_ms = earliest_origin_ms - (max_lookback - 1) * TIMEFRAME_MS
    # +2 rows of slack for inclusive-range rounding.
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    span_rows_needed = (now_ms - span_start_ms) // TIMEFRAME_MS + max_horizon + 2

    print(f"fetching {span_rows_needed} rows of BTC {TIMEFRAME} OHLCV from {datetime.fromtimestamp(span_start_ms / 1000, tz=UTC).isoformat()}")
    price_df = fetch_btc_ohlcv(timeframe=TIMEFRAME, since=span_start_ms, limit=span_rows_needed)
    print(f"price rows fetched: {len(price_df)}")

    all_z_scores: list[float] = []
    scored_count = 0
    for record in forecasts:
        try:
            scored = score_record(record, price_df)
        except RealizedDataError as e:
            print(f"skipping {record.forecast_id} ({record.origin_timestamp}): {e}")
            continue
        append_scored(SCORED_LEDGER_PATH, scored)
        all_z_scores.extend(scored.z_scores)
        scored_count += 1
        print(
            f"{record.forecast_id} origin={record.origin_timestamp}: "
            f"crps_mean={scored.crps_mean:.2f} mase={scored.mase:.3f} "
            f"skill_vs_naive={scored.skill_score_vs_naive:+.3f}"
        )

    print(f"\nscored {scored_count}/{len(forecasts)} forecasts -> {SCORED_LEDGER_PATH}")
    if all_z_scores:
        coverage = calibration_coverage(all_z_scores)
        print("calibration coverage (nominal -> empirical):")
        for level, empirical in coverage.items():
            print(f"  {level:.0%} -> {empirical:.0%}")


if __name__ == "__main__":
    main()
