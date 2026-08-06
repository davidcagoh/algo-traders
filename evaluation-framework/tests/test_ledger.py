from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from evaluation.dsr import compute_dsr_from_ledger
from evaluation.ledger import (
    DuplicateTrialError,
    LedgerValidationError,
    TrialLedger,
    TrialRecord,
    effective_trials,
)


def _record(
    trial_id: str, status: str = "completed", sharpe: float = 0.5, **overrides
) -> TrialRecord:
    fields = {
        "trial_id": trial_id,
        "created_at": "2026-08-06T00:00:00Z",
        "family": "HmmSmaSlope",
        "strategy": "HmmSmaSlopeV2",
        "params": {"sma_period": 180, "hmm_states": 3},
        "dataset_id": "binance-bull-2023-2025",
        "split_id": "full",
        "status": status,
        "sharpe": sharpe,
        "n_obs": 300,
    }
    fields.update(overrides)
    return TrialRecord(**fields)


def test_param_hash_is_order_independent():
    a = TrialRecord(
        trial_id="a",
        created_at="t",
        family="f",
        strategy="s",
        params={"x": 1, "y": 2},
        dataset_id="d",
        split_id="s0",
        status="completed",
    )
    b = TrialRecord(
        trial_id="b",
        created_at="t",
        family="f",
        strategy="s",
        params={"y": 2, "x": 1},
        dataset_id="d",
        split_id="s0",
        status="completed",
    )
    assert a.param_hash == b.param_hash


def test_append_and_load_round_trip(tmp_path):
    ledger = TrialLedger(tmp_path / "trials.jsonl")
    ledger.append(_record("t1"))
    ledger.append(_record("t2", params={"sma_period": 200, "hmm_states": 3}))
    rows = ledger.load()
    assert len(rows) == 2
    assert {r.trial_id for r in rows} == {"t1", "t2"}


def test_append_rejects_duplicate(tmp_path):
    ledger = TrialLedger(tmp_path / "trials.jsonl")
    ledger.append(_record("t1"))
    with pytest.raises(DuplicateTrialError):
        ledger.append(_record("t1-again"))  # same params/dataset/split


def test_append_allows_same_params_for_different_strategy(tmp_path):
    """Two different strategies sharing identical params on the same
    dataset/split are distinct trials, not duplicates."""
    ledger = TrialLedger(tmp_path / "trials.jsonl")
    ledger.append(_record("t1", strategy="StrategyA"))
    ledger.append(_record("t2", strategy="StrategyB"))
    assert len(ledger.load()) == 2


def test_append_allows_rerun_when_flagged(tmp_path):
    ledger = TrialLedger(tmp_path / "trials.jsonl")
    ledger.append(_record("t1"))
    ledger.append(_record("t1-rerun"), allow_rerun=True)
    assert len(ledger.load()) == 2


def test_discarded_trials_count_toward_n_trials(tmp_path):
    ledger = TrialLedger(tmp_path / "trials.jsonl")
    ledger.append(_record("t1", status="completed"))
    ledger.append(_record("t2", status="discarded", params={"sma_period": 999, "hmm_states": 3}))
    assert ledger.n_trials() == 2


def test_scope_filters_by_family_and_dataset(tmp_path):
    ledger = TrialLedger(tmp_path / "trials.jsonl")
    ledger.append(_record("t1", family="A", dataset_id="d1"))
    ledger.append(
        _record("t2", family="B", dataset_id="d1", params={"sma_period": 1, "hmm_states": 3})
    )
    assert ledger.n_trials(family="A") == 1
    assert ledger.n_trials(dataset_id="d1") == 2


def test_validate_flags_missing_fields(tmp_path):
    path = tmp_path / "trials.jsonl"
    path.write_text('{"trial_id": "t1"}\n')
    ledger = TrialLedger(path)
    problems = ledger.validate()
    assert any("missing fields" in p for p in problems)


def test_validate_reports_corrupt_line(tmp_path):
    path = tmp_path / "trials.jsonl"
    path.write_text("not json\n")
    ledger = TrialLedger(path)
    with pytest.raises(LedgerValidationError):
        ledger.validate()


def test_to_frame_empty_ledger(tmp_path):
    ledger = TrialLedger(tmp_path / "trials.jsonl")
    frame = ledger.to_frame()
    assert frame.empty


def test_sharpe_variance_matches_manual(tmp_path):
    ledger = TrialLedger(tmp_path / "trials.jsonl")
    ledger.append(_record("t1", sharpe=0.5))
    ledger.append(_record("t2", sharpe=1.5, params={"sma_period": 1, "hmm_states": 3}))
    expected = float(np.var([0.5, 1.5], ddof=1))
    assert ledger.sharpe_variance() == pytest.approx(expected)


def test_effective_trials_clusters_near_duplicates(rng):
    base = rng.normal(0.001, 0.02, 300)
    noise = rng.normal(0, 0.0005, 300)
    df = pd.DataFrame(
        {
            "v1": base,
            "v2": base + noise,  # near-duplicate of v1
            "v3": rng.normal(0.001, 0.02, 300),  # independent
        }
    )
    raw_n, eff_n = effective_trials(df, threshold=0.9)
    assert raw_n == 3
    assert eff_n < raw_n


def test_effective_trials_all_independent_equals_raw(rng):
    df = pd.DataFrame({f"t{i}": rng.normal(0, 0.02, 300) for i in range(5)})
    raw_n, eff_n = effective_trials(df, threshold=0.9)
    assert eff_n == raw_n


def test_compute_dsr_from_ledger_uses_ledger_n_trials(tmp_path, gaussian_wallet, trending_wallet):
    ledger = TrialLedger(tmp_path / "trials.jsonl")
    for i in range(40):
        ledger.append(_record(f"t{i}", params={"sma_period": i, "hmm_states": 3}))

    wallets = {"a": gaussian_wallet, "b": trending_wallet}
    rows = compute_dsr_from_ledger(wallets, ledger)
    assert len(rows) == 2
    # SR* should reflect n_trials=40, not len(wallets)=2 — cross-check
    from evaluation.dsr import compute_dsr_table

    rows_explicit = compute_dsr_table(wallets, n_trials=40)
    assert rows[0].sharpe_star == pytest.approx(rows_explicit[0].sharpe_star)


def test_compute_dsr_from_ledger_uses_ledger_sharpe_variance(
    tmp_path, gaussian_wallet, trending_wallet
):
    """Regression: a wide-search ledger's recorded Sharpes (not the narrow
    `wallets` passed in) should drive sharpe_var when they carry real
    variance — this is what fixes the narrow-family DSR-inflation bug."""
    ledger = TrialLedger(tmp_path / "trials.jsonl")
    diverse_sharpes = [0.1, 0.5, 1.0, 1.5, 2.0, -0.5, -1.0, 0.8, 1.2, 0.3]
    for i, sh in enumerate(diverse_sharpes):
        ledger.append(_record(f"t{i}", sharpe=sh, params={"sma_period": i, "hmm_states": 3}))

    wallets = {"a": gaussian_wallet, "b": trending_wallet}  # narrow, similar Sharpes
    from_ledger_var = compute_dsr_from_ledger(wallets, ledger)

    from evaluation.dsr import compute_dsr_table

    wallet_only = compute_dsr_table(wallets, n_trials=len(diverse_sharpes))
    # ledger's diverse Sharpes have much higher variance than the two
    # near-identical wallets, so SR* (and thus DSR) should differ.
    assert from_ledger_var[0].sharpe_star != pytest.approx(wallet_only[0].sharpe_star)
