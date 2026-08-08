import pytest

from aurora_forecaster.compare import diebold_mariano


def test_diebold_mariano_identical_losses_gives_zero_statistic():
    loss_a = [1.0, 2.0, 3.0, 2.5, 1.5]
    loss_b = [1.0, 2.0, 3.0, 2.5, 1.5]

    result = diebold_mariano(loss_a, loss_b)

    assert result.statistic == pytest.approx(0.0, abs=1e-9)
    assert result.p_value == pytest.approx(1.0, abs=1e-9)


def test_diebold_mariano_detects_consistently_better_series():
    # loss_a is always strictly lower than loss_b -> large negative statistic,
    # small p-value.
    loss_a = [1.0, 1.1, 0.9, 1.0, 0.95, 1.05, 1.0, 0.9, 1.1, 1.0]
    loss_b = [2.0, 2.1, 1.9, 2.0, 1.95, 2.05, 2.0, 1.9, 2.1, 2.0]

    result = diebold_mariano(loss_a, loss_b)

    assert result.statistic < 0
    assert result.p_value < 0.05


def test_diebold_mariano_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        diebold_mariano([1.0, 2.0], [1.0])


def test_diebold_mariano_rejects_too_few_observations():
    with pytest.raises(ValueError):
        diebold_mariano([1.0], [1.0])
