"""Small CLI for validating, running, and comparing research backtests."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from backtesting_suite.clickhouse import (
    ClickHouseClient,
    ClickHouseError,
    inspect_dataset,
    list_sources,
    snapshot_dataset,
)
from backtesting_suite.config import RunConfig, load_config
from backtesting_suite.data import load_data_bundle
from backtesting_suite.runner import CachedRunError, run_backtest, validate_data_execution


def _summary_path(value: str) -> Path:
    path = Path(value)
    return path / "summary.json" if path.is_dir() else path


def _compare(paths: list[str]) -> None:
    rows = []
    for value in paths:
        path = _summary_path(value)
        summary = json.loads(path.read_text())
        rows.append(
            {
                "run": summary.get("run_id", path.parent.name),
                "experiment": summary["experiment"],
                "return": summary["execution"]["total_return_pct"],
                "sharpe": summary["metrics"]["sharpe"],
                "calmar": summary["metrics"]["calmar"],
                "mdd": summary["metrics"]["mdd_pct"],
                "cost": summary["execution"]["transaction_cost"],
            }
        )
    print("| Run | Experiment | Return | Sharpe | Calmar | MDD | TC |")
    print("|---|---|---:|---:|---:|---:|---:|")
    for row in rows:
        print(
            f"| {row['run']} | {row['experiment']} | {row['return']:.2f}% | "
            f"{row['sharpe']:.3f} | {row['calmar']:.3f} | {row['mdd']:.2f}% | "
            f"{row['cost']:.2f} |"
        )


def _run_or_cached(config: RunConfig, force: bool) -> tuple[Path, dict]:
    try:
        _, directory, summary = run_backtest(config, force=force)
    except CachedRunError as exc:
        directory = exc.directory
        summary = json.loads((directory / "summary.json").read_text())
    return directory, summary


def _sweep_costs(config_path: str, component: str, bps_values: list[float], force: bool) -> None:
    config = load_config(config_path)
    matches = [cost for cost in config.execution.transaction_costs if cost.name == component]
    if not matches:
        raise ValueError(f"no transaction cost component named {component!r}")
    if matches[0].type != "proportional":
        raise ValueError(f"cost sweep requires a proportional component, got {matches[0].type!r}")

    rows = []
    for bps in bps_values:
        if bps < 0:
            raise ValueError("sweep bps cannot be negative")
        costs = tuple(
            replace(cost, bps=bps) if cost.name == component else cost
            for cost in config.execution.transaction_costs
        )
        scenario = replace(config, execution=replace(config.execution, transaction_costs=costs))
        directory, summary = _run_or_cached(scenario, force)
        rows.append((bps, directory, summary))

    print(f"| {component} (bps) | Run | Return | Sharpe | TC | Artifacts |")
    print("|---:|---|---:|---:|---:|---|")
    for bps, directory, summary in rows:
        print(
            f"| {bps:g} | {summary['run_id']} | "
            f"{summary['execution']['total_return_pct']:.2f}% | "
            f"{summary['metrics']['sharpe']:.3f} | "
            f"{summary['execution']['transaction_cost']:.2f} | {directory} |"
        )


def _data_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    try:
        client = ClickHouseClient.from_env()
        if args.data_command == "sources":
            for row in list_sources(client):
                rows = row.get("total_rows")
                size = row.get("total_bytes")
                print(
                    f"{row['database']}.{row['name']}\t{row.get('engine', '')}\t"
                    f"rows≈{rows}\tbytes≈{size}"
                )
        elif args.data_command == "inspect":
            print(json.dumps(inspect_dataset(client, args.dataset), indent=2, default=str))
        elif args.data_command == "snapshot":
            manifest = snapshot_dataset(
                client,
                args.dataset,
                start=args.start,
                end=args.end,
                output_dir=args.output_dir,
                workspace=Path.cwd(),
                timeframe=args.timeframe,
                market=args.market,
                symbols=args.symbol or [],
                columns=args.column,
                time_column=args.time_column,
                instrument_column=args.instrument_column,
                max_rows=args.max_rows,
            )
            print(f"snapshot: {manifest}")
            if manifest.name == "manifest.json":
                print("backtest: supported by the bar execution model")
                print("note: perpetual snapshots require funding: false unless a funding source is added")
            else:
                print("backtest: unsupported; this is a raw dataset snapshot")
    except (ClickHouseError, OSError, ValueError) as exc:
        parser.error(str(exc))


def main() -> None:
    parser = argparse.ArgumentParser(prog="bt", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="validate config and data")
    validate_parser.add_argument("config")
    run_parser = subparsers.add_parser("run", help="run one backtest")
    run_parser.add_argument("config")
    run_parser.add_argument("--force", action="store_true")
    compare_parser = subparsers.add_parser("compare", help="compare result summaries")
    compare_parser.add_argument("results", nargs="+")
    sweep_parser = subparsers.add_parser(
        "sweep-costs", help="run one config across proportional cost assumptions"
    )
    sweep_parser.add_argument("config")
    sweep_parser.add_argument("--component", required=True)
    sweep_parser.add_argument("--bps", type=float, nargs="+", required=True)
    sweep_parser.add_argument("--force", action="store_true")

    data_parser = subparsers.add_parser("data", help="inspect and snapshot ClickHouse data")
    data_subparsers = data_parser.add_subparsers(dest="data_command", required=True)
    data_subparsers.add_parser("sources", help="list warehouse databases and tables")
    inspect_parser = data_subparsers.add_parser("inspect", help="inspect one table's schema and coverage")
    inspect_parser.add_argument("dataset", help="database.table")
    snapshot_parser = data_subparsers.add_parser("snapshot", help="save a bounded local Parquet snapshot")
    snapshot_parser.add_argument("dataset", help="database.table")
    snapshot_parser.add_argument("--start", required=True, help="inclusive start date or timestamp")
    snapshot_parser.add_argument("--end", required=True, help="inclusive end date or timestamp")
    snapshot_parser.add_argument("--symbol", action="append", help="instrument filter; repeat to select several")
    snapshot_parser.add_argument("--column", action="append", help="column to include in a raw snapshot")
    snapshot_parser.add_argument("--time-column", help="override the inspected time column for raw snapshots")
    snapshot_parser.add_argument("--instrument-column", help="instrument key for raw snapshot filters")
    snapshot_parser.add_argument("--timeframe", help="bar snapshot interval (default: 1h)")
    snapshot_parser.add_argument("--market", choices=["spot", "perpetual"], help="market type (Binance is verified spot; Hyperliquid is perpetual)")
    snapshot_parser.add_argument("--max-rows", type=int, default=2_000_000)
    snapshot_parser.add_argument("--output-dir", default="data/clickhouse")
    args = parser.parse_args()

    if args.command == "validate":
        config = load_config(args.config)
        data = load_data_bundle(config.data)
        try:
            validate_data_execution(config, data)
        except ValueError as exc:
            parser.error(str(exc))
        print(
            f"valid: {config.experiment} | {data.metadata['table']} | "
            f"{len(data.index)} bars | {', '.join(data.symbols)} | "
            f"{data.metadata['start']} -> {data.metadata['end']}"
        )
    elif args.command == "run":
        try:
            _, directory, summary = run_backtest(args.config, force=args.force)
        except CachedRunError as exc:
            parser.error(str(exc))
        print(f"run: {summary['run_id']}")
        print(f"return: {summary['execution']['total_return_pct']:.2f}%")
        print(f"sharpe: {summary['metrics']['sharpe']:.3f}")
        print(f"artifacts: {directory}")
    elif args.command == "compare":
        _compare(args.results)
    elif args.command == "sweep-costs":
        try:
            _sweep_costs(args.config, args.component, args.bps, args.force)
        except (CachedRunError, ValueError) as exc:
            parser.error(str(exc))
    elif args.command == "data":
        _data_command(args, parser)


if __name__ == "__main__":
    main()
