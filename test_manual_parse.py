import pandas as pd

from sev_import import parse_manual_sev_text


def test_manual_two_columns_matches_05():
    text = "0.6, 339\n1, 123.1\n12, 0.39"
    result = parse_manual_sev_text(text)
    assert result.n_lines_parsed == 3
    assert result.L_med[0] == 0.6
    assert result.rho_med[0] == 339.0
    assert result.rho_med[-1] == 0.39


def test_manual_telurimetro_rows_not_zigzag():
    df = pd.read_csv(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/04.csv"
    )
    lines = [
        ",".join(str(int(v) if float(v).is_integer() else v) for v in row)
        for row in df.values
    ]
    result = parse_manual_sev_text("\n".join(lines))
    assert result.n_lines_parsed == 17
    assert result.format_detected == "telurómetro_multicolumna_rho_a"
    assert result.L_med[0] == 0.6
    assert result.rho_med[0] == 117.15
    assert result.rho_med[-1] == 176.13
    assert float(result.rho_med.max()) > float(result.rho_med.min())


def test_manual_wrong_two_cols_warns():
    df = pd.read_csv(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/04.csv"
    )
    wrong_lines = [f"{int(row[0])},{row[1]}" for row in df.values]
    result = parse_manual_sev_text("\n".join(wrong_lines))
    assert any("lectura" in w.lower() or "abrupt" in w.lower() or "saltos" in w.lower() for w in result.warnings)