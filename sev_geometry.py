"""Notas sobre columnas geométricas (a, d) en exportaciones de telurómetro."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd


def _normalize_col(name: object) -> str:
    text = str(name).lower().strip()
    text = text.replace("ω", "o").replace("·", "")
    text = re.sub(r"[\[\]()%°]", "", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _find_col(df: pd.DataFrame, exact: str) -> str | None:
    for col in df.columns:
        if _normalize_col(col) == exact:
            return str(col)
    return None


def inspect_electrode_geometry(df: pd.DataFrame, col_l: str) -> dict | None:
    """
    Analiza columnas a/d típicas de telurómetros (p. ej. 04.csv).
    DISTANCIA_AB_2 es la abscisa correcta del SEV; a suele ser el desplazamiento
    del electrodo interior y no sustituye a L en el modelo 1D.
    """
    col_a = _find_col(df, "a")
    col_d = _find_col(df, "d")
    if col_a is None and col_d is None:
        return None

    L = pd.to_numeric(df[col_l], errors="coerce").to_numpy(dtype=float)
    info: dict = {"col_a": col_a, "col_d": col_d, "messages": []}

    if col_a is not None:
        a = pd.to_numeric(df[col_a], errors="coerce").to_numpy(dtype=float)
        mask = np.isfinite(L) & np.isfinite(a) & (L > 0)
        if np.any(mask):
            delta = L[mask] - a[mask]
            info["delta_l_minus_a_mean"] = float(np.mean(delta))
            info["delta_l_minus_a_std"] = float(np.std(delta))
            if np.std(delta) < 0.15:
                info["messages"].append(
                    f"`{col_l}` ≈ `{col_a}` + {info['delta_l_minus_a_mean']:.2f} m de forma consistente. "
                    f"Usa **{col_l}** como L (AB/2); `{col_a}` es separación interior, no reemplaza L."
                )
            else:
                info["messages"].append(
                    f"Columna `{col_a}` presente: separación de electrodos interiores. "
                    "No sustituye a L=AB/2 en el modelo de capas."
                )

    if col_d is not None:
        d = pd.to_numeric(df[col_d], errors="coerce").dropna().unique()
        if len(d) == 1:
            info["messages"].append(
                f"Columna `{col_d}` constante ({d[0]:g}): parámetro de campo del telurómetro; "
                "el modelo 1D no la usa directamente."
            )

    info["messages"].append(
        "Probamos ajustes con L, a y combinaciones: **DISTANCIA_AB_2 / AB_2** da la mejor física SEV."
    )
    return info