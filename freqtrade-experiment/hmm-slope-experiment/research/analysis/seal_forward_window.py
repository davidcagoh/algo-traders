#!/usr/bin/env python3
"""Seal the precommitted 2026-06-01..2026-12-31 forward-test window.

`STATUS.md` (root `evaluation-framework/`, and this project's own records)
states this window "should not be partially inspected if it is to remain a
valid one-shot gate" — until now that was enforced by memory only. This
script makes the seal mechanical: any future data load that calls
`evaluation.holdout.guard()` against this window will raise unless someone
explicitly and irreversibly calls `break_seal()` with a recorded reason.

Usage:
    ./.venv/bin/python research/analysis/seal_forward_window.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "evaluation-framework"))
from evaluation.holdout import seal_holdout

REPO_ROOT = Path(__file__).resolve().parent.parent
SEALS_PATH = REPO_ROOT / "analysis" / "holdout_seals.jsonl"


def main() -> None:
    seal = seal_holdout(
        name="hmm-sma-slope-forward-2026H2",
        start="2026-06-01",
        end="2026-12-31",
        path=SEALS_PATH,
    )
    print(f"sealed {seal.name!r}: {seal.start}..{seal.end} (status={seal.status})")
    print(f"manifest: {SEALS_PATH}")


if __name__ == "__main__":
    main()
