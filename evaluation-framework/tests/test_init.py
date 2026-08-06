from __future__ import annotations

import evaluation


def test_all_matches_actual_module_attributes():
    for name in evaluation.__all__:
        assert hasattr(evaluation, name), f"__all__ lists {name!r} but it isn't importable"


def test_all_has_no_duplicates():
    assert len(evaluation.__all__) == len(set(evaluation.__all__))
