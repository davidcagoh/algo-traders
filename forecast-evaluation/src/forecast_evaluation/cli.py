"""Command-line entry points for evaluation and offline report generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from forecast_evaluation import __version__
from forecast_evaluation.data import ReturnSeries, load_snapshot, make_return_series
from forecast_evaluation.inference import compare_forecasts
from forecast_evaluation.metrics import summarize
from forecast_evaluation.report import render_report, write_report
from forecast_evaluation.runner import Segment, evaluate_segment, origin_indices
from forecast_evaluation.timesfm_backend import MODEL_ID, MODEL_REVISION, PACKAGE_VERSION, TimesFM3Adapter


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _source_hash(package_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(package_root.rglob("*.py")):
        digest.update(path.relative_to(package_root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _git_head(workspace: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=workspace,
            check=True, capture_output=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def _parse_leads(value: int | str | list[int]) -> tuple[int, ...]:
    if isinstance(value, int):
        return (value,)
    if isinstance(value, str) and ".." in value:
        first, last = value.split("..", maxsplit=1)
        return tuple(range(int(first), int(last) + 1))
    if isinstance(value, list):
        return tuple(int(item) for item in value)
    raise ValueError(f"invalid scored_leads value: {value!r}")


def _segments(protocol: dict[str, Any]) -> list[Segment]:
    result = []
    for raw in protocol["segments"]:
        leads = _parse_leads(raw["scored_leads"])
        result.append(Segment(
            name=raw["name"],
            max_horizon=int(raw["max_horizon"]),
            stride_hours=int(raw["origin_stride_hours"]),
            scored_leads=leads,
            start=raw.get("origin_start"),
            end=raw.get("origin_end"),
            target_cutoff_exclusive=raw.get("target_cutoff_exclusive"),
        ))
    return result


def _aligned(series: dict[str, ReturnSeries]) -> None:
    if not series:
        raise ValueError("protocol contains no series")
    first = next(iter(series.values())).timestamps
    for item in series.values():
        if not item.timestamps.equals(first):
            raise ValueError("BTC and ETH must share an identical hourly grid")


def validate_command(args: argparse.Namespace) -> dict[str, Any]:
    """Validate pinned input and report the origin schedule without model loading."""
    workspace = Path(args.workspace).resolve()
    protocol_path = Path(args.protocol)
    if not protocol_path.is_absolute():
        protocol_path = workspace / protocol_path
    protocol_text = protocol_path.read_text()
    protocol = json.loads(protocol_text)
    pin = protocol["snapshot"]
    snapshot = load_snapshot(
        workspace / pin["manifest"],
        expected_snapshot_id=pin["snapshot_id"],
        expected_sha256=pin["data_sha256"],
        workspace=workspace,
    )
    series = {
        symbol: make_return_series(snapshot.bars, symbol)
        for symbol in pin["symbols"]
    }
    _aligned(series)
    counts = []
    for segment in _segments(protocol):
        for symbol, item in series.items():
            counts.append({
                "segment": segment.name,
                "symbol": symbol,
                "origins": len(origin_indices(
                    item,
                    context_length=int(protocol["target"]["context_length"]),
                    segment=segment,
                )),
            })
    return {
        "protocol": protocol["protocol_version"],
        "protocol_sha256": _sha256_bytes(protocol_text.encode()),
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_sha256": snapshot.data_sha256,
        "source_table": snapshot.source_table,
        "symbols": list(snapshot.symbols),
        "rows": len(snapshot.bars),
        "start": snapshot.bars["timestamp"].min().isoformat(),
        "end": snapshot.bars["timestamp"].max().isoformat(),
        "origin_counts": counts,
        "model_loaded": False,
    }


def evaluate_command(args: argparse.Namespace) -> Path:
    workspace = Path(args.workspace).resolve()
    protocol_path = Path(args.protocol)
    if not protocol_path.is_absolute():
        protocol_path = workspace / protocol_path
    protocol_text = protocol_path.read_text()
    protocol = json.loads(protocol_text)
    pin = protocol["snapshot"]
    snapshot = load_snapshot(
        workspace / pin["manifest"],
        expected_snapshot_id=pin["snapshot_id"],
        expected_sha256=pin["data_sha256"],
        workspace=workspace,
    )
    series = {
        symbol: make_return_series(snapshot.bars, symbol)
        for symbol in pin["symbols"]
    }
    _aligned(series)

    package_root = Path(__file__).resolve().parent
    source_sha256 = _source_hash(package_root)
    protocol_sha256 = _sha256_bytes(protocol_text.encode())
    modes = ["univariate", "multivariate"] if args.include_multivariate else ["univariate"]
    identity = {
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_sha256": snapshot.data_sha256,
        "protocol_sha256": protocol_sha256,
        "evaluator_source_sha256": source_sha256,
        "model": protocol["model"],
        "modes": modes,
    }
    run_id = _sha256_bytes(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    )[:20]
    run_dir = workspace / "forecast-evaluation" / "runs" / run_id
    if run_dir.exists():
        print(f"cached run: {run_dir}")
        print(f"run ID: {run_id}")
        return run_dir

    model_config = protocol["model"]
    forecaster = TimesFM3Adapter(device=model_config["device"])
    frames = []
    for segment in _segments(protocol):
        for mode in modes:
            print(f"evaluating {segment.name} ({mode})")
            frames.append(evaluate_segment(
                series,
                forecaster,
                segment=segment,
                context_length=int(protocol["target"]["context_length"]),
                mode=mode,
            ))
    forecasts = pd.concat(frames, ignore_index=True)
    metrics = summarize(forecasts, protocol["cumulative_horizons"])

    try:
        import torch
        torch_version = torch.__version__
    except ImportError:
        torch_version = None
    metadata = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "package_version": __version__,
        "python_version": platform.python_version(),
        "torch_version": torch_version,
        "device": forecaster.device,
        "snapshot": {
            "id": snapshot.snapshot_id,
            "sha256": snapshot.data_sha256,
            "source_table": snapshot.source_table,
            "manifest": str(snapshot.manifest_path.relative_to(workspace)),
            "data_file": str(snapshot.data_path.relative_to(workspace)),
            "symbols": list(snapshot.symbols),
            "rows": int(len(snapshot.bars)),
        },
        "model": {
            "name": "TimesFM 3.0",
            "package": "timesfm",
            "package_version": PACKAGE_VERSION,
            "checkpoint": MODEL_ID,
            "revision": MODEL_REVISION,
            "config": model_config,
        },
        "protocol": {
            "version": protocol["protocol_version"],
            "sha256": protocol_sha256,
            "evaluator_source_sha256": source_sha256,
            "git_head": _git_head(workspace),
            "modes": modes,
            "config": protocol,
        },
        "origin_counts": (
            forecasts[["segment", "mode", "symbol", "origin"]]
            .drop_duplicates().groupby(["segment", "mode", "symbol"])
            .size().rename("origins").reset_index().to_dict(orient="records")
        ),
        "limitations": [
            "Historical replay targets may overlap TimesFM pretraining.",
            "Post-release freshness results have only 15 origins and are exploratory.",
            "q10-q90 intervals are nominal and have not been calibrated.",
            "Forecast accuracy is not evidence of a profitable trading strategy.",
            "TimesFM 3.0 checkpoint weights are restricted to non-commercial, non-production use.",
        ],
    }

    run_dir.parent.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir()
    forecasts.to_parquet(run_dir / "forecasts.parquet", index=False, compression="zstd")
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False) + "\n")
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n")
    (run_dir / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    print(f"run ID: {run_id}")
    print(f"artifacts: {run_dir}")
    return run_dir


def analyze_command(args: argparse.Namespace) -> Path:
    """Add an immutable, post-hoc inference bundle to a saved forecast run."""
    workspace = Path(args.workspace).resolve()
    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = workspace / run_dir
    run_dir = run_dir.resolve()
    forecasts_path = run_dir / "forecasts.parquet"
    protocol_path = run_dir / "protocol.json"
    forecasts = pd.read_parquet(forecasts_path)
    protocol_text = protocol_path.read_text()
    protocol = json.loads(protocol_text)
    inference_path = Path(__file__).resolve().parent / "inference.py"
    bootstrap_path = Path(__file__).resolve().parents[3] / "evaluation-framework/evaluation/bootstrap.py"
    inference_sha256 = _sha256_bytes(inference_path.read_bytes())
    source_identity = {
        "forecast_run_id": run_dir.name,
        "forecast_sha256": _sha256_bytes(forecasts_path.read_bytes()),
        "protocol_sha256": _sha256_bytes(protocol_text.encode()),
        "inference_source_sha256": inference_sha256,
        "shared_bootstrap_source_sha256": _sha256_bytes(bootstrap_path.read_bytes()),
        "bootstrap_replicates": int(args.bootstrap_replicates),
        "block_length_origins": int(args.block_length),
        "seed": int(args.seed),
    }
    analysis_id = _sha256_bytes(
        json.dumps(source_identity, sort_keys=True, separators=(",", ":")).encode()
    )[:20]
    analysis_dir = workspace / "forecast-evaluation" / "analyses" / run_dir.name / analysis_id
    if not analysis_dir.exists():
        analysis = compare_forecasts(
            forecasts,
            protocol["cumulative_horizons"],
            n_boot=args.bootstrap_replicates,
            block_len=args.block_length,
            seed=args.seed,
        )
        analysis["analysis_id"] = analysis_id
        analysis["source"] = source_identity
        analysis_dir.mkdir(parents=True)
        (analysis_dir / "analysis.json").write_text(
            json.dumps(analysis, indent=2, allow_nan=False) + "\n"
        )
    report_path = analysis_dir / "report.html"
    report_path.write_text(
        render_report(run_dir, analysis_path=analysis_dir / "analysis.json")
    )
    print(f"analysis ID: {analysis_id}")
    print(f"review bundle: {analysis_dir}")
    return analysis_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="timesfm-eval")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="verify snapshot, data grid, and origins without loading TimesFM")
    validate.add_argument("--workspace", default=".")
    validate.add_argument("--protocol", default="forecast-evaluation/protocol.json")
    evaluate = commands.add_parser("evaluate", help="run the pinned rolling-origin evaluation")
    evaluate.add_argument("--workspace", default=".")
    evaluate.add_argument("--protocol", default="forecast-evaluation/protocol.json")
    evaluate.add_argument(
        "--include-multivariate", action="store_true",
        help="after univariate evaluation, include the aligned two-target experiment",
    )
    report = commands.add_parser("report", help="render a standalone HTML report from saved artifacts")
    report.add_argument("run_dir")
    analyze = commands.add_parser(
        "analyze", help="add paired uncertainty and multiple-comparison inference to a saved run"
    )
    analyze.add_argument("run_dir", help="saved forecast run directory")
    analyze.add_argument("--workspace", default=".")
    analyze.add_argument("--bootstrap-replicates", type=int, default=10_000)
    analyze.add_argument("--block-length", type=int, default=4)
    analyze.add_argument("--seed", type=int, default=20261014)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "validate":
        try:
            print(json.dumps(validate_command(args), indent=2))
        except (OSError, ValueError, KeyError) as exc:
            parser.error(str(exc))
    elif args.command == "evaluate":
        try:
            run_dir = evaluate_command(args)
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            parser.error(str(exc))
        print(f"report command: timesfm-eval report {run_dir}")
    else:
        try:
            if args.command == "report":
                report_path = write_report(args.run_dir)
            else:
                report_path = analyze_command(args) / "report.html"
        except (OSError, ValueError, ImportError) as exc:
            parser.error(str(exc))
        print(f"report: {report_path}")


if __name__ == "__main__":
    main()
