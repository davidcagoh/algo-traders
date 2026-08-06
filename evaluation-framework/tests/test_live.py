from __future__ import annotations

from evaluation.layers import compute
from evaluation.live import LiveRun, format_reconciliation_report, reconcile


def test_reconcile_incomplete_when_below_min_trades(gaussian_wallet):
    backtest = compute(gaussian_wallet)
    live = LiveRun(
        window_start="2026-05-21",
        window_end="2026-06-20",
        n_trades=2,
        min_trades_required=5,
        realized_return_pct=-0.09,
    )
    report = reconcile(backtest, live)
    assert report.verdict == "INCOMPLETE"
    assert any("incomplete" in r.lower() for r in report.reasons)


def test_reconcile_fail_on_net_loss(gaussian_wallet):
    backtest = compute(gaussian_wallet)
    live = LiveRun(
        window_start="2026-05-21",
        window_end="2026-08-05",
        n_trades=21,
        min_trades_required=5,
        realized_return_pct=-3.54,
    )
    report = reconcile(backtest, live)
    assert report.verdict == "FAIL"


def test_reconcile_fail_on_kill_threshold_breach(gaussian_wallet):
    backtest = compute(gaussian_wallet)
    live = LiveRun(
        window_start="2026-01-01",
        window_end="2026-02-01",
        n_trades=10,
        min_trades_required=5,
        realized_return_pct=0.5,  # positive, but kill threshold still breached
        max_consecutive_losses=7,
        kill_threshold_consecutive_losses=6,
    )
    report = reconcile(backtest, live)
    assert report.verdict == "FAIL"


def test_reconcile_pass_when_positive_and_no_breach(gaussian_wallet):
    backtest = compute(gaussian_wallet)
    live = LiveRun(
        window_start="2026-01-01",
        window_end="2026-02-01",
        n_trades=10,
        min_trades_required=5,
        realized_return_pct=2.0,
        max_consecutive_losses=2,
        kill_threshold_consecutive_losses=6,
    )
    report = reconcile(backtest, live)
    assert report.verdict == "PASS"


def test_reconcile_evidence_completeness_flags_missing_fields(gaussian_wallet):
    backtest = compute(gaussian_wallet)
    live = LiveRun(
        window_start="2026-01-01",
        window_end="2026-02-01",
        n_trades=10,
        min_trades_required=5,
        realized_return_pct=1.0,
    )
    report = reconcile(backtest, live)
    assert report.evidence_completeness["uptime_pct"] is False
    assert report.evidence_completeness["funding_paid"] is False


def test_reconcile_evidence_complete_when_all_fields_present(gaussian_wallet):
    backtest = compute(gaussian_wallet)
    live = LiveRun(
        window_start="2026-01-01",
        window_end="2026-02-01",
        n_trades=10,
        min_trades_required=5,
        realized_return_pct=1.0,
        uptime_pct=99.5,
        missed_signal_count=0,
        realized_slippage_bps=2.0,
        funding_paid=-1.5,
        exception_count=0,
    )
    report = reconcile(backtest, live)
    assert all(report.evidence_completeness.values())


def test_format_reconciliation_report_contains_verdict(gaussian_wallet):
    backtest = compute(gaussian_wallet)
    live = LiveRun(
        window_start="2026-01-01",
        window_end="2026-02-01",
        n_trades=2,
        min_trades_required=5,
        realized_return_pct=-0.5,
    )
    report = reconcile(backtest, live)
    text = format_reconciliation_report(report, label="test")
    assert "test" in text
    assert "INCOMPLETE" in text


# --- Regression fixture: the real HmmSmaSlopeV2 backtest-vs-live pair ---
# From `2026-08-05-hl-paper-evaluation.md`. This is the project's most
# expensive negative result — kept as a permanent regression test so the
# reconciliation logic can never silently regress into calling either
# window a PASS. Backtest values are representative bull-window figures
# from `_dsr_table.json` (HmmSmaSlopeV2 bull), not the live run's own
# backtest (which used a different window); what matters for this test is
# that the *live* evaluation lands on the documented verdicts.


def test_hmm_sma_slope_v2_original_30_day_gate_is_incomplete(gaussian_wallet):
    backtest = compute(gaussian_wallet)
    original_gate = LiveRun(
        window_start="2026-05-21",
        window_end="2026-06-20",
        n_trades=2,
        min_trades_required=5,
        realized_return_pct=-0.09,
        sharpe=-3.49,
        calmar=-12.13,
        mdd_pct=0.06,
        max_consecutive_losses=2,
        kill_threshold_consecutive_losses=6,
    )
    report = reconcile(backtest, original_gate)
    assert report.verdict == "INCOMPLETE"


def test_hmm_sma_slope_v2_extended_run_is_fail(gaussian_wallet):
    backtest = compute(gaussian_wallet)
    extended_run = LiveRun(
        window_start="2026-05-21",
        window_end="2026-08-05",
        n_trades=21,
        min_trades_required=5,
        realized_return_pct=-3.54,
        sharpe=-5.54,
        calmar=-4.49,
        mdd_pct=3.51,
        max_consecutive_losses=11,
        kill_threshold_consecutive_losses=6,
    )
    report = reconcile(backtest, extended_run)
    assert report.verdict == "FAIL"
    assert any("11 consecutive losses" in r for r in report.reasons)
