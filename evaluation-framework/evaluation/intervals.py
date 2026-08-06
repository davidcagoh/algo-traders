"""Bootstrap-interval convenience wrapper around `evaluation.layers.compute`.

Point estimates alone (the existing `LayeredMetrics`/`format_markdown_table`)
invite over-reading small differences between candidates as real. This
module makes an interval the default rendering rather than an opt-in extra
call — see `bootstrap.py` for the underlying method citations.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from evaluation.bootstrap import BootstrapCI, bootstrap_ci
from evaluation.layers import (
    DEFAULT_ANNUAL,
    LayeredMetrics,
    cagr,
    calmar,
    compute,
    sharpe,
)

_METRIC_FUNCS = {
    "sharpe": lambda w, ann: sharpe(w, ann),
    "cagr_pct": lambda w, ann: cagr(w, ann) * 100.0,
    "calmar": lambda w, ann: calmar(w, ann),
}


def metrics_with_ci(
    wallet: pd.Series,
    trade_returns: pd.Series | None = None,
    annualisation: float = DEFAULT_ANNUAL,
    n_boot: int = 10_000,
    method: str = "stationary",
    alpha: float = 0.05,
    seed: int | None = None,
) -> tuple[LayeredMetrics, dict[str, BootstrapCI]]:
    """`compute()` plus a block-bootstrap CI for Sharpe, CAGR, and Calmar."""
    metrics = compute(wallet, trade_returns, annualisation)
    # Simple (not log) returns, matching what sharpe()/cagr()/calmar() use
    # internally, so bootstrapped statistics reproduce the same point estimate.
    r = wallet.pct_change().dropna()

    cis: dict[str, BootstrapCI] = {}
    for name in ("sharpe", "cagr_pct", "calmar"):

        def stat(x: np.ndarray, _name: str = name) -> float:
            s = pd.Series(x)
            w = 100.0 * np.concatenate([[1.0], np.cumprod(1.0 + s.to_numpy())])
            wallet_like = pd.Series(w)
            return _METRIC_FUNCS[_name](wallet_like, annualisation)

        cis[name] = bootstrap_ci(
            r, statistic=stat, n_boot=n_boot, method=method, alpha=alpha, seed=seed
        )
    return metrics, cis


def format_markdown_table_with_ci(
    m: LayeredMetrics, cis: dict[str, BootstrapCI], title: str = ""
) -> str:
    from evaluation.layers import format_markdown_table

    base = format_markdown_table(m, title)
    pct = int((1 - cis["sharpe"].alpha) * 100)
    header = (
        f"_{pct}% block-bootstrap CIs "
        f"({cis['sharpe'].method}, block={cis['sharpe'].block_len}, "
        f"n_boot={cis['sharpe'].n_boot}):_"
    )
    lines = [base, "", header]
    for name, label in (("sharpe", "Sharpe"), ("cagr_pct", "CAGR%"), ("calmar", "Calmar")):
        ci = cis[name]
        lines.append(f"- {label}: {ci.point:.3f} [{ci.lower:.3f}, {ci.upper:.3f}]")
    return "\n".join(lines)
