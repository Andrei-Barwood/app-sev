"""Métricas de ajuste SEV y criterio de aceptación (error ≤ 5 %)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

ACCEPTANCE_ERROR_PCT = 5.0


def _safe_log10(values: np.ndarray) -> np.ndarray:
    return np.log10(np.maximum(np.asarray(values, dtype=float), 1e-6))


@dataclass(frozen=True)
class FitReport:
    rmse_linear: float
    rmse_log: float
    r2_log: float
    mean_error_pct: float
    max_error_pct: float
    mean_error_log_pct: float
    max_error_log_pct: float
    n_points: int
    n_over_threshold: int
    accepted: bool
    strict_accepted: bool
    threshold_pct: float
    results_df: pd.DataFrame


def linear_error_pct(rho_med: np.ndarray, rho_calc: np.ndarray) -> np.ndarray:
    rho_med = np.asarray(rho_med, dtype=float)
    rho_calc = np.asarray(rho_calc, dtype=float)
    return np.abs((rho_med - rho_calc) / rho_med) * 100.0


def log_error_pct(rho_med: np.ndarray, rho_calc: np.ndarray) -> np.ndarray:
    """Error relativo en escala log: útil cuando ρ abarca varios órdenes de magnitud."""
    log_med = _safe_log10(rho_med)
    log_calc = _safe_log10(rho_calc)
    decades = np.abs(log_med - log_calc)
    return (10.0**decades - 1.0) * 100.0


def compute_r2_log(rho_med: np.ndarray, rho_calc: np.ndarray) -> float:
    log_med = _safe_log10(rho_med)
    log_calc = _safe_log10(rho_calc)
    ss_res = float(np.sum((log_med - log_calc) ** 2))
    ss_tot = float(np.sum((log_med - np.mean(log_med)) ** 2))
    return 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0


def build_results_dataframe(
    L_med: np.ndarray,
    rho_med: np.ndarray,
    rho_calc: np.ndarray,
    *,
    threshold_pct: float = ACCEPTANCE_ERROR_PCT,
) -> pd.DataFrame:
    err_lin = linear_error_pct(rho_med, rho_calc)
    err_log = log_error_pct(rho_med, rho_calc)
    return pd.DataFrame(
        {
            "L (AB/2) [m]": np.asarray(L_med, dtype=float),
            "Rho Medido [Ω·m]": np.asarray(rho_med, dtype=float),
            "Rho Calculado [Ω·m]": np.asarray(rho_calc, dtype=float),
            "Error (%)": err_lin,
            "Error log (%)": err_log,
            "Cumple ≤5%": err_lin <= threshold_pct,
        }
    )


def assess_fit(
    L_med: np.ndarray,
    rho_med: np.ndarray,
    rho_calc: np.ndarray,
    *,
    threshold_pct: float = ACCEPTANCE_ERROR_PCT,
) -> FitReport:
    rho_med = np.asarray(rho_med, dtype=float)
    rho_calc = np.asarray(rho_calc, dtype=float)
    err_lin = linear_error_pct(rho_med, rho_calc)
    err_log = log_error_pct(rho_med, rho_calc)
    log_med = _safe_log10(rho_med)
    log_calc = _safe_log10(rho_calc)

    results_df = build_results_dataframe(L_med, rho_med, rho_calc, threshold_pct=threshold_pct)
    n_over = int(np.sum(err_lin > threshold_pct))

    mean_err = float(np.mean(err_lin))
    return FitReport(
        rmse_linear=float(np.sqrt(np.mean((rho_med - rho_calc) ** 2))),
        rmse_log=float(np.sqrt(np.mean((log_med - log_calc) ** 2))),
        r2_log=compute_r2_log(rho_med, rho_calc),
        mean_error_pct=mean_err,
        max_error_pct=float(np.max(err_lin)),
        mean_error_log_pct=float(np.mean(err_log)),
        max_error_log_pct=float(np.max(err_log)),
        n_points=int(len(rho_med)),
        n_over_threshold=n_over,
        accepted=mean_err <= threshold_pct,
        strict_accepted=n_over == 0,
        threshold_pct=threshold_pct,
        results_df=results_df,
    )


def log_axis_ticks(values: np.ndarray, *, max_ticks: int = 10) -> list[float]:
    """Genera marcas legibles para ejes logarítmicos sin solapamiento."""
    values = np.asarray(values, dtype=float)
    positive = values[values > 0]
    if positive.size == 0:
        return [1.0]

    vmin = float(np.min(positive))
    vmax = float(np.max(positive))
    exp_min = int(np.floor(np.log10(vmin)))
    exp_max = int(np.ceil(np.log10(vmax)))
    candidates: list[float] = []

    for exp in range(exp_min, exp_max + 1):
        base = 10.0**exp
        for mult in (1.0, 2.0, 3.0, 5.0):
            tick = mult * base
            if vmin * 0.85 <= tick <= vmax * 1.15:
                candidates.append(tick)

    for edge in (vmin, vmax):
        if edge not in candidates:
            candidates.append(edge)

    candidates = sorted(set(round(t, 6) for t in candidates))
    if len(candidates) <= max_ticks:
        return candidates

    step = max(1, len(candidates) // max_ticks)
    return candidates[::step]


def style_results_table(df: pd.DataFrame, threshold_pct: float = ACCEPTANCE_ERROR_PCT):
    def _highlight(row):
        err = row.get("Error (%)", 0)
        if err > threshold_pct:
            return ["background-color: #fde2e2; color: #8b0000"] * len(row)
        return ["background-color: #e8f5e9; color: #1b5e20"] * len(row)

    fmt = {
        "L (AB/2) [m]": "{:.2f}",
        "Rho Medido [Ω·m]": "{:.2f}",
        "Rho Calculado [Ω·m]": "{:.2f}",
        "Error (%)": "{:.2f}",
        "Error log (%)": "{:.2f}",
    }
    display_cols = [c for c in df.columns if c != "Cumple ≤5%"]
    return (
        df[display_cols]
        .style.format(fmt)
        .apply(_highlight, axis=1)
    )