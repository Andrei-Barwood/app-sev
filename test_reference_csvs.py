"""Regresión contra los CSV de referencia del curso (Evaluación 4 - Unidad 3)."""

from pathlib import Path

from core import calc_rho_a
from model_init import estimate_initial_model
from optimizer import run_optimization
from sev_feasibility import assess_feasibility
from sev_import import extract_reference_benchmark, parse_sev_file
from sev_metrics import ACCEPTANCE_ERROR_PCT, assess_fit

TESTS_DIR = Path(
    "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
    "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests"
)


def _optimize_file(name: str):
    path = TESTS_DIR / name
    result = parse_sev_file(str(path))
    init = estimate_initial_model(result.L_med, result.rho_med)
    best_rho, best_h, _, _ = run_optimization(
        result.L_med,
        result.rho_med,
        init.rho,
        init.h,
        [False] * init.n_layers,
        [False] * (init.n_layers - 1),
        use_global=True,
        try_alternate_layers=True,
    )
    calc = calc_rho_a(result.L_med, best_rho, best_h)
    fit = assess_fit(result.L_med, result.rho_med, calc)
    return result, fit, best_rho, best_h


def test_01_csv_matches_course_reference_mean_error():
    result, fit, _, _ = _optimize_file("01.csv")
    bench = extract_reference_benchmark(
        result.df, result.col_l, result.col_rho, result.L_med, result.rho_med
    )
    assert bench is not None
    assert abs(fit.mean_error_pct - bench["mean_error_pct"]) < 0.15
    assert fit.accepted
    assert fit.mean_error_pct <= ACCEPTANCE_ERROR_PCT + 0.05


def test_05_csv_rejected_and_feasibility_warns():
    result = parse_sev_file(str(TESTS_DIR / "05.csv"))
    feasibility = assess_feasibility(result.L_med, result.rho_med)
    _, fit, _, _ = _optimize_file("05.csv")
    assert not fit.accepted
    assert not feasibility.can_pass_mean
    assert fit.mean_error_pct > 50.0


def test_04_csv_detects_field_columns_not_calculated():
    result = parse_sev_file(str(TESTS_DIR / "04.csv"))
    assert result.col_l == "DISTANCIA_AB_2"
    assert result.col_rho == "R_Medidas"
    assert result.rho_med[0] == 339.0
    assert result.rho_med[-1] == 0.39


def test_02_and_03_are_same_reference_as_01():
    r1 = parse_sev_file(str(TESTS_DIR / "01.csv"))
    r2 = parse_sev_file(str(TESTS_DIR / "02.csv"))
    r3 = parse_sev_file(str(TESTS_DIR / "03.csv"))
    assert len(r1.L_med) == len(r2.L_med) == len(r3.L_med)
    assert (r1.rho_med == r2.rho_med).all()
    assert (r2.rho_med == r3.rho_med).all()