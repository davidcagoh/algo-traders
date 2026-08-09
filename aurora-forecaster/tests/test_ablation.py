
import pytest

from aurora_forecaster.ablation import (
    CURRENTS_ONLY,
    DXY_ONLY,
    DXY_VISION,
    FUNDING_ONLY,
    FUNDING_VISION,
    GDELT_CURRENTS,
    GDELT_ONLY,
    RATE_LIMITS_PER_DAY,
    SPY_ONLY,
    SPY_VISION,
    STANDARD_CONFIGS,
    UNIMODAL,
    StreamConfig,
    compute_ablation_results,
    ledger_path,
    load_scored_ledger,
    loss_series_from_scored_records,
    run_ablation_report,
    scored_ledger_path,
    warn_infeasible_sources,
)
from aurora_forecaster.scored_ledger import ScoredForecastRecord, append_scored


def _scored_record(forecast_id, origin_timestamp, crps_mean, text_config="unimodal"):
    return ScoredForecastRecord(
        forecast_id=forecast_id,
        scored_at="2026-08-08T00:00:00+00:00",
        asset="BTC",
        modality="unimodal" if text_config == "unimodal" else "multimodal",
        model_id="DecisionIntelligence/Aurora",
        origin_timestamp=origin_timestamp,
        crps_per_step=[crps_mean],
        crps_mean=crps_mean,
        mase=0.9,
        skill_score_vs_naive=0.1,
        z_scores=[0.1],
        text_config=text_config,
    )


def test_stream_config_modality_derived_from_sources():
    assert UNIMODAL.modality == "unimodal"
    assert GDELT_ONLY.modality == "multimodal"
    assert FUNDING_ONLY.modality == "multimodal"
    assert FUNDING_VISION.modality == "multimodal"


def test_standard_configs_excludes_alphavantage():
    names = [c.name for c in STANDARD_CONFIGS]
    assert "alphavantage" not in names
    assert set(names) == {
        "unimodal", "gdelt", "currents", "gdelt+currents", "funding", "dxy", "spy",
        "funding-vision", "dxy-vision", "spy-vision",
    }


def test_rate_limits_per_day_has_no_cap_for_funding_dxy_spy():
    assert RATE_LIMITS_PER_DAY["funding"] is None
    assert RATE_LIMITS_PER_DAY["dxy"] is None
    assert RATE_LIMITS_PER_DAY["spy"] is None


def test_ledger_path_for_new_configs(tmp_path):
    assert ledger_path(tmp_path, FUNDING_ONLY) == tmp_path / "btc_funding_forecast_ledger.jsonl"
    assert ledger_path(tmp_path, DXY_ONLY) == tmp_path / "btc_dxy_forecast_ledger.jsonl"
    assert ledger_path(tmp_path, SPY_ONLY) == tmp_path / "btc_spy_forecast_ledger.jsonl"


def test_ledger_path_for_vision_configs(tmp_path):
    assert (
        ledger_path(tmp_path, FUNDING_VISION)
        == tmp_path / "btc_funding-vision_forecast_ledger.jsonl"
    )
    assert ledger_path(tmp_path, DXY_VISION) == tmp_path / "btc_dxy-vision_forecast_ledger.jsonl"
    assert ledger_path(tmp_path, SPY_VISION) == tmp_path / "btc_spy-vision_forecast_ledger.jsonl"


def test_warn_infeasible_sources_checks_vision_sources_too():
    over_cap_vision_config = StreamConfig(name="av-vision", vision_sources=("alphavantage",))

    warnings = warn_infeasible_sources(over_cap_vision_config, num_origins=30)

    assert len(warnings) == 1
    assert "25" in warnings[0]


def test_ledger_path_preserves_existing_unimodal_filename(tmp_path):
    assert ledger_path(tmp_path, UNIMODAL) == tmp_path / "btc_unimodal_forecast_ledger.jsonl"
    assert (
        scored_ledger_path(tmp_path, UNIMODAL) == tmp_path / "btc_unimodal_forecast_scored.jsonl"
    )


