"""Backtest-to-live reconciliation with a three-valued verdict.

Literature: Liu 2026, *Evaluating Structured Strategy Backtests*
(`../literature/strategy-evaluation/empirical-audits/2604.18821-backtest-regime-live-performance.pdf`,
1,726 commercial strategies) — measures pro-forma-to-live decay relative to
peer/external benchmarks, conditioned on launch regime. Jadouli 2026
(`../literature/strategy-evaluation/empirical-audits/2607.19453-negative-results-evidence-audit.pdf`)
— reconcile with the same evidence schema and retain negative outcomes.

`LiveRun` is deliberately a superset of what a real run can usually
produce, so missing fields are visible rather than silently absent — see
`2026-08-05-hl-paper-evaluation.md`
(`../freqtrade-experiment/hmm-slope-experiment/execution/records/results/`):
uptime, same-OHLC signal fidelity, slippage, funding impact, and exception
audit "cannot be reconstructed from the retained trade mirror. Their
absence prevents a retrospective gate pass" — exactly the distinction
`Verdict.INCOMPLETE` exists to encode, separately from `Verdict.FAIL`.
That run's pre-registered 30-day gate required 5 round trips and got 2:
"the original gate is incomplete, not a pass" — not the same thing as the
extended run's clear failure (21 trades, -3.54%, 11-loss streak). Treating
both as one undifferentiated "not a pass" outcome loses that distinction;
this module keeps it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from evaluation.layers import LayeredMetrics

Verdict = Literal["PASS", "FAIL", "INCOMPLETE"]


@dataclass(frozen=True)
class LiveRun:
    window_start: str
    window_end: str
    n_trades: int
    min_trades_required: int
    realized_return_pct: float
    sharpe: float | None = None
    calmar: float | None = None
    mdd_pct: float | None = None
    max_consecutive_losses: int | None = None
    kill_threshold_consecutive_losses: int | None = None
    uptime_pct: float | None = None
    missed_signal_count: int | None = None
    realized_slippage_bps: float | None = None
    funding_paid: float | None = None
    exception_count: int | None = None
    regime_label: str | None = None


@dataclass(frozen=True)
class ReconciliationReport:
    verdict: Verdict
    reasons: list[str]
    sharpe_decay_ratio: float | None
    evidence_completeness: dict[str, bool]


_OPTIONAL_EVIDENCE_FIELDS = (
    "uptime_pct",
    "missed_signal_count",
    "realized_slippage_bps",
    "funding_paid",
    "exception_count",
)


def reconcile(backtest: LayeredMetrics, live: LiveRun) -> ReconciliationReport:
    """Compare a live run against its backtest and return a PASS/FAIL/
    INCOMPLETE verdict plus reasons and an evidence-completeness map.

    INCOMPLETE fires when the pre-registered minimum trade count was not
    reached — the run is not evidence of failure, just insufficient
    evidence. FAIL requires enough trades to be a real read: a net loss, or
    hitting the pre-registered consecutive-loss kill threshold. PASS
    requires enough trades, positive realized return, and no kill-threshold
    breach.
    """
    evidence_completeness = {
        field: getattr(live, field) is not None for field in _OPTIONAL_EVIDENCE_FIELDS
    }

    reasons: list[str] = []

    if live.n_trades < live.min_trades_required:
        reasons.append(
            f"{live.n_trades} closed trades < pre-registered minimum "
            f"{live.min_trades_required} — gate is incomplete, not a pass"
        )
        return ReconciliationReport(
            verdict="INCOMPLETE",
            reasons=reasons,
            sharpe_decay_ratio=None,
            evidence_completeness=evidence_completeness,
        )

    kill_breach = (
        live.max_consecutive_losses is not None
        and live.kill_threshold_consecutive_losses is not None
        and live.max_consecutive_losses >= live.kill_threshold_consecutive_losses
    )
    if kill_breach:
        reasons.append(
            f"{live.max_consecutive_losses} consecutive losses >= kill threshold "
            f"{live.kill_threshold_consecutive_losses}"
        )

    net_loss = live.realized_return_pct < 0
    if net_loss:
        reasons.append(f"realized return {live.realized_return_pct:+.2f}% is negative")

    sharpe_decay_ratio = None
    if (
        live.sharpe is not None
        and backtest.sharpe not in (0, None)
        and backtest.sharpe == backtest.sharpe
    ):
        sharpe_decay_ratio = live.sharpe / backtest.sharpe
        if sharpe_decay_ratio < 0:
            reasons.append(
                f"live Sharpe {live.sharpe:.2f} has opposite sign from backtest "
                f"Sharpe {backtest.sharpe:.2f} (decay ratio {sharpe_decay_ratio:.2f})"
            )

    incomplete_evidence = [f for f, present in evidence_completeness.items() if not present]
    if incomplete_evidence:
        reasons.append(
            f"missing evidence fields: {', '.join(incomplete_evidence)} — "
            "verdict below is based on what's available, not a full audit"
        )

    verdict: Verdict = "FAIL" if (kill_breach or net_loss) else "PASS"
    return ReconciliationReport(
        verdict=verdict,
        reasons=reasons,
        sharpe_decay_ratio=sharpe_decay_ratio,
        evidence_completeness=evidence_completeness,
    )


def format_reconciliation_report(report: ReconciliationReport, label: str = "") -> str:
    title = f" — {label}" if label else ""
    lines = [
        f"### Backtest-to-live reconciliation{title}",
        "",
        f"**Verdict: {report.verdict}**",
        "",
    ]
    if report.sharpe_decay_ratio is not None:
        lines.append(f"Sharpe decay ratio (live/backtest): {report.sharpe_decay_ratio:.3f}")
    lines.append("")
    lines.append("Reasons:")
    for r in report.reasons:
        lines.append(f"- {r}")
    lines.append("")
    lines.append("Evidence completeness:")
    for field, present in report.evidence_completeness.items():
        lines.append(f"- {field}: {'present' if present else 'MISSING'}")
    return "\n".join(lines)
