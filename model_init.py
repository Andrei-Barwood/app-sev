"""Estimación coherente del modelo de capas a partir de datos SEV importados."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from core import calc_rho_a


MOONEY_KEYS = {
    "H": "3 Capas - Tipo H (Mínimo) ρ1>ρ2<ρ3",
    "K": "3 Capas - Tipo K (Máximo) ρ1<ρ2>ρ3",
    "A": "3 Capas - Tipo A (Ascendente) ρ1<ρ2<ρ3",
    "Q": "3 Capas - Tipo Q (Descendente) ρ1>ρ2>ρ3",
    "DESC2": "2 Capas - Descendente",
    "ASC2": "2 Capas - Ascendente",
}


@dataclass
class ModelInitResult:
    n_layers: int
    rho: list[float]
    h: list[float]
    curve_type: str
    mooney_key: str
    coherence_score: float
    init_rmse: float
    init_r2: float
    use_global_search: bool
    recommended_n_layers: int = 3
    notes: list[str] = field(default_factory=list)


def _smooth_curve(rho: np.ndarray) -> np.ndarray:
    if len(rho) >= 5:
        return np.convolve(rho, np.ones(3) / 3.0, mode="valid")
    return rho.astype(float)


def _detect_curve_type(L: np.ndarray, rho: np.ndarray) -> str:
    smoothed = _smooth_curve(rho)
    n = len(smoothed)
    margin = max(1, int(n * 0.15))
    idx_max = int(np.argmax(smoothed))
    idx_min = int(np.argmin(smoothed))

    if margin <= idx_max <= n - 1 - margin:
        return "K"
    if margin <= idx_min <= n - 1 - margin:
        return "H"
    if smoothed[-1] > smoothed[0] * 1.15:
        return "A" if n >= 6 else "ASC2"
    if smoothed[0] > smoothed[-1] * 1.15:
        return "Q" if n >= 6 else "DESC2"
    return "Q"


def _segment_rho_values(L: np.ndarray, rho: np.ndarray, n_layers: int) -> list[float]:
    log_l = np.log10(np.maximum(L, 1e-6))
    values: list[float] = []
    for i in range(n_layers):
        q_lo = i / n_layers
        q_hi = (i + 1) / n_layers
        lo = np.quantile(log_l, q_lo)
        hi = np.quantile(log_l, q_hi)
        if i == n_layers - 1:
            mask = (log_l >= lo) & (log_l <= hi)
        else:
            mask = (log_l >= lo) & (log_l < hi)
        if not np.any(mask):
            mask = log_l >= lo
        segment = rho[mask]
        values.append(max(0.1, float(np.median(segment))))
    return values


def _adjust_rho_for_curve_type(rho_values: list[float], curve_type: str, smoothed: np.ndarray) -> list[float]:
    rho1 = max(0.1, float(smoothed[0]))
    rho_end = max(0.1, float(smoothed[-1]))
    if curve_type == "H":
        return [rho1, max(0.1, float(np.min(smoothed)) * 0.7), rho_end]
    if curve_type == "K":
        return [rho1, max(0.1, float(np.max(smoothed)) * 1.2), rho_end]
    if curve_type in {"A", "ASC2"}:
        return [rho1, max(0.1, float(np.sqrt(rho1 * rho_end))), rho_end]
    if curve_type in {"Q", "DESC2"}:
        mid = max(0.1, float(np.exp((np.log(rho1) + np.log(rho_end)) / 2.0)))
        return [rho1, mid, rho_end]
    return rho_values


def _estimate_transition_thickness(L: np.ndarray, rho: np.ndarray) -> float:
    log_l = np.log10(np.maximum(L, 1e-6))
    log_r = np.log10(np.maximum(rho, 1e-6))
    target = (log_r[0] + log_r[-1]) / 2.0
    for i in range(len(log_r) - 1):
        if (log_r[i] - target) * (log_r[i + 1] - target) <= 0:
            denom = log_r[i + 1] - log_r[i]
            frac = 0.5 if abs(denom) < 1e-12 else (target - log_r[i]) / denom
            l_cross = 10 ** (log_l[i] + frac * (log_l[i + 1] - log_l[i]))
            return float(
                np.clip(
                    l_cross * 0.35,
                    max(float(L[0]) * 0.005, 0.001),
                    max(float(L[-1]) * 2.0, 0.01),
                )
            )
    return float(np.clip(float(np.median(L)) * 0.25, max(float(L[0]) * 0.005, 0.001), float(L[-1])))


def _estimate_thicknesses(L: np.ndarray, rho: np.ndarray, n_layers: int) -> list[float]:
    if n_layers < 2:
        return []
    log_l = np.log10(np.maximum(L, 1e-6))
    log_r = np.log10(np.maximum(rho, 1e-6))
    slope = np.gradient(log_r, log_l)
    interior = slope[1:-1] if len(slope) > 2 else slope
    if len(interior) >= n_layers - 1:
        idxs = np.argsort(np.abs(interior))[-(n_layers - 1) :]
        idxs.sort()
        candidates = [float(L[i + 1]) for i in idxs]
    else:
        candidates = list(np.geomspace(max(float(L[1]), float(L[0]) * 1.2), float(L[-2]), n_layers - 1))

    h_min = max(float(np.min(L)) * 0.002, 0.001)
    h_max = max(float(np.max(L)) * 4.0, h_min * 20.0)
    cleaned = [float(np.clip(h, h_min, h_max)) for h in candidates]
    cleaned.sort()
    for i in range(1, len(cleaned)):
        if cleaned[i] <= cleaned[i - 1]:
            cleaned[i] = min(h_max, cleaned[i - 1] * 1.25)
    return cleaned


def _metrics(L: np.ndarray, rho: np.ndarray, rho_model: list[float], h_model: list[float]) -> tuple[float, float]:
    rho_calc = calc_rho_a(L, rho_model, h_model)
    rmse = float(np.sqrt(np.mean((rho - rho_calc) ** 2)))
    log_med = np.log10(np.maximum(rho, 1e-6))
    log_calc = np.log10(np.maximum(rho_calc, 1e-6))
    ss_res = float(np.sum((log_med - log_calc) ** 2))
    ss_tot = float(np.sum((log_med - np.mean(log_med)) ** 2))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    return rmse, r2


def estimate_initial_model(L: np.ndarray, rho: np.ndarray) -> ModelInitResult:
    L = np.asarray(L, dtype=float)
    rho = np.asarray(rho, dtype=float)
    order = np.argsort(L)
    L = L[order]
    rho = rho[order]

    curve_type = _detect_curve_type(L, rho)
    contrast = float(np.max(rho) / max(float(np.min(rho)), 1e-3))
    n_layers = 2 if curve_type in {"DESC2", "ASC2"} else 3
    recommended_n_layers = n_layers
    if curve_type in {"Q", "DESC2"} and contrast > 80:
        n_layers = 2
        recommended_n_layers = 4 if contrast > 120 else 3
    elif contrast > 200:
        recommended_n_layers = max(n_layers, 4)
    smoothed = _smooth_curve(rho)

    rho_values = _segment_rho_values(L, rho, n_layers)
    if n_layers == 3:
        rho_values = _adjust_rho_for_curve_type(rho_values, curve_type, smoothed)
    elif n_layers == 2:
        rho_values = [max(0.1, float(smoothed[0])), max(0.1, float(smoothed[-1]))]
    elif n_layers >= 4:
        rho_values = _segment_rho_values(L, rho, n_layers)

    if n_layers == 2 and curve_type in {"Q", "DESC2"}:
        h_values = [_estimate_transition_thickness(L, rho)]
    else:
        h_values = _estimate_thicknesses(L, rho, n_layers)
    init_rmse, init_r2 = _metrics(L, rho, rho_values, h_values)

    notes: list[str] = []
    score = 1.0
    if len(L) < 5:
        score -= 0.25
        notes.append("Hay pocos puntos (< 5). El modelo inicial puede ser inestable.")
    if float(np.mean(np.diff(L) > 0)) < 0.8:
        score -= 0.35
        notes.append("L no crece de forma consistente. Revisa la columna AB/2.")
    if contrast > 80:
        notes.append(
            "Curva con contraste extremo (ρ máx/ρ mín > 80). "
            "El modelo 1D puede no reproducir todos los puntos; verifica columnas y usa búsqueda global."
        )
    if recommended_n_layers > n_layers:
        notes.append(
            f"Prueba con **{recommended_n_layers} capas** (botón en Modelo de Capas) "
            "para curvas de alto contraste."
        )
    if contrast > 500:
        notes.append("La curva abarca varios órdenes de magnitud; conviene usar búsqueda global.")
    if init_r2 < 0.0:
        score -= 0.35
        notes.append("El modelo inicial todavía no reproduce la forma de la curva medida.")
    elif init_r2 < 0.3:
        score -= 0.15
        notes.append("Coherencia inicial moderada: la optimización necesitará más exploración.")
    score = float(np.clip(score, 0.0, 1.0))

    mooney_key = MOONEY_KEYS.get(curve_type, MOONEY_KEYS["Q"])
    return ModelInitResult(
        n_layers=n_layers,
        rho=rho_values,
        h=h_values,
        curve_type=curve_type,
        mooney_key=mooney_key,
        coherence_score=score,
        init_rmse=init_rmse,
        init_r2=init_r2,
        use_global_search=score < 0.75 or init_r2 < 0.35,
        recommended_n_layers=recommended_n_layers,
        notes=notes,
    )


def resolve_initial_model(
    L: np.ndarray,
    rho: np.ndarray,
    *,
    auto_expand_layers: bool = True,
) -> ModelInitResult:
    """Inicializa el modelo; expande a más capas automáticamente en curvas difíciles."""
    base = estimate_initial_model(L, rho)
    if not auto_expand_layers:
        return base
    contrast = float(np.max(rho) / max(float(np.min(rho)), 1e-3))
    target = int(base.recommended_n_layers)
    if target > base.n_layers and (contrast > 120 or base.use_global_search):
        expanded = build_initial_model_for_layers(L, rho, target)
        expanded.notes.append(
            f"Inicialización automática con {target} capas (curva de alto contraste)."
        )
        return expanded
    return base


def build_initial_model_for_layers(L: np.ndarray, rho: np.ndarray, n_layers: int) -> ModelInitResult:
    """Construye un modelo inicial para un número de capas solicitado (p. ej. 4)."""
    base = estimate_initial_model(L, rho)
    n_layers = max(2, min(10, int(n_layers)))
    if n_layers == base.n_layers:
        return base

    L = np.asarray(L, dtype=float)
    rho = np.asarray(rho, dtype=float)
    order = np.argsort(L)
    L = L[order]
    rho = rho[order]
    smoothed = _smooth_curve(rho)

    if n_layers == 2:
        rho_values = [max(0.1, float(smoothed[0])), max(0.1, float(smoothed[-1]))]
        h_values = [_estimate_transition_thickness(L, rho)]
    elif n_layers == 3:
        rho_values = _adjust_rho_for_curve_type(
            _segment_rho_values(L, rho, 3), base.curve_type, smoothed
        )
        h_values = _estimate_thicknesses(L, rho, 3)
    else:
        rho_values = _segment_rho_values(L, rho, n_layers)
        h_values = _estimate_thicknesses(L, rho, n_layers)

    init_rmse, init_r2 = _metrics(L, rho, rho_values, h_values)
    return ModelInitResult(
        n_layers=n_layers,
        rho=rho_values,
        h=h_values,
        curve_type=base.curve_type,
        mooney_key=base.mooney_key,
        coherence_score=base.coherence_score,
        init_rmse=init_rmse,
        init_r2=init_r2,
        use_global_search=True,
        recommended_n_layers=n_layers,
        notes=list(base.notes),
    )


def build_data_signature(filename: str, col_l: str, col_rho: str) -> str:
    # v2: preferencia Ro_Calculados (ρₐ) frente a R_Medidas (Ω) en exportaciones telurómetro.
    return f"v2|{filename}|{col_l}|{col_rho}"


def build_manual_data_signature(text: str) -> str:
    import hashlib

    normalized = "\n".join(line.strip() for line in text.strip().splitlines() if line.strip())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"manual|{digest}"