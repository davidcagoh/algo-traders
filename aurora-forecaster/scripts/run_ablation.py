"""
Manual script: builds the pairwise Diebold-Mariano ablation report across
every `STANDARD_CONFIGS` config that has a scored ledger on disk yet.

Pure local file I/O -- no network/model needed -- but kept in `scripts/`
alongside the other manual entry points; the interesting logic
(`aurora_forecaster.ablation.run_ablation_report`) is unit tested in
`tests/test_ablation.py`.

Usage: python scripts/run_ablation.py
"""

from __future__ import annotations

from pathlib import Path

from aurora_forecaster.ablation import STANDARD_CONFIGS, run_ablation_report

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"


def main() -> None:
    report = run_ablation_report(ARTIFACTS_DIR, STANDARD_CONFIGS)
    print(report)

    out_path = ARTIFACTS_DIR / "btc_ablation_report.md"
    out_path.write_text(report)
    print(f"\nwritten to {out_path}")


if __name__ == "__main__":
    main()
