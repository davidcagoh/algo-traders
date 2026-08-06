import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "evaluation-framework"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))

from forward_accumulate import check_dsr_binding, check_kill_criteria, to_trial_record

DSR_BINDING_N_DAYS = 250


def test_dsr_not_binding_below_threshold():
    assert check_dsr_binding(n_days=249) is False


def test_dsr_binding_at_threshold():
    assert check_dsr_binding(n_days=DSR_BINDING_N_DAYS) is True


def test_dsr_binding_above_threshold():
    assert check_dsr_binding(n_days=400) is True


def _metrics(sharpe, calmar, mdd_pct, effective_assets, turnover):
    return {
        "sharpe": sharpe,
        "calmar": calmar,
        "max_drawdown_pct": mdd_pct,
        "avg_effective_assets": effective_assets,
        "avg_turnover_per_rebalance": turnover,
    }


def test_kill_criteria_passes_when_strictly_better_than_baseline():
    signed = _metrics(sharpe=2.0, calmar=1.5, mdd_pct=-10.0, effective_assets=5.0, turnover=0.5)
    baseline = _metrics(sharpe=1.0, calmar=1.0, mdd_pct=-20.0, effective_assets=3.0, turnover=0.5)

    result = check_kill_criteria(signed, baseline)

    assert result["killed"] is False
    assert result["reasons"] == []


def test_kill_criteria_triggers_on_sharpe_not_beating_baseline():
    signed = _metrics(sharpe=0.5, calmar=1.5, mdd_pct=-10.0, effective_assets=5.0, turnover=0.5)
    baseline = _metrics(sharpe=1.0, calmar=1.0, mdd_pct=-20.0, effective_assets=3.0, turnover=0.5)

    result = check_kill_criteria(signed, baseline)

    assert result["killed"] is True
    assert any("sharpe" in reason.lower() for reason in result["reasons"])


def test_kill_criteria_triggers_on_low_effective_assets():
    signed = _metrics(sharpe=2.0, calmar=1.5, mdd_pct=-10.0, effective_assets=2.5, turnover=0.5)
    baseline = _metrics(sharpe=1.0, calmar=1.0, mdd_pct=-20.0, effective_assets=3.0, turnover=0.5)

    result = check_kill_criteria(signed, baseline)

    assert result["killed"] is True
    assert any("effective assets" in reason.lower() for reason in result["reasons"])


def test_kill_criteria_triggers_on_excess_turnover():
    signed = _metrics(sharpe=2.0, calmar=1.5, mdd_pct=-10.0, effective_assets=5.0, turnover=1.3)
    baseline = _metrics(sharpe=1.0, calmar=1.0, mdd_pct=-20.0, effective_assets=3.0, turnover=0.5)

    result = check_kill_criteria(signed, baseline)

    assert result["killed"] is True
    assert any("turnover" in reason.lower() for reason in result["reasons"])


def test_to_trial_record_carries_kill_check_and_dsr_binding_in_notes():
    signed = _metrics(sharpe=2.0, calmar=1.5, mdd_pct=-10.0, effective_assets=5.0, turnover=0.5)
    kill_check = {"killed": False, "reasons": []}

    record = to_trial_record(
        metrics=signed,
        run_date="2026-08-06",
        n_days=47,
        dsr_binding=False,
        kill_check=kill_check,
    )

    assert record.project == "mean-variance-paper"
    assert record.evidence_stage == "paper"
    assert record.strategy == "shrunk_mean_variance_signed"
    assert record.gate_outcome == "pending"
    assert record.n_obs == 47
    assert "dsr_binding=False" in record.notes
    assert "killed=False" in record.notes


def test_to_trial_record_sets_gate_outcome_killed_when_kill_check_fires():
    signed = _metrics(sharpe=0.5, calmar=1.5, mdd_pct=-10.0, effective_assets=5.0, turnover=0.5)
    kill_check = {"killed": True, "reasons": ["sharpe does not beat baseline"]}

    record = to_trial_record(
        metrics=signed,
        run_date="2026-08-06",
        n_days=47,
        dsr_binding=False,
        kill_check=kill_check,
    )

    assert record.gate_outcome == "killed"
