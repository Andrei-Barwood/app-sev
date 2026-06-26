"""Estado unificado del modelo de capas (evita desincronización de widgets Streamlit)."""

from __future__ import annotations

from typing import Any

import numpy as np


def ensure_layer_lengths(st_session: Any, n_layers: int) -> None:
    rho = list(st_session.rho)
    h = list(st_session.h)
    fixed_rho = list(getattr(st_session, "fixed_rho", []))
    fixed_h = list(getattr(st_session, "fixed_h", []))

    if len(rho) < n_layers:
        rho.extend([rho[-1] if rho else 100.0] * (n_layers - len(rho)))
    else:
        rho = rho[:n_layers]

    if len(h) < n_layers - 1:
        last_h = h[-1] if h else 10.0
        h.extend([last_h] * (n_layers - 1 - len(h)))
    else:
        h = h[: n_layers - 1]

    if len(fixed_rho) < n_layers:
        fixed_rho.extend([False] * (n_layers - len(fixed_rho)))
    else:
        fixed_rho = fixed_rho[:n_layers]

    if len(fixed_h) < n_layers - 1:
        fixed_h.extend([False] * (n_layers - 1 - len(fixed_h)))
    else:
        fixed_h = fixed_h[: n_layers - 1]

    st_session.rho = rho
    st_session.h = h
    st_session.fixed_rho = fixed_rho
    st_session.fixed_h = fixed_h


def extend_layers_from_data(
    st_session: Any,
    n_layers: int,
    L_med: np.ndarray | None = None,
    rho_med: np.ndarray | None = None,
) -> None:
    """Añade capas interpolando desde los datos SEV en lugar de valores fijos arbitrarios."""
    current = len(st_session.rho)
    if n_layers <= current:
        return

    if L_med is not None and rho_med is not None and len(L_med) >= 3:
        from model_init import estimate_initial_model

        target = estimate_initial_model(np.asarray(L_med), np.asarray(rho_med))
        if target.n_layers >= n_layers:
            st_session.rho = list(target.rho[:n_layers])
            st_session.h = list(target.h[: n_layers - 1])
            st_session.fixed_rho = [False] * n_layers
            st_session.fixed_h = [False] * (n_layers - 1)
            return

    rho = list(st_session.rho)
    h = list(st_session.h)
    while len(rho) < n_layers:
        if len(rho) >= 2:
            rho.append(max(0.1, float(np.sqrt(rho[-1] * rho[-2]))))
        else:
            rho.append(max(0.1, float(rho[-1]) if rho else 100.0))
    while len(h) < n_layers - 1:
        if h:
            h.append(max(0.1, float(h[-1] * 1.5)))
        else:
            h.append(10.0)
    st_session.rho = rho
    st_session.h = h
    st_session.fixed_rho = [False] * n_layers
    st_session.fixed_h = [False] * (n_layers - 1)


def clear_layer_widget_keys(st_session: Any) -> None:
    for key in list(st_session.keys()):
        if key.startswith(("layer_rho_", "layer_h_", "layer_frho_", "layer_fh_", "layer_n_")):
            del st_session[key]
        elif key in {"rho_0", "rho_1", "rho_2", "rho_3", "rho_4", "rho_5", "rho_6", "rho_7", "rho_8", "rho_9"}:
            del st_session[key]
        elif key.startswith(("rho_", "h_", "frho_", "fh_")):
            del st_session[key]


def bump_layer_widget_generation(st_session: Any) -> int:
    generation = int(st_session.get("layer_widget_generation", 0)) + 1
    st_session.layer_widget_generation = generation
    clear_layer_widget_keys(st_session)
    return generation


def set_layer_model(
    st_session: Any,
    rho: list[float],
    h: list[float],
    *,
    fixed_rho: list[bool] | None = None,
    fixed_h: list[bool] | None = None,
) -> None:
    n_layers = len(rho)
    st_session.rho = [max(0.01, float(v)) for v in rho]
    st_session.h = [max(0.001, float(v)) for v in h[: n_layers - 1]]
    st_session.fixed_rho = list(fixed_rho) if fixed_rho else [False] * n_layers
    st_session.fixed_h = list(fixed_h) if fixed_h else [False] * max(n_layers - 1, 0)
    st_session.n_layers = n_layers
    ensure_layer_lengths(st_session, n_layers)
    bump_layer_widget_generation(st_session)


def apply_model_init_to_session(init, st_session: Any) -> None:
    set_layer_model(st_session, init.rho, init.h)
    st_session.model_init_report = {
        "curve_type": init.curve_type,
        "mooney_key": init.mooney_key,
        "coherence_score": init.coherence_score,
        "init_rmse": init.init_rmse,
        "init_r2": init.init_r2,
        "use_global_search": init.use_global_search,
        "notes": init.notes,
        "rho": list(st_session.rho),
        "h": list(st_session.h),
    }


def widget_key(st_session: Any, kind: str, index: int) -> str:
    generation = int(st_session.get("layer_widget_generation", 0))
    return f"layer_{kind}_{generation}_{index}"


def read_layer_model_from_widgets(st_session: Any, n_layers: int) -> tuple[list[float], list[float], list[bool], list[bool]]:
    rho: list[float] = []
    h: list[float] = []
    fixed_rho: list[bool] = []
    fixed_h: list[bool] = []

    for i in range(n_layers):
        rho.append(float(st_session.get(widget_key(st_session, "rho", i), st_session.rho[i])))
        fixed_rho.append(bool(st_session.get(widget_key(st_session, "frho", i), st_session.fixed_rho[i])))
        if i < n_layers - 1:
            h.append(float(st_session.get(widget_key(st_session, "h", i), st_session.h[i])))
            fixed_h.append(bool(st_session.get(widget_key(st_session, "fh", i), st_session.fixed_h[i])))

    return rho, h, fixed_rho, fixed_h


def sync_lists_from_widgets(st_session: Any, n_layers: int) -> None:
    rho, h, fixed_rho, fixed_h = read_layer_model_from_widgets(st_session, n_layers)
    st_session.rho = rho
    st_session.h = h
    st_session.fixed_rho = fixed_rho
    st_session.fixed_h = fixed_h