"""One-command orchestration from run specification to immutable artifacts."""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from backtesting_suite.config import RunConfig, load_config
from backtesting_suite.dashboard import write_dashboard
from backtesting_suite.data import load_data_bundle
from backtesting_suite.execution.bar import BarExecutionModel
from backtesting_suite.execution.base import ExecutionModel
from backtesting_suite.report import build_summary, write_report
from backtesting_suite.result import BacktestResult
from backtesting_suite.strategy import assert_no_lookahead, load_strategy, normalize_targets


class CachedRunError(RuntimeError):
    def __init__(self, directory: Path):
        self.directory = directory
        super().__init__(
            f"identical run already exists at {directory}; pass force=True to recompute"
        )


def _code_hash(value: Any) -> str:
    """Hash the defining module when possible, falling back to object source."""

    module = inspect.getmodule(value.__class__)
    module_path = Path(module.__file__).resolve() if module and module.__file__ else None
    if module_path and module_path.exists():
        return hashlib.sha256(module_path.read_bytes()).hexdigest()
    try:
        source = inspect.getsource(value.__class__)
    except (OSError, TypeError):
        source = repr(value)
    return hashlib.sha256(source.encode()).hexdigest()


def _suite_hash() -> str:
    package = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(package.rglob("*.py")):
        digest.update(str(path.relative_to(package)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _git_ref(root: Path) -> str | None:
    process = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False
    )
    if process.returncode != 0:
        return None
    return process.stdout.strip() or None


def _execution_model(import_path: str) -> ExecutionModel:
    if import_path == "bar":
        return BarExecutionModel()
    if ":" not in import_path:
        raise ValueError("custom execution model must use module:object syntax")
    module_name, object_name = import_path.split(":", 1)
    value = getattr(importlib.import_module(module_name), object_name)
    model = value() if isinstance(value, type) else value
    if not isinstance(model, ExecutionModel):
        raise TypeError(f"{import_path} does not implement simulate(data, targets, config)")
    return model


def _run_id(
    config: RunConfig,
    dataset_hash: str,
    strategy_hash: str,
    execution_hash: str,
    suite_hash: str,
) -> str:
    payload = {
        "config": config.to_dict(),
        "dataset_sha256": dataset_hash,
        "strategy_sha256": strategy_hash,
        "execution_sha256": execution_hash,
        "suite_sha256": suite_hash,
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def _record_trial(
    config: RunConfig,
    directory: Path,
    summary: dict[str, Any],
    run_id: str,
    code_ref: str | None,
    artifacts_root: Path,
) -> None:
    try:
        from evaluation import DuplicateTrialError, TrialLedger, TrialRecord
    except ImportError:
        return
    cost_id = hashlib.sha256(
        json.dumps(config.to_dict()["execution"], sort_keys=True).encode()
    ).hexdigest()[:12]
    record = TrialRecord(
        trial_id=run_id,
        created_at=datetime.now(UTC).isoformat(),
        family=config.experiment,
        strategy=config.strategy.import_path,
        params=config.strategy.params,
        dataset_id=summary["dataset"]["manifest_sha256"],
        split_id=f"{config.data.start}:{config.data.end}",
        status="completed",
        code_ref=code_ref,
        cost_model_id=cost_id,
        sharpe=summary["metrics"]["sharpe"],
        n_obs=summary["metrics"]["n_obs"],
        returns_artifact=str(directory / "returns.parquet"),
        notes=config.notes,
        project=config.experiment,
        venue=config.data.market,
        evidence_stage="backtest",
        gate_outcome="n/a",
    )
    ledger = TrialLedger(artifacts_root / "trials.jsonl")
    try:
        ledger.append(record)
    except DuplicateTrialError:
        pass


def run_backtest(
    config_or_path: RunConfig | str | Path,
    *,
    root: str | Path = ".",
    force: bool = False,
) -> tuple[BacktestResult, Path, dict[str, Any]]:
    workspace = Path(root).resolve()
    config = load_config(config_or_path) if not isinstance(config_or_path, RunConfig) else config_or_path
    data = load_data_bundle(config.data, workspace)
    if str(workspace) not in sys.path:
        sys.path.insert(0, str(workspace))
    strategy = load_strategy(config.strategy.import_path)
    targets = normalize_targets(strategy.generate_targets(data, config.strategy.params), data)
    if config.strategy.no_lookahead_check:
        assert_no_lookahead(strategy, data, config.strategy.params, targets)
    strategy_hash = _code_hash(strategy)
    model = _execution_model(config.execution.model)
    execution_hash = _code_hash(model)
    suite_hash = _suite_hash()
    run_id = _run_id(
        config,
        data.metadata["dataset_sha256"],
        strategy_hash,
        execution_hash,
        suite_hash,
    )
    directory = workspace / config.artifacts_dir / config.experiment / run_id
    if (directory / "summary.json").exists() and not force:
        raise CachedRunError(directory)

    result = model.simulate(data, targets, config.execution)
    code_ref = _git_ref(workspace)
    result.metadata.update(
        {
            "run_id": run_id,
            "experiment": config.experiment,
            "strategy": config.strategy.import_path,
            "strategy_sha256": strategy_hash,
            "execution_sha256": execution_hash,
            "suite_sha256": suite_hash,
            "manifest_sha256": data.metadata["manifest_sha256"],
            "code_ref": code_ref,
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    directory.mkdir(parents=True, exist_ok=True)
    result.save(directory)
    (directory / "resolved-config.yaml").write_text(
        yaml.safe_dump(config.to_dict(), sort_keys=False)
    )
    summary, markdown = build_summary(config, data, result)
    summary["run_id"] = run_id
    summary["code_ref"] = code_ref
    write_report(directory, summary, markdown)
    write_dashboard(directory, config, data, result, summary)
    (directory / "dataset-manifest.json").write_bytes(Path(data.metadata["manifest_path"]).read_bytes())
    _record_trial(
        config,
        directory,
        summary,
        run_id,
        code_ref,
        workspace / config.artifacts_dir,
    )
    return result, directory, summary
