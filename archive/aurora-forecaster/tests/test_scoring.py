import math

import pytest

from aurora_forecaster.scoring import (
    calibration_coverage,
    crps_gaussian,
    mase,
    skill_score,
)


def test_crps_gaussian_zero_sigma_degenerates_to_absolute_error():
    # As sigma -> 0, CRPS(N(mu, sigma), y) -> |y - mu| (point forecast).
    assert crps_gaussian(mu=10.0, sigma=1e-9, y=13.0) == pytest.approx(3.0, abs=1e-4)


def test_crps_gaussian_matches_known_closed_form_value():
    # CRPS(N(0,1), 0) = 2*phi(0) - 1/sqrt(pi), a standard reference value.
    expected = 2.0 / math.sqrt(2 * math.pi) - 1.0 / math.sqrt(math.pi)
    assert crps_gaussian(mu=0.0, sigma=1.0, y=0.0) == pytest.approx(expected, abs=1e-9)


def test_crps_gaussian_rejects_non_positive_sigma():
    with pytest.raises(ValueError):
        crps_gaussian(mu=0.0, sigma=0.0, y=1.0)
    with pytest.raises(ValueError):
        crps_gaussian(mu=0.0, sigma=-1.0, y=1.0)


def test_mase_scale_free_ratio():
    errors = [1.0, 2.0, 3.0]  # mean abs error = 2.0
    insample_naive_errors = [0.5, 1.5]  # mean abs error = 1.0
    assert mase(errors, insample_naive_errors) == pytest.approx(2.0)


def test_mase_rejects_zero_naive_scale():
    with pytest.raises(ValueError):
        mase([1.0], [0.0, 0.0])


def test_skill_score_positive_means_model_beats_naive():
    # model loss half the naive loss -> 0.5 skill
    assert skill_score(model_loss=1.0, naive_loss=2.0) == pytest.approx(0.5)


def test_skill_score_zero_when_equal_to_naive():
    assert skill_score(model_loss=2.0, naive_loss=2.0) == pytest.approx(0.0)


def test_skill_score_negative_when_worse_than_naive():
    assert skill_score(model_loss=4.0, naive_loss=2.0) == pytest.approx(-1.0)


def test_calibration_coverage_perfectly_calibrated_normal_samples():
    # Empirical coverage of a standard-normal PIT: at each nominal level p,
    # the central interval [-z, z] with z = Phi^-1((1+p)/2) should contain
    # exactly the z-scores we construct to sit just inside/outside it.
    # Use exact boundary z-scores for p=0.5 (z=0.6745) to check the coverage
    # counter includes points on/inside the boundary.
    z_scores = [0.0, 0.6, -0.6, 0.9, -0.9]
    coverage = calibration_coverage(z_scores, levels=(0.5,))
    # |z| <= 0.6745 for 0.0, 0.6, -0.6 -> 3/5 = 0.6
    assert coverage[0.5] == pytest.approx(0.6)


def test_calibration_coverage_multiple_levels_are_monotonic():
    z_scores = [0.0, 0.1, -0.1, 1.0, -1.0, 2.5, -2.5]
    coverage = calibration_coverage(z_scores, levels=(0.5, 0.8, 0.95))
    assert coverage[0.5] <= coverage[0.8] <= coverage[0.95]
