from sev_import import parse_sev_file
from sev_schlumberger import schlumberger_k_factor, build_schlumberger_verification_table


def test_schlumberger_k_reading_1():
    k = schlumberger_k_factor(0.6, 1.0)
    assert abs(k * 339.0 - 117.15) < 0.05


def test_verification_table_04_csv():
    result = parse_sev_file(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/04.csv"
    )
    table = build_schlumberger_verification_table(
        result.df,
        result.col_l,
        col_r="R_Medidas",
        col_rho="Ro_Calculados",
        col_mn="d",
    )
    assert len(table) == 17
    assert abs(table["ρ_a calculada [Ω·m]"].iloc[0] - 117.15) < 0.1