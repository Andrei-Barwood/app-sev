"""Exportación de resultados de malla BT compatible con Dibujar_Malla_BT.lsp (MALLABTCSV / MALLABTJSON)."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

import pandas as pd

# Encabezados tabulares (mismo estilo que resultados_sev.csv de app-sev)
MALLA_BT_TABULAR_HEADERS = (
    "Largo [m]",
    "Ancho [m]",
    "Separacion D [m]",
    "Profundidad [m]",
    "Resistividad [Ω·m]",
    "Rg [Ω]",
    "Longitud total [m]",
    "Area [m2]",
    "Etiqueta",
    "Modo 3D",
    "Agregar picas",
    "Longitud picas [m]",
)

MALLA_BT_TABULAR_KEYS = (
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
)


def calc_longitud_total(largo: float, ancho: float, separacion: float) -> float:
    """Réplica la fórmula de malla-bt:entero-lineas y malla-bt:calc-longitud-total en AutoLISP."""
    if separacion <= 0:
        return 0.0
    n_x = max(1, int(largo / separacion) + 1)
    n_y = max(1, int(ancho / separacion) + 1)
    return n_x * ancho + n_y * largo


def calc_rg_lisp(rho: float, largo: float, ancho: float, separacion: float) -> float | None:
    """Rg aproximada usada por el script AutoLISP (IEEE 80 simplificada)."""
    lt = calc_longitud_total(largo, ancho, separacion)
    area = largo * ancho
    if lt <= 0 or area <= 0:
        return None
    return rho * (1.0 / lt + 1.0 / (20.0 * area) ** 0.5)


def build_malla_bt_payload(
    *,
    largo: float,
    ancho: float,
    separacion: float,
    profundidad: float,
    resistividad: float,
    etiqueta: str = "",
    modo_3d: bool = False,
    agregar_picas: bool = True,
    longitud_picas: float = 3.0,
    rg: float | None = None,
    longitud_total: float | None = None,
    area: float | None = None,
) -> dict[str, Any]:
    """Arma el diccionario de parámetros esperado por MALLABTCSV / MALLABTJSON."""
    area_val = area if area is not None else largo * ancho
    lt_val = longitud_total if longitud_total is not None else calc_longitud_total(largo, ancho, separacion)
    rg_val = rg if rg is not None else calc_rg_lisp(resistividad, largo, ancho, separacion)

    payload: dict[str, Any] = {
        "largo": round(float(largo), 6),
        "ancho": round(float(ancho), 6),
        "separacion": round(float(separacion), 6),
        "profundidad": round(float(profundidad), 6),
        "resistividad": round(float(resistividad), 6),
        "longitud_total": round(float(lt_val), 6),
        "area": round(float(area_val), 6),
        "etiqueta": etiqueta.strip(),
        "modo_3d": 1 if modo_3d else 0,
        "agregar_picas": 1 if agregar_picas else 0,
        "longitud_picas": round(float(longitud_picas), 6),
    }
    if rg_val is not None:
        payload["rg"] = round(float(rg_val), 6)
    return payload


def _format_scalar(value: Any) -> str:
    if isinstance(value, str):
        return value
    return f"{value:g}"


def format_malla_bt_csv_parametros(payload: dict[str, Any]) -> str:
    """CSV parametro,valor (formato legacy reconocido por malla-bt:parsear-csv)."""
    rows = [("parametro", "valor")]
    field_order = (
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
    )
    for key in field_order:
        if key not in payload:
            continue
        rows.append((key, _format_scalar(payload[key])))
    return "\n".join(f"{k},{v}" for k, v in rows) + "\n"


def format_malla_bt_csv(payload: dict[str, Any]) -> str:
    """CSV tabular horizontal (mismo estilo que resultados_sev.csv de app-sev)."""
    values: list[str] = []
    for key in MALLA_BT_TABULAR_KEYS:
        if key not in payload:
            values.append("")
            continue
        values.append(_format_scalar(payload[key]))
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(MALLA_BT_TABULAR_HEADERS)
    writer.writerow(values)
    return buffer.getvalue()


def format_malla_bt_csv_completo(
    payload: dict[str, Any],
    df_sev: pd.DataFrame | None = None,
) -> str:
    """Exporta parametros de malla + tabla SEV anexa (compatible con MALLABTCSV v1.6)."""
    parts = [format_malla_bt_csv_parametros(payload).rstrip("\n")]
    if df_sev is not None and not df_sev.empty:
        parts.append("")
        parts.append(df_sev.to_csv(index=False).rstrip("\n"))
    return "\n".join(parts) + "\n"


def format_malla_bt_json(payload: dict[str, Any]) -> str:
    """JSON con las claves que extrae malla-bt:parsear-json."""
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"