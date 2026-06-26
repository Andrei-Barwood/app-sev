import pandas as pd

from sev_import import (
    assess_column_selection,
    detect_l_rho_columns,
    load_dataframe_from_upload,
    parse_sev_file,
    refresh_stored_csv_dataset,
)


def test_detect_columns_for_04_csv():
    result = parse_sev_file(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/04.csv"
    )
    assert result.col_l == "DISTANCIA_AB_2"
    assert result.col_rho == "Ro_Calculados"
    assert len(result.L_med) == 17
    assert result.L_med[0] == 0.6
    assert result.rho_med[0] == 117.15
    assert result.L_med[-1] == 12.0
    assert result.detection_method == "encabezado"


def test_detect_columns_for_app_export_csv():
    result = parse_sev_file(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/01.csv"
    )
    assert result.col_l.startswith("L (AB/2)")
    assert "Rho Medido" in result.col_rho
    assert len(result.L_med) == 19


def test_detect_from_dataframe_04():
    with open(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/04.csv",
        "rb",
    ) as fh:
        df = load_dataframe_from_upload(fh, "04.csv")
    col_l, col_rho, method, _ = detect_l_rho_columns(df)
    assert col_l == "DISTANCIA_AB_2"
    assert col_rho == "Ro_Calculados"
    assert method == "encabezado"


def test_assess_wrong_columns_for_04_csv():
    result = parse_sev_file(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/04.csv",
        col_l="N_Lectura",
        col_rho="DISTANCIA_AB_2",
    )
    notes = assess_column_selection(
        result.col_l,
        result.col_rho,
        result.L_med,
        result.rho_med,
        result.suggested_col_l,
        result.suggested_col_rho,
    )
    levels = {note.level for note in notes}
    assert "error" in levels


def test_refresh_stored_csv_fixes_r_medidas_to_ro_calculados():
    result = parse_sev_file(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/04.csv"
    )
    stale_panel = {
        "df": result.df,
        "col_l": result.col_l,
        "col_rho": "R_Medidas",
        "L_med": result.df["DISTANCIA_AB_2"].to_numpy(dtype=float),
        "rho_med": result.df["R_Medidas"].to_numpy(dtype=float),
    }
    changed, msg, L_med, rho_med, col_l, col_rho = refresh_stored_csv_dataset(stale_panel)
    assert changed
    assert col_rho == "Ro_Calculados"
    assert rho_med[0] == 117.15
    assert "R_Medidas" in msg or "Ro_Calculados" in msg


def test_assess_correct_columns_for_04_csv():
    result = parse_sev_file(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/04.csv"
    )
    notes = assess_column_selection(
        result.col_l,
        result.col_rho,
        result.L_med,
        result.rho_med,
        result.suggested_col_l,
        result.suggested_col_rho,
    )
    assert any(note.level == "success" for note in notes)