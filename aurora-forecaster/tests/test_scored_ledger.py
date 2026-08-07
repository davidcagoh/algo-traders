import json

from aurora_forecaster.scored_ledger import ScoredForecastRecord, append_scored


def make_record(forecast_id: str = "f-1") -> ScoredForecastRecord:
    return ScoredForecastRecord(
        forecast_id=forecast_id,
        scored_at="2026-08-07T00:00:00+00:00",
        asset="BTC",
        modality="unimodal",
        model_id="DecisionIntelligence/Aurora",
        origin_timestamp="2026-08-06T23:00:00+00:00",
        crps_per_step=[1.0, 2.0],
        crps_mean=1.5,
        mase=0.9,
        skill_score_vs_naive=0.1,
        z_scores=[0.1, -0.2],
    )


def test_round_trip_json_line():
    record = make_record()

    restored = ScoredForecastRecord.from_dict(json.loads(record.to_json_line()))

    assert restored == record


def test_append_scored_is_append_only(tmp_path):
    path = tmp_path / "scored.jsonl"

    append_scored(path, make_record("f-1"))
    append_scored(path, make_record("f-2"))

    lines = path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["forecast_id"] == "f-1"
    assert json.loads(lines[1])["forecast_id"] == "f-2"
