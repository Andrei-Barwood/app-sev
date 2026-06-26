from sev_import import parse_sev_file
from sev_feasibility import assess_feasibility


def test_feasibility_05_csv_is_unlikely_to_pass():
    result = parse_sev_file(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/05.csv"
    )
    report = assess_feasibility(result.L_med, result.rho_med)
    assert report.estimated_min_mean_pct > 20.0
    assert not report.can_pass_mean
    assert report.level in {"error", "warning"}


def test_feasibility_01_csv_is_viable():
    result = parse_sev_file(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/01.csv"
    )
    report = assess_feasibility(result.L_med, result.rho_med)
    assert report.estimated_min_mean_pct < 8.0
    assert report.can_pass_mean
    assert report.level == "success"