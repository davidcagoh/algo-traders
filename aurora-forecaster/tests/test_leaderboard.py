from aurora_forecaster.ablation_core import ConfigSummary
from aurora_forecaster.leaderboard import (
    LeaderboardEntry,
    load_leaderboard_history,
    record_leaderboard_entry,
)


def test_record_leaderboard_entry_writes_one_line_per_summary(tmp_path):
    summaries = [
        ConfigSummary(config_name="unimodal", n_origins=12, mean_loss=600.0, std_loss=80.0),
        ConfigSummary(config_name="funding-vision", n_origins=12, mean_loss=550.0, std_loss=60.0),
    ]

    record_leaderboard_entry(tmp_path, summaries, run_at="2026-08-09T00:00:00+00:00")

    history = load_leaderboard_history(tmp_path)
    assert len(history) == 2
    assert history[0] == LeaderboardEntry(
        run_at="2026-08-09T00:00:00+00:00",
        config_name="unimodal",
        n_origins=12,
        mean_loss=600.0,
        std_loss=80.0,
    )
    assert history[1].config_name == "funding-vision"


def test_load_leaderboard_history_missing_file_returns_empty_list(tmp_path):
    assert load_leaderboard_history(tmp_path) == []


def test_record_leaderboard_entry_appends_across_multiple_calls(tmp_path):
    summaries = [ConfigSummary(config_name="unimodal", n_origins=4, mean_loss=666.0, std_loss=83.5)]

    record_leaderboard_entry(tmp_path, summaries, run_at="2026-08-08T00:00:00+00:00")
    record_leaderboard_entry(tmp_path, summaries, run_at="2026-08-09T00:00:00+00:00")

    history = load_leaderboard_history(tmp_path)
    assert len(history) == 2
    assert [e.run_at for e in history] == ["2026-08-08T00:00:00+00:00", "2026-08-09T00:00:00+00:00"]
