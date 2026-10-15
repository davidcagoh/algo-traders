import pandas as pd
import pytest

from forecast_evaluation.inference import compare_forecasts, validate_forecasts


def known_answer_rows(origins: int = 24) -> pd.DataFrame:
    rows = []
    for index in range(origins):
        origin = pd.Timestamp("2025-01-01", tz="UTC") + pd.Timedelta(weeks=index)
        for lead in (1, 2):
            actual = 1.0
            for model, point in (
                ("timesfm3", actual), ("zero_return", 0.0), ("last_return", 0.0)
            ):
                rows.append({
                    "segment": "historical_replay", "mode": "univariate",
                    "symbol": "BTC", "origin": origin.isoformat(), "lead": lead,
                    "actual": actual, "model": model, "point": point,
                })
    return pd.DataFrame(rows)


def test_known_answer_comparison_has_negative_loss_difference_and_adjusted_p():
    forecasts = known_answer_rows()
    result = compare_forecasts(forecasts, [1, 2], n_boot=999, seed=8)
    repeated = compare_forecasts(forecasts, [1, 2], n_boot=999, seed=8)
    assert repeated == result
    comparisons = result["comparisons"]
    assert result["status"] == "exploratory_post_hoc"
    assert result["multiplicity"]["family_size"] == len(comparisons)
    assert all(item["mae_difference"] < 0 for item in comparisons)
    assert all(item["ci95_high"] < 0 for item in comparisons)
    assert all(item["p_value_holm"] <= 0.05 for item in comparisons)


def test_integrity_rejects_duplicate_or_misaligned_realized_targets():
    forecasts = known_answer_rows()
    validate_forecasts(forecasts)

    with pytest.raises(ValueError, match="duplicate"):
        validate_forecasts(pd.concat([forecasts, forecasts.iloc[[0]]], ignore_index=True))

    changed = forecasts.copy()
    changed.loc[changed.index[0], "actual"] += 0.25
    with pytest.raises(ValueError, match="identical realized targets"):
        validate_forecasts(changed)


def test_integrity_rejects_missing_baseline_pairs():
    forecasts = known_answer_rows()
    forecasts = forecasts.loc[~(
        (forecasts["origin"] == forecasts["origin"].iloc[0])
        & (forecasts["lead"] == 1)
        & (forecasts["model"] == "zero_return")
    )]
    with pytest.raises(ValueError, match="incomplete"):
        validate_forecasts(forecasts)
