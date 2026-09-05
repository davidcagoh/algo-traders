"""Typed configuration for one fully reproducible backtest run."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import yaml


class ConfigError(ValueError):
    """Raised when a run configuration is incomplete or inconsistent."""


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigError(f"{name} must be a mapping")
    return value


def _positive(value: Any, name: str) -> float:
    number = float(value)
    if number <= 0:
        raise ConfigError(f"{name} must be positive")
    return number


@dataclass(frozen=True)
class FeatureConfig:
    name: str
    path: str
    member_column: str = "series"
    value_column: str = "value"
    timestamp_column: str = "timestamp"
    members: tuple[str, ...] = ()
    availability_lag: str = "0s"
    fill_method: str = "ffill"

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> FeatureConfig:
        if "name" not in raw or "path" not in raw:
            raise ConfigError("each feature requires name and path")
        fill = str(raw.get("fill_method", "ffill"))
        if fill not in {"ffill", "none"}:
            raise ConfigError("feature.fill_method must be 'ffill' or 'none'")
        availability_lag = str(raw.get("availability_lag", "0s"))
        try:
            lag = pd.Timedelta(availability_lag)
        except ValueError as exc:
            raise ConfigError(f"invalid feature availability_lag {availability_lag!r}") from exc
        if lag < pd.Timedelta(0):
            raise ConfigError("feature availability_lag cannot be negative")
        return cls(
            name=str(raw["name"]),
            path=str(raw["path"]),
            member_column=str(raw.get("member_column", "series")),
            value_column=str(raw.get("value_column", "value")),
            timestamp_column=str(raw.get("timestamp_column", "timestamp")),
            members=tuple(str(item) for item in raw.get("members", [])),
            availability_lag=availability_lag,
            fill_method=fill,
        )


@dataclass(frozen=True)
class DataConfig:
    manifest: str
    market: str
    timeframe: str
    universe: tuple[str, ...]
    start: str
    end: str
    features: tuple[FeatureConfig, ...] = ()

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> DataConfig:
        required = {"manifest", "market", "timeframe", "universe", "start", "end"}
        missing = required - raw.keys()
        if missing:
            raise ConfigError(f"data is missing {sorted(missing)}")
        market = str(raw["market"])
        if market not in {"spot", "perpetual"}:
            raise ConfigError("data.market must be 'spot' or 'perpetual'")
        universe = tuple(str(item) for item in raw["universe"])
        if not universe:
            raise ConfigError("data.universe cannot be empty")
        features = tuple(
            FeatureConfig.from_mapping(_mapping(item, "feature"))
            for item in raw.get("features", [])
        )
        return cls(
            manifest=str(raw["manifest"]),
            market=market,
            timeframe=str(raw["timeframe"]),
            universe=universe,
            start=str(raw["start"]),
            end=str(raw["end"]),
            features=features,
        )


@dataclass(frozen=True)
class StrategyConfig:
    import_path: str
    params: Mapping[str, Any] = field(default_factory=dict)
    no_lookahead_check: bool = True

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> StrategyConfig:
        import_path = raw.get("import")
        if not import_path or ":" not in str(import_path):
            raise ConfigError("strategy.import must use 'module:object' syntax")
        return cls(
            import_path=str(import_path),
            params=dict(_mapping(raw.get("params", {}), "strategy.params")),
            no_lookahead_check=bool(raw.get("no_lookahead_check", True)),
        )


@dataclass(frozen=True)
class CostConfig:
    type: str
    name: str
    bps: float = 0.0
    amount_per_trade: float = 0.0
    coefficient_bps: float = 0.0
    max_participation: float = 0.1

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> CostConfig:
        kind = str(raw.get("type", ""))
        if kind not in {"proportional", "fixed", "square_root_impact"}:
            raise ConfigError(
                "transaction cost type must be proportional, fixed, or square_root_impact"
            )
        name = str(raw.get("name", kind))
        config = cls(
            type=kind,
            name=name,
            bps=float(raw.get("bps", 0.0)),
            amount_per_trade=float(raw.get("amount_per_trade", 0.0)),
            coefficient_bps=float(raw.get("coefficient_bps", 0.0)),
            max_participation=float(raw.get("max_participation", 0.1)),
        )
        if min(config.bps, config.amount_per_trade, config.coefficient_bps) < 0:
            raise ConfigError("transaction costs cannot be negative")
        if not 0 < config.max_participation <= 1:
            raise ConfigError("max_participation must be in (0, 1]")
        return config


@dataclass(frozen=True)
class ConstraintConfig:
    max_gross_exposure: float = 1.0
    max_net_exposure: float = 1.0
    max_abs_weight: float = 1.0
    min_cash_weight: float = 0.0
    violation: str = "raise"

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> ConstraintConfig:
        violation = str(raw.get("violation", "raise"))
        if violation not in {"raise", "scale"}:
            raise ConfigError("constraints.violation must be 'raise' or 'scale'")
        return cls(
            max_gross_exposure=_positive(raw.get("max_gross_exposure", 1.0), "max gross"),
            max_net_exposure=_positive(raw.get("max_net_exposure", 1.0), "max net"),
            max_abs_weight=_positive(raw.get("max_abs_weight", 1.0), "max weight"),
            min_cash_weight=float(raw.get("min_cash_weight", 0.0)),
            violation=violation,
        )


@dataclass(frozen=True)
class ExecutionConfig:
    model: str = "bar"
    price_field: str = "open"
    signal_delay_bars: int = 1
    rebalance_policy: str = "every_bar"
    initial_cash: float = 100_000.0
    funding: bool = True
    annual_borrow_bps: float = 0.0
    missing_price_policy: str = "raise"
    transaction_costs: tuple[CostConfig, ...] = ()
    constraints: ConstraintConfig = field(default_factory=ConstraintConfig)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> ExecutionConfig:
        price_field = str(raw.get("price_field", "open"))
        if price_field not in {"open", "close"}:
            raise ConfigError("execution.price_field must be 'open' or 'close'")
        delay = int(raw.get("signal_delay_bars", 1))
        if delay < 0:
            raise ConfigError("execution.signal_delay_bars cannot be negative")
        missing_policy = str(raw.get("missing_price_policy", "raise"))
        if missing_policy not in {"raise", "zero_return"}:
            raise ConfigError("missing_price_policy must be 'raise' or 'zero_return'")
        rebalance_policy = str(raw.get("rebalance_policy", "every_bar"))
        if rebalance_policy not in {"every_bar", "target_change"}:
            raise ConfigError("rebalance_policy must be 'every_bar' or 'target_change'")
        costs = tuple(
            CostConfig.from_mapping(_mapping(item, "transaction cost"))
            for item in raw.get("transaction_costs", [])
        )
        names = [cost.name for cost in costs]
        if len(names) != len(set(names)):
            raise ConfigError("transaction cost names must be unique")
        reserved = {"transaction_cost", "funding_pnl", "borrow_cost"}
        if collision := reserved.intersection(names):
            raise ConfigError(f"reserved transaction cost names: {sorted(collision)}")
        constraints = ConstraintConfig.from_mapping(
            _mapping(raw.get("constraints", {}), "execution.constraints")
        )
        annual_borrow_bps = float(raw.get("annual_borrow_bps", 0.0))
        if annual_borrow_bps < 0:
            raise ConfigError("annual_borrow_bps cannot be negative")
        return cls(
            model=str(raw.get("model", "bar")),
            price_field=price_field,
            signal_delay_bars=delay,
            rebalance_policy=rebalance_policy,
            initial_cash=_positive(raw.get("initial_cash", 100_000.0), "initial cash"),
            funding=bool(raw.get("funding", True)),
            annual_borrow_bps=annual_borrow_bps,
            missing_price_policy=missing_policy,
            transaction_costs=costs,
            constraints=constraints,
        )


@dataclass(frozen=True)
class EvaluationConfig:
    profile: str = "research"
    benchmark: str | None = None
    bootstrap_samples: int = 0
    regimes: bool = False

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> EvaluationConfig:
        profile = str(raw.get("profile", "research"))
        if profile not in {"smoke", "research", "publication"}:
            raise ConfigError("evaluation.profile must be smoke, research, or publication")
        samples = int(raw.get("bootstrap_samples", 0))
        if samples < 0:
            raise ConfigError("bootstrap_samples cannot be negative")
        benchmark = raw.get("benchmark")
        return cls(
            profile=profile,
            benchmark=str(benchmark) if benchmark is not None else None,
            bootstrap_samples=samples,
            regimes=bool(raw.get("regimes", False)),
        )


@dataclass(frozen=True)
class RunConfig:
    experiment: str
    data: DataConfig
    strategy: StrategyConfig
    execution: ExecutionConfig
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    artifacts_dir: str = "backtest-artifacts"
    notes: str = ""

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> RunConfig:
        if not raw.get("experiment"):
            raise ConfigError("experiment is required")
        return cls(
            experiment=str(raw["experiment"]),
            data=DataConfig.from_mapping(_mapping(raw.get("data"), "data")),
            strategy=StrategyConfig.from_mapping(_mapping(raw.get("strategy"), "strategy")),
            execution=ExecutionConfig.from_mapping(
                _mapping(raw.get("execution", {}), "execution")
            ),
            evaluation=EvaluationConfig.from_mapping(
                _mapping(raw.get("evaluation", {}), "evaluation")
            ),
            artifacts_dir=str(raw.get("artifacts_dir", "backtest-artifacts")),
            notes=str(raw.get("notes", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_config(path: str | Path) -> RunConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text())
    return RunConfig.from_mapping(_mapping(raw, "config"))
