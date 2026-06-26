import numpy as np

from sev_metrics import ACCEPTANCE_ERROR_PCT, assess_fit, log_axis_ticks


def test_log_axis_ticks_are_sorted_and_within_range():
    ticks = log_axis_ticks(np.array([0.6, 1.0, 12.0]))
    assert ticks == sorted(ticks)
    assert min(ticks) <= 0.6
    assert max(ticks) >= 12.0
    assert len(ticks) <= 12


def test_assess_fit_accepts_good_curve():
    rho_med = np.array([100.0, 110.0, 105.0])
    rho_calc = np.array([102.0, 108.0, 104.0])
    report = assess_fit(np.array([1.0, 2.0, 3.0]), rho_med, rho_calc)
    assert report.accepted
    assert report.strict_accepted
    assert report.mean_error_pct <= ACCEPTANCE_ERROR_PCT


def test_assess_fit_rejects_poor_curve():
    rho_med = np.array([339.0, 10.0, 0.39])
    rho_calc = np.array([70.0, 8.0, 3.5])
    report = assess_fit(np.array([0.6, 3.0, 12.0]), rho_med, rho_calc)
    assert not report.accepted
    assert report.n_over_threshold >= 2
    assert report.max_error_pct > ACCEPTANCE_ERROR_PCT