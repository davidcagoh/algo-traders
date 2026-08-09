
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


def test_diebold_mariano_result_reports_max_lag():
    loss_a = [1.0, 1.1, 0.9, 1.0, 0.95, 1.05, 1.0, 0.9, 1.1, 1.0]
    loss_b = [2.0, 2.1, 1.9, 2.0, 1.95, 2.05, 2.0, 1.9, 2.1, 2.0]

    result = diebold_mariano(loss_a, loss_b, max_lag=3)

    assert result.max_lag == 3


def test_diebold_mariano_default_max_lag_uses_automatic_bandwidth():
    # Newey-West (1994) plug-in: floor(4 * (n/100)**(2/9)); for n=25 this is 2.
    loss_a = [float(i % 3) for i in range(25)]
    loss_b = [float((i + 1) % 3) for i in range(25)]

    result = diebold_mariano(loss_a, loss_b)

    assert result.max_lag == 2


def test_diebold_mariano_max_lag_clipped_to_n_minus_1():
    loss_a = [1.0, 2.0, 3.0]
    loss_b = [1.5, 1.5, 1.5]

    result = diebold_mariano(loss_a, loss_b, max_lag=100)

    assert result.max_lag == 2


def test_diebold_mariano_rejects_negative_max_lag():
    with pytest.raises(ValueError):
        diebold_mariano([1.0, 2.0], [1.5, 1.5], max_lag=-1)


def test_diebold_mariano_hac_widens_interval_under_positive_serial_correlation():
    # Deterministic block pattern: d_t = loss_a_t - loss_b_t is +0.3 for the
    # first 8 origins, then -0.9 for the next 8 -- strong positive lag-1
    # autocorrelation within each block. Sample mean is meaningfully
    # negative (loss_a looks better on average), and the plain/short-lag
    # estimator (max_lag=0, treats each d_t as independent) calls this
    # significant. The full-sample HAC estimator (max_lag=n-1=15) correctly
    # inflates the variance to reflect the block persistence and the same
    # data is no longer significant -- this is the fix actually doing
    # something, not just failing to break existing behavior.
    loss_b = [1.0] * 16
    loss_a = [1.3] * 8 + [0.1] * 8

    short = diebold_mariano(loss_a, loss_b, max_lag=0)
    hac = diebold_mariano(loss_a, loss_b, max_lag=15)

    assert short.p_value < 0.05
    assert hac.p_value > 0.05
