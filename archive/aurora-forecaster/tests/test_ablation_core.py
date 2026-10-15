import pytest

from aurora_forecaster.ablation_core import (
    ConfigSummary,
    LossSeries,
    align_common_origins,
    format_ablation_report,
    pairwise_compare,
    summarize_loss_series,
)


def test_loss_series_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        LossSeries(config_name="a", origin_timestamps=("t1", "t2"), losses=(1.0,))


def test_loss_series_rejects_duplicate_timestamps():
    with pytest.raises(ValueError):
        LossSeries(config_name="a", origin_timestamps=("t1", "t1"), losses=(1.0, 2.0))


def test_summarize_loss_series_known_mean_and_std():
    series = LossSeries(
        config_name="unimodal", origin_timestamps=("t1", "t2", "t3", "t4"),
        losses=(1.0, 2.0, 3.0, 4.0),
    )

    summary = summarize_loss_series(series)

    assert summary == ConfigSummary(
        config_name="unimodal", n_origins=4, mean_loss=2.5, std_loss=pytest.approx(1.29099, rel=1e-4)
    )


def test_summarize_loss_series_single_element_has_zero_std():
    series = LossSeries(config_name="unimodal", origin_timestamps=("t1",), losses=(5.0,))

    summary = summarize_loss_series(series)

    assert summary.std_loss == 0.0


def test_align_common_origins_returns_sorted_intersection():
    a = LossSeries(
        config_name="a", origin_timestamps=("t3", "t1", "t2"), losses=(3.0, 1.0, 2.0)
    )
    b = LossSeries(
        config_name="b", origin_timestamps=("t2", "t4", "t1"), losses=(20.0, 40.0, 10.0)
    )

    losses_a, losses_b, common = align_common_origins(a, b)

    assert common == ["t1", "t2"]
    assert losses_a == [1.0, 2.0]
    assert losses_b == [10.0, 20.0]


def test_align_common_origins_raises_on_fewer_than_two_common_origins():
    a = LossSeries(config_name="a", origin_timestamps=("t1",), losses=(1.0,))
    b = LossSeries(config_name="b", origin_timestamps=("t1",), losses=(10.0,))

    with pytest.raises(ValueError):
        align_common_origins(a, b)


def test_align_common_origins_raises_on_disjoint_origins():
    a = LossSeries(config_name="a", origin_timestamps=("t1", "t2"), losses=(1.0, 2.0))
    b = LossSeries(config_name="b", origin_timestamps=("t3", "t4"), losses=(10.0, 20.0))

    with pytest.raises(ValueError):
        align_common_origins(a, b)


def _series(name, timestamps, losses):
    return LossSeries(config_name=name, origin_timestamps=tuple(timestamps), losses=tuple(losses))


def test_pairwise_compare_all_pairs_from_mutually_overlapping_series():
    common_ts = [f"t{i}" for i in range(5)]
    a = _series("a", common_ts, [1.0, 1.1, 0.9, 1.0, 1.05])
    b = _series("b", common_ts, [2.0, 2.1, 1.9, 2.0, 2.05])
    c = _series("c", common_ts, [1.5, 1.6, 1.4, 1.5, 1.55])

    comparisons, skipped = pairwise_compare([a, b, c], max_lag=1)

    assert skipped == []
    pairs = {(cmp.config_a, cmp.config_b) for cmp in comparisons}
    assert pairs == {("a", "b"), ("a", "c"), ("b", "c")}
    for cmp in comparisons:
        assert cmp.n_common_origins == 5
        assert cmp.dm.max_lag == 1


def test_pairwise_compare_skips_pairs_with_too_few_common_origins_without_blocking_others():
    common_ts = [f"t{i}" for i in range(5)]
    a = _series("a", common_ts, [1.0, 1.1, 0.9, 1.0, 1.05])
    b = _series("b", common_ts, [2.0, 2.1, 1.9, 2.0, 2.05])
    gappy = _series("gappy", ["t0"], [5.0])

    comparisons, skipped = pairwise_compare([a, b, gappy])

    pairs = {(cmp.config_a, cmp.config_b) for cmp in comparisons}
    assert pairs == {("a", "b")}
    assert len(skipped) == 2
    assert any("gappy" in reason for reason in skipped)


def test_format_ablation_report_contains_configs_and_skipped_reasons():
    summaries = [
        ConfigSummary(config_name="a", n_origins=5, mean_loss=1.0, std_loss=0.1),
        ConfigSummary(config_name="b", n_origins=5, mean_loss=2.0, std_loss=0.2),
    ]
    common_ts = [f"t{i}" for i in range(5)]
    a = _series("a", common_ts, [1.0, 1.1, 0.9, 1.0, 1.05])
    b = _series("b", common_ts, [2.0, 2.1, 1.9, 2.0, 2.05])
    comparisons, _ = pairwise_compare([a, b])

    report = format_ablation_report(summaries, comparisons, skipped=["c vs d: only 1 common origins"])

    assert "a" in report
    assert "b" in report
    assert "c vs d: only 1 common origins" in report
    assert f"{comparisons[0].dm.p_value:.3f}" in report
