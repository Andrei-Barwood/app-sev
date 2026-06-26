import numpy as np

from model_init import estimate_initial_model
from optimizer import run_optimization
from sev_import import parse_sev_file


def test_model_init_04_csv_detects_descending_curve():
    result = parse_sev_file(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/04.csv"
    )
    init = estimate_initial_model(result.L_med, result.rho_med)
    assert init.curve_type in {"Q", "DESC2"}
    assert init.n_layers in {2, 3}
    assert len(init.rho) == init.n_layers
    assert len(init.h) == init.n_layers - 1
    assert init.rho[0] > init.rho[-1]


def test_model_init_01_csv_and_optimization_improves():
    result = parse_sev_file(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/01.csv"
    )
    init = estimate_initial_model(result.L_med, result.rho_med)
    assert init.curve_type in {"K", "A", "H", "Q"}
    best_rho, best_h, rmse, r2 = run_optimization(
        result.L_med,
        result.rho_med,
        init.rho,
        init.h,
        [False] * init.n_layers,
        [False] * (init.n_layers - 1),
        use_global=True,
    )
    assert r2 > 0.8
    assert rmse < 80.0
    assert np.all(np.asarray(best_rho) > 0)
    assert np.all(np.asarray(best_h) > 0)