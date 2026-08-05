"""Six-layer evaluation stack — cross-venue port.

Ported from `feishu/eval/`. Adapted for use across SGX equities, IDX
equities, and Hyperliquid perps by removing feishu-specific constants
(242-day annualisation, competition-score field) and parameterising
annualisation per-venue.

See `../wiki/_index.md` and `../wiki/concepts/cv-and-deflation.md` for the
framing.
"""

from evaluation.layers import (
    ASHARES_ANNUAL,
    SGX_ANNUAL,
    IDX_ANNUAL,
    HSI_ANNUAL,
    FTSE_ANNUAL,
    CRYPTO_ANNUAL,
    LayeredMetrics,
    compute,
    format_markdown_table,
)
from evaluation.dsr import (
    DSRStats,
    compute_dsr_table,
    deflated_sharpe,
    expected_max_sharpe,
    format_dsr_table,
    is_dsr_binding,
)
from evaluation.correlation_mdb import (
    correlation_matrix,
    marginal_diversification_benefit,
    mdb_robust_flag,
    mdb_table,
    returns_matrix,
)
from evaluation.backtest import (
    build_returns_matrix,
    load_daily_returns,
    load_trade_returns,
    load_wallet_curve,
)

__all__ = [
    "ASHARES_ANNUAL",
    "SGX_ANNUAL",
    "IDX_ANNUAL",
    "HSI_ANNUAL",
    "FTSE_ANNUAL",
    "CRYPTO_ANNUAL",
    "LayeredMetrics",
    "compute",
    "format_markdown_table",
    "DSRStats",
    "compute_dsr_table",
    "deflated_sharpe",
    "expected_max_sharpe",
    "format_dsr_table",
    "is_dsr_binding",
    "correlation_matrix",
    "marginal_diversification_benefit",
    "mdb_robust_flag",
    "mdb_table",
    "returns_matrix",
    "build_returns_matrix",
    "load_daily_returns",
    "load_trade_returns",
    "load_wallet_curve",
]
