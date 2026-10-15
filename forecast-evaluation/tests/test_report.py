import json

import pandas as pd

from forecast_evaluation.metrics import summarize
from forecast_evaluation.report import (
    _directional_accuracy_figure,
    _forecast_figure,
    render_report,
    write_report,
)


def test_report_is_self_contained_and_uses_saved_forecasts(tmp_path):
    rows = []
    for symbol in ("BTC", "ETH"):
        for model, point in (("timesfm3", 0.01), ("zero_return", 0.0), ("last_return", 0.005)):
            for lead, actual in ((1, 0.012), (2, -0.006)):
                row = {
                    "segment": "post_release_freshness", "mode": "univariate", "symbol": symbol,
                    "origin": "2026-09-01T00:00:00+00:00", "lead": lead,
                    "actual": actual, "model": model, "point": point,
                }
                row.update({
                    f"q{level}": point + (level - 50) / 2000 if model == "timesfm3" else float("nan")
                    for level in range(10, 100, 10)
                })
                rows.append(row)
    forecasts = pd.DataFrame(rows)
    metrics = summarize(forecasts, [1, 2])
    metadata = {
        "run_id": "unit-test-run", "created_at": "2026-10-15T00:00:00+00:00",
        "origin_counts": [{"origins": 2}], "device": "cpu", "torch_version": "test",
        "snapshot": {
            "id": "snapshot-id", "rows": 10, "sha256": "sha256",
            "source_table": "binance.candles_1m", "symbols": ["BTC", "ETH"],
        },
        "model": {
            "checkpoint": "google/timesfm-3.0-pytorch", "revision": "revision-id",
            "package_version": "3.0.2",
        },
        "protocol": {"version": "timesfm3-btc-eth-v1", "sha256": "protocol-sha"},
        "limitations": [
            "15 origins only", "nominal intervals are uncalibrated",
            "TimesFM 3.0 checkpoint weights are restricted to non-commercial, non-production use.",
        ],
    }
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    forecasts.to_parquet(run_dir / "forecasts.parquet")
    (run_dir / "metrics.json").write_text(json.dumps(metrics))
    (run_dir / "metadata.json").write_text(json.dumps(metadata))

    document = render_report(run_dir)
    output = write_report(run_dir)

    assert output.is_file()
    assert "Plotly.newPlot" in document
    assert "post_release_freshness" not in document
    assert "q10–q90" in document
    assert "nominal target 80%" in document
    assert "15 origins only" in document
    assert "non-commercial, non-production use" in document
    assert "One-hour return RMSE by forecast lead" in document
    assert "Directional accuracy by forecast lead" in document
    assert "Directional accuracy (%)" in document
    assert "Pinball loss by forecast lead" in document
    assert "One-hour return MAE skill versus baselines" in document
    assert "One-hour return RMSE skill versus baselines" in document
    assert "Cumulative-return RMSE by horizon" in document
    assert "Cumulative-return RMSE skill versus baselines" in document
    assert "Forecast origin" in document
    assert "Protocol" in document
    assert "timesfm3-btc-eth-v1" in document
    assert "binance.candles_1m" in document
    assert "plotly-latest.min.js" not in document

    analysis = {
        "analysis_id": "analysis-id",
        "multiplicity": {"family_size": 10},
        "comparisons": [{
            "segment": "historical_replay", "kind": "cumulative", "horizon": 24,
            "symbol": "BTC", "mode": "univariate", "baseline": "zero_return",
            "mae_difference": -0.001, "ci95_low": -0.002, "ci95_high": -0.0001,
            "p_value_holm": 0.2, "n_origins": 135,
        }, {
            "segment": "post_release_freshness", "kind": "lead", "horizon": 24,
            "symbol": "BTC", "mode": "univariate", "baseline": "zero_return",
            "mae_difference": 0.001, "ci95_low": -0.002, "ci95_high": 0.004,
            "p_value_holm": 1.0, "n_origins": 15,
        }],
    }
    analysis_path = tmp_path / "analysis.json"
    analysis_path.write_text(json.dumps(analysis))
    reviewed_document = render_report(run_dir, analysis_path=analysis_path)
    assert "paired comparisons passes" in reviewed_document
    assert "exploratory rather than confirmatory" in reviewed_document
    assert "Post-release cumulative horizons beyond one hour are unavailable" in reviewed_document
    assert "Marginal return · lead 24h" in reviewed_document
    assert "pointwise block-bootstrap intervals" in reviewed_document


def test_forecast_chart_marks_the_forecast_origin():
    import plotly.graph_objects as go

    forecasts = pd.DataFrame([
        {
            "segment": "historical", "mode": "univariate", "symbol": "BTC",
            "model": "timesfm3", "origin": "2026-09-01T00:00:00+00:00",
            "lead": lead, "q10": -0.01, "q50": 0.0, "q90": 0.01, "actual": 0.0,
        }
        for lead in (1, 2)
    ])

    figure = _forecast_figure(go, forecasts, segment="historical", mode="univariate")

    assert figure.layout.xaxis.range[0] == 0
    assert any(shape.x0 == 0 and shape.x1 == 0 for shape in figure.layout.shapes)
    assert any("Forecast origin" in annotation.text for annotation in figure.layout.annotations)


def test_directional_accuracy_does_not_score_zero_return_as_a_prediction():
    import plotly.graph_objects as go

    rows = pd.DataFrame([
        {"symbol": "BTC", "model": "timesfm3", "lead_hours": 1, "directional_accuracy": 0.75},
        {"symbol": "BTC", "model": "zero_return", "lead_hours": 1, "directional_accuracy": 0.0},
        {"symbol": "BTC", "model": "last_return", "lead_hours": 1, "directional_accuracy": 0.5},
    ])

    figure = _directional_accuracy_figure(go, rows)

    assert [trace.name for trace in figure.data] == ["BTC · timesfm3", "BTC · last_return"]
    assert list(figure.data[0].y) == [75.0]
    assert list(figure.layout.yaxis.range) == [0, 100]