def test_ledger_path_multi_source_config_uses_joined_name(tmp_path):
    assert (
        ledger_path(tmp_path, GDELT_CURRENTS)
        == tmp_path / "btc_gdelt+currents_forecast_ledger.jsonl"
    )


def test_warn_infeasible_sources_flags_alphavantage_over_cap():
    alphavantage_config = StreamConfig(name="alphavantage", sources=("alphavantage",))

    warnings = warn_infeasible_sources(alphavantage_config, num_origins=30)

    assert len(warnings) == 1
    assert "25" in warnings[0]


def test_warn_infeasible_sources_gdelt_never_warns():
    assert warn_infeasible_sources(GDELT_ONLY, num_origins=10_000) == []


def test_warn_infeasible_sources_under_cap_no_warning():
    assert warn_infeasible_sources(CURRENTS_ONLY, num_origins=5) == []


def test_loss_series_from_scored_records_sorts_and_extracts_field():
    records = [
        _scored_record("f-2", "t2", 2.0),
        _scored_record("f-1", "t1", 1.0),
        _scored_record("f-3", "t3", 3.0),
    ]

    series = loss_series_from_scored_records("unimodal", records)

    assert series.origin_timestamps == ("t1", "t2", "t3")
    assert series.losses == (1.0, 2.0, 3.0)


def test_loss_series_from_scored_records_alternate_loss_field():
    records = [_scored_record("f-1", "t1", 1.0)]

    series = loss_series_from_scored_records("unimodal", records, loss_field="mase")

    assert series.losses == (0.9,)


def test_loss_series_from_scored_records_rejects_bad_field():
    records = [_scored_record("f-1", "t1", 1.0)]

    with pytest.raises(AttributeError):
        loss_series_from_scored_records("unimodal", records, loss_field="not_a_field")


def test_load_scored_ledger_round_trips(tmp_path):
    path = tmp_path / "scored.jsonl"
    append_scored(path, _scored_record("f-1", "t1", 1.0))
    append_scored(path, _scored_record("f-2", "t2", 2.0))

    records = load_scored_ledger(path)

    assert [r.forecast_id for r in records] == ["f-1", "f-2"]


def test_load_scored_ledger_missing_file_returns_empty_list(tmp_path):
    assert load_scored_ledger(tmp_path / "does_not_exist.jsonl") == []


def test_run_ablation_report_skips_configs_with_no_scored_ledger(tmp_path):
    common_ts = [f"t{i}" for i in range(5)]
    unimodal_path = scored_ledger_path(tmp_path, UNIMODAL)
    gdelt_path = scored_ledger_path(tmp_path, GDELT_ONLY)
    for i, ts in enumerate(common_ts):
        append_scored(unimodal_path, _scored_record(f"u-{i}", ts, 1.0 + i * 0.1, "unimodal"))
        append_scored(gdelt_path, _scored_record(f"g-{i}", ts, 0.9 + i * 0.1, "gdelt"))

    report = run_ablation_report(tmp_path, configs=STANDARD_CONFIGS)

    assert "unimodal" in report
    assert "gdelt" in report
    assert "no scored ledger yet" in report
    assert "currents" in report  # named in the "no scored ledger yet" note


def test_compute_ablation_results_returns_structured_tuple(tmp_path):
    common_ts = [f"t{i}" for i in range(5)]
    unimodal_path = scored_ledger_path(tmp_path, UNIMODAL)
    gdelt_path = scored_ledger_path(tmp_path, GDELT_ONLY)
    for i, ts in enumerate(common_ts):
        append_scored(unimodal_path, _scored_record(f"u-{i}", ts, 1.0 + i * 0.1, "unimodal"))
        append_scored(gdelt_path, _scored_record(f"g-{i}", ts, 0.9 + i * 0.1, "gdelt"))

    summaries, comparisons, skipped, missing = compute_ablation_results(
        tmp_path, configs=STANDARD_CONFIGS
    )

    assert {s.config_name for s in summaries} == {"unimodal", "gdelt"}
    assert len(comparisons) == 1
    assert comparisons[0].n_common_origins == 5
    assert skipped == []
    assert "currents" in missing
    assert "unimodal" not in missing
