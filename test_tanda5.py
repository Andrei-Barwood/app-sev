"""Regresión tanda 5: modo estricto, referencia CSV y auto-capas."""

from pathlib import Path

import numpy as np

from model_init import resolve_initial_model
from optimizer import run_optimization
from sev_import import extract_reference_benchmark, parse_sev_file
from sev_metrics import ACCEPTANCE_ERROR_PCT, assess_fit, linear_error_pct
from core import calc_rho_a

TESTS_DIR = Path(
    "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
    "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests"
)


def test_04_csv_auto_expands_to_four_layers():
    result = parse_sev_file(str(TESTS_DIR / "04.csv"))
    init = resolve_initial_model(result.L_med, result.rho_med)
    assert init.n_layers >= 4


def test_01_csv_reference_curve_aligns_to_measurements():
    result = parse_sev_file(str(TESTS_DIR / "01.csv"))
    bench = extract_reference_benchmark(
        result.df, result.col_l, result.col_rho, result.L_med, result.rho_med
    )
    assert bench is not None
    aligned = bench["rho_calc_aligned"]
    assert len(aligned) == len(result.L_med)
    assert np.all(np.isfinite(aligned))
    assert aligned[0] > 0


def test_04_csv_has_ro_calculados_for_plot():
    result = parse_sev_file(str(TESTS_DIR / "04.csv"))
    bench = extract_reference_benchmark(
        result.df, result.col_l, result.col_rho, result.L_med, result.rho_med
    )
    assert bench is not None
    assert "Ro_Calculados" in bench["col_calc"] or "calculado" in bench["col_calc"].lower()
    assert np.sum(np.isfinite(bench["rho_calc_aligned"])) == len(result.L_med)


def test_strict_mode_reduces_points_over_threshold_on_01():
    result = parse_sev_file(str(TESTS_DIR / "01.csv"))
    init = resolve_initial_model(result.L_med, result.rho_med)

    best_std_rho, best_std_h, _, _ = run_optimization(
        result.L_med,
        result.rho_med,
        init.rho,
        init.h,
        [False] * init.n_layers,
        [False] * (init.n_layers - 1),
        use_global=True,
        try_alternate_layers=True,
        strict_mode=False,
    )
    calc_std = calc_rho_a(result.L_med, best_std_rho, best_std_h)
    over_std = int(np.sum(linear_error_pct(result.rho_med, calc_std) > ACCEPTANCE_ERROR_PCT))

    best_strict_rho, best_strict_h, _, _ = run_optimization(
        result.L_med,
        result.rho_med,
        init.rho,
        init.h,
        [False] * init.n_layers,
        [False] * (init.n_layers - 1),
        use_global=True,
        try_alternate_layers=True,
        strict_mode=True,
    )
    calc_strict = calc_rho_a(result.L_med, best_strict_rho, best_strict_h)
    over_strict = int(np.sum(linear_error_pct(result.rho_med, calc_strict) > ACCEPTANCE_ERROR_PCT))

    fit_std = assess_fit(result.L_med, result.rho_med, calc_std)
    fit_strict = assess_fit(result.L_med, result.rho_med, calc_strict)
    assert over_strict <= over_std
    assert fit_strict.max_error_pct <= fit_std.max_error_pct + 0.05
    assert fit_strict.mean_error_pct <= ACCEPTANCE_ERROR_PCT + 0.1