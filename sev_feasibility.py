"""Estimación rápida de si un dataset SEV puede cumplir el criterio de error ≤ 5 %."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import differential_evolution

from core import calc_rho_a
from model_init import estimate_initial_model
from sev_metrics import ACCEPTANCE_ERROR_PCT, _safe_log10, linear_error_pct


@dataclass(frozen=True)
class FeasibilityReport:
    level: str
    title: str
    message: str
    contrast: float
    estimated_mean_error_pct: float
    estimated_min_mean_pct: float
    can_pass_mean: bool
    can_pass_strict: bool
    curve_type: str
    n_layers_tried: int


def _quick_mean_error_pct(
    L_med: np.ndarray,
    rho_med: np.ndarray,
    n_layers: int,
    *,
    seed: int = 42,
) -> float:
    L_med = np.asarray(L_med, dtype=float)
    rho_med = np.asarray(rho_med, dtype=float)
    init = estimate_initial_model(L_med, rho_med)
    if n_layers == 2:
        x0 = [
            np.log10(max(init.rho[0], 0.01)),
            np.log10(max(init.rho[-1], 0.01)),
            np.log10(max(init.h[0] if init.h else 1.0, 0.001)),
        ]
        bounds = [
            (np.log10(0.01), np.log10(5000)),
            (np.log10(0.01), np.log10(5000)),
            (np.log10(0.001), np.log10(100)),
        ]

        def obj(x: np.ndarray) -> float:
            r1, r2, h1 = 10 ** x[0], 10 ** x[1], 10 ** x[2]
            calc = calc_rho_a(L_med, [r1, r2], [h1])
            return float(np.mean((_safe_log10(rho_med) - _safe_log10(calc)) ** 2))

    else:
        rho3 = init.rho[2] if len(init.rho) > 2 else init.rho[-1]
        h1 = init.h[0] if init.h else 1.0
        h2 = init.h[1] if len(init.h) > 1 else 10.0
        x0 = [
            np.log10(max(init.rho[0], 0.01)),
            np.log10(max(init.rho[1] if len(init.rho) > 1 else rho3, 0.01)),
            np.log10(max(rho3, 0.01)),
            np.log10(max(h1, 0.001)),
            np.log10(max(h2, 0.01)),
        ]
        bounds = [
            (np.log10(0.01), np.log10(5000)),
            (np.log10(0.01), np.log10(5000)),
            (np.log10(0.01), np.log10(5000)),
            (np.log10(0.001), np.log10(100)),
            (np.log10(0.01), np.log10(100)),
        ]

        def obj(x: np.ndarray) -> float:
            r = [10 ** x[i] for i in range(3)]
            h = [10 ** x[3], 10 ** x[4]]
            calc = calc_rho_a(L_med, r, h)
            return float(np.mean((_safe_log10(rho_med) - _safe_log10(calc)) ** 2))

    result = differential_evolution(
        obj,
        bounds,
        seed=seed,
        maxiter=180,
        popsize=12,
        tol=1e-3,
        polish=True,
    )
    if n_layers == 2:
        r1, r2, h1 = 10 ** result.x[0], 10 ** result.x[1], 10 ** result.x[2]
        calc = calc_rho_a(L_med, [r1, r2], [h1])
    else:
        r = [10 ** result.x[i] for i in range(3)]
        h = [10 ** result.x[3], 10 ** result.x[4]]
        calc = calc_rho_a(L_med, r, h)
    return float(np.mean(linear_error_pct(rho_med, calc)))


def assess_feasibility(L_med: np.ndarray, rho_med: np.ndarray) -> FeasibilityReport:
    L_med = np.asarray(L_med, dtype=float)
    rho_med = np.asarray(rho_med, dtype=float)
    init = estimate_initial_model(L_med, rho_med)
    contrast = float(np.max(rho_med) / max(float(np.min(rho_med)), 1e-3))

    estimates = [
        _quick_mean_error_pct(L_med, rho_med, 2, seed=7),
        _quick_mean_error_pct(L_med, rho_med, 3, seed=19),
    ]
    est_min = float(min(estimates))
    est_mean = float(np.mean(estimates))
    can_pass_mean = est_min <= ACCEPTANCE_ERROR_PCT
    can_pass_strict = False

    if contrast > 200 and est_min > 20:
        level, title = "error", "Muy improbable alcanzar 5 %"
        message = (
            f"Contraste ρ máx/ρ mín ≈ {contrast:.0f}. La exploración rápida estima "
            f"error medio ≥ {est_min:.0f} %. Con este archivo el ajuste 1D **no** "
            f"alcanzará el {ACCEPTANCE_ERROR_PCT:.0f} % permitido."
        )
    elif est_min > ACCEPTANCE_ERROR_PCT * 2:
        level, title = "warning", "Difícil cumplir 5 %"
        message = (
            f"Error medio estimado ≥ {est_min:.1f} % (criterio {ACCEPTANCE_ERROR_PCT:.0f} %). "
            f"Usa búsqueda global y revisa columnas L=AB/2 y ρ medida."
        )
    elif est_min > ACCEPTANCE_ERROR_PCT:
        level, title = "warning", "Ajuste marginal"
        message = (
            f"Error medio estimado ≈ {est_min:.1f}–{max(estimates):.1f} %. "
            f"Puede quedar ligeramente por encima del {ACCEPTANCE_ERROR_PCT:.0f} %."
        )
    else:
        level, title = "success", "Ajuste viable"
        message = (
            f"Error medio estimado ≈ {est_min:.1f} %. "
            f"Es razonable esperar cumplir el criterio de {ACCEPTANCE_ERROR_PCT:.0f} % "
            f"(promedio). El criterio estricto (todos los puntos ≤ 5 %) puede no lograrse."
        )

    return FeasibilityReport(
        level=level,
        title=title,
        message=message,
        contrast=contrast,
        estimated_mean_error_pct=est_mean,
        estimated_min_mean_pct=est_min,
        can_pass_mean=can_pass_mean,
        can_pass_strict=can_pass_strict,
        curve_type=init.curve_type,
        n_layers_tried=2,
    )