import json

import pandas as pd

from malla_export import (
    MALLA_BT_TABULAR_HEADERS,
    build_malla_bt_payload,
    calc_longitud_total,
    format_malla_bt_csv,
    format_malla_bt_csv_completo,
    format_malla_bt_csv_parametros,
    format_malla_bt_json,
)


def test_calc_longitud_total_matches_lisp_example():
    assert calc_longitud_total(20, 15, 2.5) == 275.0


def test_csv_tabular_header_compatible_with_autolisp():
    payload = build_malla_bt_payload(
        largo=20,
        ancho=15,
        separacion=2.5,
        profundidad=0.8,
        resistividad=100,
        etiqueta="Malla Subestacion A",
        modo_3d=True,
        agregar_picas=True,
        longitud_picas=3,
        rg=0.452,
        longitud_total=92.5,
        area=300,
    )
    csv_text = format_malla_bt_csv(payload)
    lines = [line for line in csv_text.strip().splitlines() if line]
    assert lines[0].split(",")[0] == MALLA_BT_TABULAR_HEADERS[0]
    assert "Largo [m]" in lines[0]
    assert "20" in lines[1]
    assert "Malla Subestacion A" in lines[1]


def test_csv_parametros_legacy_still_supported():
    payload = build_malla_bt_payload(
        largo=20,
        ancho=15,
        separacion=2.5,
        profundidad=0.8,
        resistividad=100,
        etiqueta="Malla Subestacion A",
    )
    csv_text = format_malla_bt_csv_parametros(payload)
    lines = [line for line in csv_text.strip().splitlines() if line]
    assert lines[0].lower().startswith("parametro,")
    assert "largo,20" in lines


def test_csv_completo_includes_sev_section():
    payload = build_malla_bt_payload(
        largo=5,
        ancho=5,
        separacion=1,
        profundidad=0.6,
        resistividad=168.4,
        etiqueta="Prueba",
    )
    sev_df = pd.DataFrame(
        {
            "L (AB/2) [m]": [1.5, 2.0],
            "Rho Medido [Ω·m]": [168.4, 170.8],
            "Rho Calculado [Ω·m]": [157.5, 177.5],
            "Error (%)": [6.46, 3.94],
        }
    )
    csv_text = format_malla_bt_csv_completo(payload, sev_df)
    assert "parametro,valor" in csv_text
    assert "L (AB/2) [m],Rho Medido" in csv_text
    assert "1.5,168.4" in csv_text


def test_json_contains_expected_keys():
    payload = build_malla_bt_payload(
        largo=5,
        ancho=5,
        separacion=1,
        profundidad=0.6,
        resistividad=100,
        etiqueta="Prueba",
    )
    data = json.loads(format_malla_bt_json(payload))
    for key in (
        "largo",
        "ancho",
        "separacion",
        "profundidad",
        "resistividad",
        "rg",
        "longitud_total",
        "area",
        "etiqueta",
        "modo_3d",
        "agregar_picas",
        "longitud_picas",
    ):
        assert key in data