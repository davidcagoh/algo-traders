from __future__ import annotations

import pandas as pd
import pytest

from evaluation.holdout import HoldoutViolation, break_seal, guard, seal_holdout


def test_seal_holdout_creates_manifest(tmp_path):
    path = tmp_path / "seals.jsonl"
    seal = seal_holdout("fwd-2026", "2026-06-01", "2026-12-31", path)
    assert seal.status == "sealed"
    assert path.exists()


def test_seal_holdout_idempotent_same_bounds(tmp_path):
    path = tmp_path / "seals.jsonl"
    seal_holdout("fwd-2026", "2026-06-01", "2026-12-31", path)
    seal2 = seal_holdout("fwd-2026", "2026-06-01", "2026-12-31", path)
    assert seal2.status == "sealed"


def test_seal_holdout_rejects_changed_bounds(tmp_path):
    path = tmp_path / "seals.jsonl"
    seal_holdout("fwd-2026", "2026-06-01", "2026-12-31", path)
    with pytest.raises(HoldoutViolation):
        seal_holdout("fwd-2026", "2026-06-01", "2026-11-30", path)


def test_guard_raises_on_single_overlapping_timestamp(tmp_path):
    path = tmp_path / "seals.jsonl"
    seal_holdout("fwd-2026", "2026-06-01", "2026-12-31", path)
    idx = pd.date_range("2026-05-01", "2026-06-05", freq="D")
    data = pd.Series(range(len(idx)), index=idx)
    with pytest.raises(HoldoutViolation):
        guard(data, "fwd-2026", path)


def test_guard_passes_outside_window(tmp_path):
    path = tmp_path / "seals.jsonl"
    seal_holdout("fwd-2026", "2026-06-01", "2026-12-31", path)
    idx = pd.date_range("2026-01-01", "2026-03-01", freq="D")
    data = pd.Series(range(len(idx)), index=idx)
    guard(data, "fwd-2026", path)  # should not raise


def test_guard_no_seal_raises(tmp_path):
    path = tmp_path / "seals.jsonl"
    idx = pd.date_range("2026-01-01", "2026-03-01", freq="D")
    data = pd.Series(range(len(idx)), index=idx)
    with pytest.raises(HoldoutViolation):
        guard(data, "no-such-seal", path)


def test_guard_with_date_col(tmp_path):
    path = tmp_path / "seals.jsonl"
    seal_holdout("fwd-2026", "2026-06-01", "2026-12-31", path)
    df = pd.DataFrame({"date": pd.date_range("2026-07-01", periods=5, freq="D"), "x": range(5)})
    with pytest.raises(HoldoutViolation):
        guard(df, "fwd-2026", path, date_col="date")


def test_break_seal_then_guard_passes(tmp_path):
    path = tmp_path / "seals.jsonl"
    seal_holdout("fwd-2026", "2026-06-01", "2026-12-31", path)
    break_seal(
        "fwd-2026", path, reason="manuscript deadline forced early peek", decision_ref="dec-042"
    )
    idx = pd.date_range("2026-07-01", periods=5, freq="D")
    data = pd.Series(range(5), index=idx)
    guard(data, "fwd-2026", path)  # no longer raises, but is logged


def test_break_seal_not_reversible_via_reseal(tmp_path):
    path = tmp_path / "seals.jsonl"
    seal_holdout("fwd-2026", "2026-06-01", "2026-12-31", path)
    break_seal("fwd-2026", path, reason="test", decision_ref="dec-1")
    with pytest.raises(HoldoutViolation):
        seal_holdout("fwd-2026", "2026-06-01", "2026-12-31", path)


def test_break_seal_requires_existing_seal(tmp_path):
    path = tmp_path / "seals.jsonl"
    with pytest.raises(HoldoutViolation):
        break_seal("nonexistent", path, reason="x", decision_ref="y")


def test_guard_access_log_records_every_call(tmp_path):
    path = tmp_path / "seals.jsonl"
    seal_holdout("fwd-2026", "2026-06-01", "2026-12-31", path)
    idx = pd.date_range("2026-01-01", "2026-02-01", freq="D")
    guard(pd.Series(range(len(idx)), index=idx), "fwd-2026", path)
    lines = path.read_text().strip().splitlines()
    events = [__import__("json").loads(line)["event"] for line in lines]
    assert "guard_pass" in events


def test_guard_rejects_non_pandas_without_date_col(tmp_path):
    path = tmp_path / "seals.jsonl"
    seal_holdout("fwd-2026", "2026-06-01", "2026-12-31", path)
    with pytest.raises(TypeError):
        guard([1, 2, 3], "fwd-2026", path)
