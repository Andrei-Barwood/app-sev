"""Cálculos Schlumberger: resistencia medida → resistividad aparente."""

from __future__ import annotations

import numpy as np
import pandas as pd


def schlumberger_k_factor(ab2: float, mn: float) -> float:
    """
    Factor geométrico K para arreglo Schlumberger (MN constante).

    ρ_a = K · R

    K = π · [(AB/2)² − (MN/2)²] / MN
    """
    ab2 = float(ab2)
    mn = max(float(mn), 1e-6)
    return float(np.pi * (ab2**2 - (mn / 2.0) ** 2) / mn)


def resistance_to_apparent_resistivity(
    ab2: np.ndarray,
    resistance_ohm: np.ndarray,
    mn: float | np.ndarray = 1.0,
) -> np.ndarray:
    ab2 = np.asarray(ab2, dtype=float)
    r = np.asarray(resistance_ohm, dtype=float)
    mn_arr = np.full_like(ab2, float(mn), dtype=float) if np.isscalar(mn) else np.asarray(mn, dtype=float)
    k = np.pi * (ab2**2 - (mn_arr / 2.0) ** 2) / np.maximum(mn_arr, 1e-6)
    return k * r


def build_schlumberger_verification_table(
    df: pd.DataFrame,
    col_l: str,
    col_r: str | None = None,
    col_rho: str | None = None,
    col_mn: str | None = None,
) -> pd.DataFrame:
    """Tabla de verificación ρ_a = K·R para el informe técnico."""
    l_vals = pd.to_numeric(df[col_l], errors="coerce").to_numpy(dtype=float)
    if col_mn and col_mn in df.columns:
        mn_vals = pd.to_numeric(df[col_mn], errors="coerce").to_numpy(dtype=float)
    else:
        mn_vals = np.full(len(l_vals), 1.0)

    if col_r and col_r in df.columns:
        r_vals = pd.to_numeric(df[col_r], errors="coerce").to_numpy(dtype=float)
    else:
        r_vals = np.full(len(l_vals), np.nan)

    rho_calc = resistance_to_apparent_resistivity(l_vals, r_vals, mn_vals)
    k_vals = np.array([schlumberger_k_factor(l, m) for l, m in zip(l_vals, mn_vals)])

    out = pd.DataFrame({
        "L (AB/2) [m]": l_vals,
        "MN [m]": mn_vals,
        "K [m]": np.round(k_vals, 4),
        "R medida [Ω]": r_vals,
        "ρ_a calculada [Ω·m]": np.round(rho_calc, 2),
    })
    if col_rho and col_rho in df.columns:
        rho_ref = pd.to_numeric(df[col_rho], errors="coerce").to_numpy(dtype=float)
        out["ρ_a archivo [Ω·m]"] = rho_ref
        out["Δ %"] = np.where(
            np.isfinite(rho_ref) & (rho_ref > 0),
            np.abs((rho_calc - rho_ref) / rho_ref) * 100.0,
            np.nan,
        )
    return out.dropna(subset=["L (AB/2) [m]", "R medida [Ω]"])