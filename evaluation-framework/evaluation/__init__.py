"""Six-layer evaluation stack — cross-venue port.

Ported from `feishu/eval/`. Adapted for use across SGX equities, IDX
equities, and Hyperliquid perps by removing feishu-specific constants
(242-day annualisation, competition-score field) and parameterising
annualisation per-venue.

Every module here traces to a source in
`../literature/strategy-evaluation/_index.md` — see each module's docstring
for the specific citation. See `../wiki/_index.md` and
`../wiki/concepts/cv-and-deflation.md` for the framing, and `PLAN.md` for
the build-out this package follows.
"""

from evaluation.backtest import (
    build_returns_matrix,
    load_daily_returns,
    load_trade_returns,
    load_wallet_curve,
)
from evaluation.benchmark import (
    ExcessMetrics,
    buy_and_hold,
    excess_metrics,
    format_benchmark_table,
    peer_benchmark,
)
from evaluation.bootstrap import (
    BootstrapCI,
    bootstrap_ci,
    circular_block_bootstrap,
    moving_block_bootstrap,
    optimal_block_length,
    paired_bootstrap_test,
    stationary_bootstrap,
)
from evaluation.correlation_mdb import (
    correlation_matrix,
    equal_weights,
    marginal_diversification_benefit,
    mdb_robust_flag,
    mdb_table,
    mean_variance_weights,
    portfolio_returns,
    returns_matrix,
    risk_parity_weights,
)
from evaluation.costs import (
    CostModel,
    apply_costs,
    breakeven_cost,
    cost_drag_summary,
    cost_grid,
    turnover,
)
from evaluation.dsr import (
    DSRStats,
    compute_dsr_from_ledger,
    compute_dsr_table,
    deflated_sharpe,
    expected_max_sharpe,
    format_dsr_table,
    is_dsr_binding,
)
from evaluation.factors import (
    FactorResult,
    crypto_factors,
    factor_regression,
    format_factor_table,
)
from evaluation.holdout import HoldoutViolation, break_seal, guard, seal_holdout
from evaluation.intervals import format_markdown_table_with_ci, metrics_with_ci
from evaluation.layers import (
    ASHARES_ANNUAL,
    CRYPTO_ANNUAL,
    FTSE_ANNUAL,
    HSI_ANNUAL,
    IDX_ANNUAL,
    SGX_ANNUAL,
    LayeredMetrics,
    compute,
    format_markdown_table,
)
from evaluation.ledger import (
    DuplicateTrialError,
    LedgerValidationError,
    TrialLedger,
    TrialRecord,
    effective_trials,
)
from evaluation.live import (
    LiveRun,
    ReconciliationReport,
    format_reconciliation_report,
    reconcile,
)
from evaluation.pbo import PBOResult, cscv_pbo, format_pbo_table
from evaluation.regimes import label_regimes, regime_metrics, regime_stability
from evaluation.spa import SPAResult, format_spa_table, spa_test
from evaluation.splits import (
    DoubleOOSSplit,
    FoldSpec,
    PurgedKFold,
    PurgedWalkForward,
    combinatorial_purged_splits,
)
from evaluation.stress import (
    SlippageAtRisk,
    capacity_curve,
    depth_from_ohlcv,
    flash_crash_scenario,
    slippage_at_risk,
)

__all__ = [
    "ASHARES_ANNUAL",
    "CRYPTO_ANNUAL",
    "FTSE_ANNUAL",
    "HSI_ANNUAL",
    "IDX_ANNUAL",
    "SGX_ANNUAL",
    "BootstrapCI",
    "CostModel",
    "DSRStats",
    "DoubleOOSSplit",
    "DuplicateTrialError",
    "ExcessMetrics",
    "FactorResult",
    "FoldSpec",
    "HoldoutViolation",
    "LayeredMetrics",
    "LedgerValidationError",
    "LiveRun",
    "PBOResult",
    "PurgedKFold",
    "PurgedWalkForward",
    "ReconciliationReport",
    "SPAResult",
    "SlippageAtRisk",
    "TrialLedger",
    "TrialRecord",
    "apply_costs",
    "bootstrap_ci",
    "break_seal",
    "breakeven_cost",
    "build_returns_matrix",
    "buy_and_hold",
    "capacity_curve",
    "circular_block_bootstrap",
    "combinatorial_purged_splits",
    "compute",
    "compute_dsr_from_ledger",
    "compute_dsr_table",
    "correlation_matrix",
    "cost_drag_summary",
    "cost_grid",
    "crypto_factors",
    "cscv_pbo",
    "deflated_sharpe",
    "depth_from_ohlcv",
    "effective_trials",
    "equal_weights",
    "excess_metrics",
    "expected_max_sharpe",
    "factor_regression",
    "flash_crash_scenario",
    "format_benchmark_table",
    "format_dsr_table",
    "format_factor_table",
    "format_markdown_table",
    "format_markdown_table_with_ci",
    "format_pbo_table",
    "format_reconciliation_report",
    "format_spa_table",
    "guard",
    "is_dsr_binding",
    "label_regimes",
    "load_daily_returns",
    "load_trade_returns",
    "load_wallet_curve",
    "marginal_diversification_benefit",
    "mdb_robust_flag",
    "mdb_table",
    "mean_variance_weights",
    "metrics_with_ci",
    "moving_block_bootstrap",
    "optimal_block_length",
    "paired_bootstrap_test",
    "peer_benchmark",
    "portfolio_returns",
    "reconcile",
    "regime_metrics",
    "regime_stability",
    "returns_matrix",
    "risk_parity_weights",
    "seal_holdout",
    "slippage_at_risk",
    "spa_test",
    "stationary_bootstrap",
    "turnover",
]
