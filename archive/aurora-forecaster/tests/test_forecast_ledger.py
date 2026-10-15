import json

from aurora_forecaster.forecast_ledger import ForecastRecord, append_forecast


def make_record(forecast_id: str = "f-1") -> ForecastRecord:
    return ForecastRecord(
        forecast_id=forecast_id,
        created_at="2026-08-07T00:00:00+00:00",
        asset="BTC",
        modality="unimodal",
        model_id="DecisionIntelligence/Aurora",
        origin_timestamp="2026-08-06T23:00:00+00:00",
        lookback=528,
        horizon=96,
        num_samples=10,
        sample_mean=[1.0, 2.0],
        sample_std=[0.1, 0.2],
    )


def test_round_trip_json_line():
    record = make_record()

    restored = ForecastRecord.from_dict(json.loads(record.to_json_line()))

    assert restored == record


def test_append_forecast_is_append_only(tmp_path):
    path = tmp_path / "ledger.jsonl"

    append_forecast(path, make_record("f-1"))
    append_forecast(path, make_record("f-2"))

    lines = path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["forecast_id"] == "f-1"
    assert json.loads(lines[1])["forecast_id"] == "f-2"


def test_text_config_defaults_to_unimodal():
    record = make_record()

    assert record.text_config == "unimodal"


def test_from_dict_defaults_text_config_for_old_lines_missing_the_key():
    old_line = make_record()
    d = json.loads(old_line.to_json_line())
    del d["text_config"]

    restored = ForecastRecord.from_dict(d)

    assert restored.text_config == "unimodal"


def test_round_trip_json_line_with_non_default_text_config():
    record = ForecastRecord(
        forecast_id="f-1",
        created_at="2026-08-07T00:00:00+00:00",
        asset="BTC",
        modality="multimodal",
        model_id="DecisionIntelligence/Aurora",
        origin_timestamp="2026-08-06T23:00:00+00:00",
        lookback=528,
        horizon=96,
        num_samples=10,
        sample_mean=[1.0, 2.0],
        sample_std=[0.1, 0.2],
        text_config="gdelt+currents",
    )

    restored = ForecastRecord.from_dict(json.loads(record.to_json_line()))

    assert restored == record
    assert restored.text_config == "gdelt+currents"


def test_covariate_encoding_defaults_to_text():
    record = make_record()

    assert record.covariate_encoding == "text"


def test_from_dict_defaults_covariate_encoding_for_old_lines_missing_the_key():
    old_line = make_record()
    d = json.loads(old_line.to_json_line())
    del d["covariate_encoding"]

    restored = ForecastRecord.from_dict(d)

    assert restored.covariate_encoding == "text"


def test_round_trip_json_line_with_vision_covariate_encoding():
    record = ForecastRecord(
        forecast_id="f-1",
        created_at="2026-08-07T00:00:00+00:00",
        asset="BTC",
        modality="multimodal",
        model_id="DecisionIntelligence/Aurora",
        origin_timestamp="2026-08-06T23:00:00+00:00",
        lookback=528,
        horizon=96,
        num_samples=10,
        sample_mean=[1.0, 2.0],
        sample_std=[0.1, 0.2],
        text_config="funding-vision",
        covariate_encoding="vision",
    )

    restored = ForecastRecord.from_dict(json.loads(record.to_json_line()))

    assert restored == record
    assert restored.covariate_encoding == "vision"
