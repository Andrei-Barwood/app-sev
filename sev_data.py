"""Dataset SEV activo: única fuente de verdad para gráficos, modelo y optimización."""

from __future__ import annotations

from typing import Any

import numpy as np


def store_active_dataset(
    st_session: Any,
    L_med: np.ndarray,
    rho_med: np.ndarray,
    *,
    source: str,
    filename: str = "",
    col_l: str = "",
    col_rho: str = "",
    df=None,
    assessments=None,
    feasibility=None,
    reference_benchmark=None,
) -> None:
    L_arr = np.asarray(L_med, dtype=float).copy()
    rho_arr = np.asarray(rho_med, dtype=float).copy()
    order = np.argsort(L_arr)
    L_arr = L_arr[order]
    rho_arr = rho_arr[order]

    st_session.sev_active_dataset = {
        "L_med": L_arr,
        "rho_med": rho_arr,
        "source": source,
        "filename": filename,
        "col_l": col_l,
        "col_rho": col_rho,
        "n_points": int(len(L_arr)),
    }

    if source == "Cargar archivo (CSV/Excel)":
        st_session.sev_import_panel = {
            "filename": filename,
            "df": df,
            "col_l": col_l,
            "col_rho": col_rho,
            "assessments": assessments or [],
            "n_points": int(len(L_arr)),
            "L_med": L_arr,
            "rho_med": rho_arr,
            "feasibility": feasibility,
            "reference_benchmark": reference_benchmark,
        }
    else:
        st_session.pop("sev_import_panel", None)


def get_active_dataset(st_session: Any) -> dict | None:
    dataset = st_session.get("sev_active_dataset")
    if not dataset:
        return None
    return {
        **dataset,
        "L_med": np.asarray(dataset["L_med"], dtype=float).copy(),
        "rho_med": np.asarray(dataset["rho_med"], dtype=float).copy(),
    }


def get_active_L_rho(st_session: Any) -> tuple[np.ndarray | None, np.ndarray | None]:
    dataset = get_active_dataset(st_session)
    if dataset is None:
        return None, None
    return dataset["L_med"], dataset["rho_med"]


def clear_active_dataset(st_session: Any) -> None:
    st_session.pop("sev_active_dataset", None)
    st_session.pop("sev_import_panel", None)
    st_session.pop("sev_data_signature", None)
    st_session.pop("model_init_report", None)