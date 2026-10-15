import pandas as pd
import pytest

from forecast_evaluation.metrics import score_by_lead, score_cumulative


def forecast_rows():
    rows = []
    actuals = [0.01, -0.02, 0.03, -0.01]
    for origin_index, actual in enumerate(actuals):
        for lead in (1, 2):
            value = actual * lead
            for model, point in (
                ("timesfm3", value * 0.5), ("zero_return", 0.0), ("last_return", value * 0.25)
            ):
                row = {
                    "segment": "historical", "mode": "univariate", "symbol": "BTC",
                    "origin": f"origin-{origin_index}", "lead": lead, "actual": value,
                    "model": model, "point": point,
                }
                row.update({
                    f"q{level}": point + (level - 50) / 2000 if model == "timesfm3" else float("nan")
                    for level in range(10, 100, 10)
                })
                rows.append(row)
    return pd.DataFrame(rows)


def test_lead_scores_include_quantile_coverage_and_baseline_skill():
    rows = score_by_lead(forecast_rows())
    model = next(row for row in rows if row["lead_hours"] == 1 and row["model"] == "timesfm3")

    assert model["n"] == 4
    assert model["pinball_loss"] >= 0
    assert 0 <= model["nominal_80_coverage"] <= 1
    assert model["nominal_80_width"] == pytest.approx(0.04)
    assert model["skill_vs_zero_mae"] > 0
    assert model["skill_vs_last_return_mae"] > 0


def test_cumulative_scores_sum_hourly_targets_and_predictions():
    rows = score_cumulative(forecast_rows(), [1, 2, 3])
    timesfm = next(
        row for row in rows if row["model"] == "timesfm3" and row["lead_hours"] == 2
    )

    assert timesfm["n"] == 4
    assert timesfm["mae"] > 0
    assert timesfm["skill_vs_zero_mae"] > 0
    assert {row["lead_hours"] for row in rows} == {1, 2}


def test_lead_metrics_reject_crossed_quantiles():
    frame = forecast_rows()
    target = frame.index[frame.model == "timesfm3"][0]
    frame.loc[target, [f"q{level}" for level in range(10, 100, 10)]] = [
        0.2, 0.1, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9
    ]
    with pytest.raises(ValueError, match="ordered"):
        score_by_lead(frame)
