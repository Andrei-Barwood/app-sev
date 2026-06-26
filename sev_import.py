"""Lectura e interpretación de archivos SEV (CSV/Excel) para la app."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import BytesIO
from typing import BinaryIO

import numpy as np
import pandas as pd


@dataclass
class SevImportResult:
    L_med: np.ndarray
    rho_med: np.ndarray
    col_l: str
    col_rho: str
    df: pd.DataFrame
    detection_method: str
    warnings: list[str] = field(default_factory=list)
    suggested_col_l: str | None = None
    suggested_col_rho: str | None = None


@dataclass
class ColumnAssessment:
    level: str
    title: str
    message: str


def get_import_format_help() -> str:
    return """
**El archivo debe contener mediciones de un sondeo Schlumberger con al menos dos columnas numéricas:**

| Dato | Descripción | Unidad |
|------|-------------|--------|
| **L** | Semidistancia entre electrodos de corriente (**AB/2**) | metros (m) |
| **ρₐ** | Resistividad aparente **medida en campo** | ohm·m (Ω·m) |

**Formato aceptado**
- Primera fila con encabezados (recomendado) o solo números.
- Separadores: coma `,`, punto y coma `;` o tabulador (exportación desde Excel).
- Decimales con punto `1.5` o coma `1,5`.

**Nombres de columna reconocidos automáticamente**

- Para **L**: `L (AB/2)`, `DISTANCIA_AB_2`, `AB/2`, `Distancia`, etc.
- Para **ρ medida**: `Rho Medido`, `R_Medidas`, `R_Medida`, `Rho_med`, etc.

**Columnas que se ignoran** (si están presentes): número de lectura (`N_Lectura`),
valores calculados (`Ro_Calculados`, `Rho Calculado`), errores, parámetros `a` y `d`.

**Ejemplo mínimo válido**
```
L (AB/2) [m],Rho Medido [Ω·m]
1.5,168.4
2.0,170.8
3.0,201.2
```

**Ejemplo con exportación de telurómetro / IPI2Win** (como `04.csv`)
```
N_Lectura,DISTANCIA_AB_2,a,d,R_Medidas,Ro_Calculados
1,0.6,0.1,1,339,117.15
2,0.7,0.2,1,236.7,178.47
```
La app seleccionará `DISTANCIA_AB_2` como L y `R_Medidas` como ρ medida.
"""


def get_sev_transparency_help() -> str:
    return """
En un **sondeo eléctrico vertical (SEV)** cada fila válida representa una medición física:

1. Se amplía la separación entre electrodos de corriente hasta una distancia **L = AB/2** (metros).
2. En esa separación se mide la **resistividad aparente ρₐ** (Ω·m) con el telurómetro.

La curva del SEV es **ρₐ vs L** en escala log-log. El modelo de capas (Pekeris + filtro de Ghosh)
solo tiene sentido si usas exactamente esas dos magnitudes.

**Si eliges otras columnas**, por ejemplo `N_Lectura`, `a`, `d` o `Ro_Calculados`, no estás
cambiando "una preferencia": estás alimentando el algoritmo con variables que **no corresponden
al experimento**, y el ajuste matemático puede converger a un resultado **físicamente incorrecto**
aunque el gráfico "se vea bien".
"""


def get_column_role_hint(col_name: str) -> str:
    norm = _normalize_col(col_name)
    if _is_excluded_column(norm):
        if norm in {"a", "d"}:
            return "Parámetro de arreglo; no es L = AB/2."
        return "Índice o metadato; no es una magnitud del SEV."
    if _score_l_column(norm) >= 75:
        return "Candidata para L (AB/2)."
    if _score_rho_column(norm) >= 70:
        if any(x in norm for x in ("calculado", "calc", "teorico", "modelo", "ajust")):
            return "Valor modelado/calculado; no es ρ medida en campo."
        return "Candidata para ρₐ medida."
    if any(x in norm for x in ("calculado", "calc", "teorico", "modelo", "ajust")):
        return "Valor calculado por otro software; no sustituye la medición."
    if "error" in norm:
        return "Columna de error; no participa en el modelo."
    return "Columna numérica sin rol SEV claro; verifica antes de usarla."


def _looks_like_index_series(values: np.ndarray) -> bool:
    if len(values) < 3:
        return False
    diffs = np.diff(values)
    return bool(
        np.allclose(diffs, 1.0, atol=0.01)
        and abs(float(values[0]) - 1.0) < 0.01
        and np.allclose(values, np.round(values), atol=0.01)
    )


def assess_column_selection(
    col_l: str,
    col_rho: str,
    L: np.ndarray,
    rho: np.ndarray,
    suggested_col_l: str | None = None,
    suggested_col_rho: str | None = None,
) -> list[ColumnAssessment]:
    notes: list[ColumnAssessment] = []
    norm_l = _normalize_col(col_l)
    norm_rho = _normalize_col(col_rho)

    if col_l == col_rho:
        notes.append(
            ColumnAssessment(
                "error",
                "Misma columna para L y ρ",
                "L (AB/2) y ρₐ medida deben ser columnas distintas.",
            )
        )
        return notes

    if _is_excluded_column(norm_l) or _looks_like_index_series(L):
        notes.append(
            ColumnAssessment(
                "error",
                "L no representa AB/2",
                f"`{col_l}` parece un índice o parámetro auxiliar, no la semidistancia AB/2. "
                "El eje horizontal del SEV debe crecer con la expansión del arreglo Schlumberger.",
            )
        )

    if any(x in norm_rho for x in ("calculado", "calc", "teorico", "modelo", "ajust")):
        notes.append(
            ColumnAssessment(
                "error",
                "ρ calculada en lugar de medida",
                f"`{col_rho}` contiene valores modelados. El ajuste debe usar la resistividad "
                "**medida en campo**; de lo contrario comparas el modelo contra sí mismo.",
            )
        )

    if _is_excluded_column(norm_rho):
        notes.append(
            ColumnAssessment(
                "warning",
                "ρ desde columna auxiliar",
                f"`{col_rho}` no parece una resistividad medida. Confirma que sea ρₐ del telurómetro.",
            )
        )

    if _score_l_column(norm_l) == 0 and float(np.max(L)) <= 20.0 and _looks_like_index_series(L):
        notes.append(
            ColumnAssessment(
                "error",
                "Eje L incompatible con un SEV",
                "Los valores de L se comportan como un contador 1, 2, 3… Eso produce un gráfico "
                "incorrecto aunque la forma parezca razonable.",
            )
        )

    if suggested_col_l and suggested_col_rho:
        if col_l != suggested_col_l or col_rho != suggested_col_rho:
            notes.append(
                ColumnAssessment(
                    "info",
                    "Selección distinta a la sugerida",
                    f"La app sugiere L ← `{suggested_col_l}` y ρ ← `{suggested_col_rho}`. "
                    "Si cambiaste las columnas, valida el gráfico antes de optimizar.",
                )
            )
        elif not notes:
            notes.append(
                ColumnAssessment(
                    "success",
                    "Selección coherente con el SEV",
                    f"Usar `{col_l}` como L y `{col_rho}` como ρ medida es consistente con "
                    "el arreglo Schlumberger y el modelo de capas.",
                )
            )

    if len(L) >= 3 and float(np.mean(np.diff(L) > 0)) < 0.5:
        notes.append(
            ColumnAssessment(
                "warning",
                "L no es mayormente creciente",
                "En un SEV típico L aumenta en cada lectura. Si no ocurre, revisa la columna elegida.",
            )
        )

    return notes


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return _numeric_columns(df)


def build_colored_preview(df: pd.DataFrame, col_l: str, col_rho: str, max_rows: int = 12):
    preview = df.head(max_rows).copy()
    style_map = dict(preview_column_styles(df, col_l, col_rho))

    def _color_cols(column: pd.Series):
        return [style_map.get(column.name, "background-color: #f8f9fa; color: #6c757d;")] * len(column)

    return preview.style.apply(_color_cols, axis=0)


def preview_column_styles(df: pd.DataFrame, col_l: str, col_rho: str) -> list[tuple[str, str]]:
    styles: list[tuple[str, str]] = []
    for col in df.columns:
        if col == col_l:
            styles.append((col, "background-color: #d4edda; color: #155724;"))
        elif col == col_rho:
            styles.append((col, "background-color: #fff3cd; color: #856404;"))
        else:
            styles.append((col, "background-color: #f8f9fa; color: #6c757d;"))
    return styles


def _normalize_col(name: object) -> str:
    text = str(name).lower().strip()
    text = text.replace("ω", "o").replace("·", "")
    text = re.sub(r"[\[\]()%°]", "", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _to_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    cols: list[str] = []
    for col in df.columns:
        if _to_numeric_series(df[col]).notna().sum() > 0:
            cols.append(col)
    return cols


def _score_l_column(norm_name: str) -> int:
    rules = (
        (100, ("distancia_ab_2", "distancia_ab2")),
        (95, ("distancia_ab",)),
        (90, ("l_ab_2", "lab2")),
        (85, ("ab_2", "ab2")),
        (80, ("semidistancia",)),
        (75, ("distancia",)),
        (60, ("l_m",)),
        (50, ("^l$",)),
    )
    for score, tokens in rules:
        for token in tokens:
            if token.startswith("^"):
                if re.fullmatch(token[1:], norm_name):
                    return score
            elif token in norm_name:
                return score
    return 0


def _score_rho_column(norm_name: str) -> int:
    if any(x in norm_name for x in ("calculado", "calc", "teorico", "modelo", "ajust")):
        return 0
    if "error" in norm_name:
        return 0
    rules = (
        (100, ("r_medidas", "rho_medido", "ro_medidas")),
        (95, ("r_medida", "rho_medida")),
        (90, ("rho_med", "rho_a", "resistividad_aparente")),
        (80, ("resistividad",)),
        (70, ("rho", "ro")),
    )
    for score, tokens in rules:
        for token in tokens:
            if token in norm_name:
                return score
    return 0


def _is_excluded_column(norm_name: str) -> bool:
    excluded = (
        "n_lectura",
        "lectura",
        "indice",
        "index",
        "numero",
        "item",
        "punto",
        "id",
    )
    if norm_name in excluded:
        return True
    if norm_name in {"a", "d"}:
        return True
    if re.fullmatch(r"n\d*", norm_name):
        return True
    return False


def detect_l_rho_columns(
    df: pd.DataFrame,
    col_l: str | None = None,
    col_rho: str | None = None,
) -> tuple[str, str, str, list[str]]:
    """Devuelve (col_l, col_rho, método, advertencias)."""
    warnings: list[str] = []
    numeric_cols = _numeric_columns(df)
    if len(numeric_cols) < 2:
        raise ValueError("No se encontraron al menos dos columnas numéricas en el archivo.")

    if col_l and col_rho:
        if col_l not in df.columns or col_rho not in df.columns:
            raise ValueError("Las columnas seleccionadas no existen en el archivo.")
        return col_l, col_rho, "manual", warnings

    norm_map = {col: _normalize_col(col) for col in numeric_cols}

    l_candidates: list[tuple[int, str]] = []
    rho_candidates: list[tuple[int, str]] = []
    for col, norm in norm_map.items():
        if _is_excluded_column(norm):
            continue
        l_score = _score_l_column(norm)
        rho_score = _score_rho_column(norm)
        if l_score > 0:
            l_candidates.append((l_score, col))
        if rho_score > 0:
            rho_candidates.append((rho_score, col))

    if l_candidates and rho_candidates:
        l_candidates.sort(key=lambda item: item[0], reverse=True)
        rho_candidates.sort(key=lambda item: item[0], reverse=True)
        best_l = l_candidates[0][1]
        best_rho = next((col for _, col in rho_candidates if col != best_l), rho_candidates[0][1])
        if best_l == best_rho:
            raise ValueError("No se pudieron distinguir columnas distintas para L y ρ medida.")
        return best_l, best_rho, "encabezado", warnings

    if len(numeric_cols) == 2:
        warnings.append(
            "No se reconocieron encabezados claros. Se usaron las dos únicas columnas numéricas "
            f"({numeric_cols[0]} → L, {numeric_cols[1]} → ρ)."
        )
        return numeric_cols[0], numeric_cols[1], "dos_columnas", warnings

    # Heurística por comportamiento de los datos
    best_pair: tuple[str, str] | None = None
    best_score = -1.0
    for i, col_x in enumerate(numeric_cols):
        for col_y in numeric_cols[i + 1 :]:
            x = _to_numeric_series(df[col_x]).dropna().values
            y = _to_numeric_series(df[col_y]).dropna().values
            if len(x) < 3 or len(y) < 3:
                continue
            n = min(len(x), len(y))
            x = x[:n]
            y = y[:n]
            mono_x = float(np.mean(np.diff(x) > 0))
            mono_y = float(np.mean(np.diff(y) > 0))
            if mono_x >= mono_y:
                l_col, rho_col = col_x, col_y
                mono_l = mono_x
            else:
                l_col, rho_col = col_y, col_x
                mono_l = mono_y
            l_vals = _to_numeric_series(df[l_col]).dropna().values
            score = mono_l + min(float(np.max(l_vals)), 100.0) / 100.0
            if score > best_score:
                best_score = score
                best_pair = (l_col, rho_col)

    if best_pair:
        warnings.append(
            "El archivo tiene varias columnas numéricas sin encabezados reconocibles. "
            f"Se infirió L ← `{best_pair[0]}` y ρ ← `{best_pair[1]}` por tendencia de los datos. "
            "Verifica el gráfico o selecciona las columnas manualmente."
        )
        return best_pair[0], best_pair[1], "heuristica", warnings

    warnings.append(
        "No se reconocieron encabezados. Se usaron las dos primeras columnas numéricas; "
        "revisa que correspondan a L (AB/2) y ρ medida."
    )
    return numeric_cols[0], numeric_cols[1], "fallback", warnings


def _validate_series(L: np.ndarray, rho: np.ndarray) -> list[str]:
    warnings: list[str] = []
    if len(L) < 3:
        warnings.append("Hay menos de 3 puntos. El ajuste del modelo puede ser poco confiable.")
    if np.any(L <= 0):
        warnings.append("Existen valores de L ≤ 0. Solo se conservaron filas con L > 0.")
    if np.any(rho <= 0):
        warnings.append("Existen valores de ρ ≤ 0. Solo se conservaron filas con ρ > 0.")
    if len(L) >= 3 and float(np.mean(np.diff(L) > 0)) < 0.5:
        warnings.append(
            "L no aumenta de forma mayormente creciente. ¿Estás usando la columna correcta para AB/2?"
        )
    if float(np.max(L)) < 0.5:
        warnings.append("El valor máximo de L es muy pequeño (< 0.5 m). Confirma que L esté en metros.")
    if float(np.max(rho)) > 100000:
        warnings.append("Hay resistividades muy altas (> 100 000 Ω·m). Verifica unidades y columna ρ.")
    return warnings


def load_dataframe_from_upload(uploaded_file: BinaryIO, filename: str) -> pd.DataFrame:
    if filename.lower().endswith((".csv", ".txt")):
        try:
            df = pd.read_csv(uploaded_file, sep=r"[;\t]", engine="python")
            if df.shape[1] < 2:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=None, engine="python")
        except Exception:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=None, engine="python")
    else:
        df = pd.read_excel(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def parse_sev_upload(
    uploaded_file: BinaryIO,
    filename: str,
    col_l: str | None = None,
    col_rho: str | None = None,
) -> SevImportResult:
    df = load_dataframe_from_upload(uploaded_file, filename)
    suggested_l, suggested_rho, _, _ = detect_l_rho_columns(df)
    col_l_name, col_rho_name, method, detect_warnings = detect_l_rho_columns(df, col_l, col_rho)

    work = df[[col_l_name, col_rho_name]].copy()
    work[col_l_name] = _to_numeric_series(work[col_l_name])
    work[col_rho_name] = _to_numeric_series(work[col_rho_name])
    work = work.dropna(subset=[col_l_name, col_rho_name])
    work = work[(work[col_l_name] > 0) & (work[col_rho_name] > 0)]
    if work.empty:
        raise ValueError(
            f"No quedaron filas válidas usando `{col_l_name}` y `{col_rho_name}`. "
            "Revisa que ambas columnas tengan L y ρ medida en las mismas filas."
        )

    work = work.sort_values(col_l_name).reset_index(drop=True)
    L_med = work[col_l_name].to_numpy(dtype=float)
    rho_med = work[col_rho_name].to_numpy(dtype=float)

    warnings = list(detect_warnings)
    warnings.extend(_validate_series(L_med, rho_med))
    return SevImportResult(
        L_med=L_med,
        rho_med=rho_med,
        col_l=col_l_name,
        col_rho=col_rho_name,
        df=df,
        detection_method=method,
        warnings=warnings,
        suggested_col_l=suggested_l,
        suggested_col_rho=suggested_rho,
    )


def _find_column_by_tokens(df: pd.DataFrame, tokens: tuple[str, ...]) -> str | None:
    for col in df.columns:
        norm = _normalize_col(str(col))
        if any(token in norm for token in tokens):
            return str(col)
    return None


def extract_reference_benchmark(
    df: pd.DataFrame,
    col_l: str,
    col_rho: str,
    L_med: np.ndarray,
    rho_med: np.ndarray,
) -> dict | None:
    """Extrae benchmark del curso si el CSV trae columnas de referencia (p. ej. 01.csv)."""
    col_calc = _find_column_by_tokens(df, ("rho_calculado", "ro_calculado", "calculado"))
    col_err = _find_column_by_tokens(df, ("error",))
    if col_calc is None:
        return None

    work = df[[col_l, col_rho, col_calc]].copy()
    if col_err:
        work[col_err] = df[col_err]
    work[col_l] = _to_numeric_series(work[col_l])
    work[col_rho] = _to_numeric_series(work[col_rho])
    work[col_calc] = _to_numeric_series(work[col_calc])
    work = work.dropna(subset=[col_l, col_rho, col_calc])
    work = work[(work[col_l] > 0) & (work[col_rho] > 0) & (work[col_calc] > 0)]
    if work.empty:
        return None

    if col_err:
        work[col_err] = _to_numeric_series(work[col_err])
        ref_errors = work[col_err].to_numpy(dtype=float)
    else:
        ref_errors = np.abs((work[col_rho] - work[col_calc]) / work[col_rho]) * 100.0

    return {
        "col_calc": col_calc,
        "col_error": col_err,
        "mean_error_pct": float(np.mean(ref_errors)),
        "max_error_pct": float(np.max(ref_errors)),
        "n_over_5pct": int(np.sum(ref_errors > 5.0)),
        "n_points": int(len(ref_errors)),
        "rho_calc": work[col_calc].to_numpy(dtype=float),
        "errors_pct": ref_errors,
    }


@dataclass
class ManualParseResult:
    L_med: np.ndarray
    rho_med: np.ndarray
    warnings: list[str]
    format_detected: str
    n_lines_parsed: int


def _extract_numbers_from_line(line: str) -> list[float]:
    """Separa por comas/tabuladores (CSV) y convierte cada celda a número."""
    normalized = line.strip().replace("\t", ",").replace(";", ",")
    parts = [p.strip() for p in normalized.split(",") if p.strip()]
    values: list[float] = []
    for part in parts:
        token = part.replace(" ", "")
        if token.count(",") == 1 and token.count(".") == 0:
            token = token.replace(",", ".")
        try:
            values.append(float(token))
        except ValueError:
            nums = re.findall(r"[-+]?\d+(?:\.\d+)?", part)
            values.extend(float(n) for n in nums)
    return values


def _pick_l_rho_from_numbers(nums: list[float]) -> tuple[float, float, str]:
    if len(nums) < 2:
        raise ValueError("Se necesitan al menos dos números por línea.")

    if len(nums) == 2:
        return nums[0], nums[1], "dos_columnas"

    if len(nums) >= 5:
        # Formato telurómetro: N_Lectura, DISTANCIA_AB_2, a, d, R_Medidas, [Ro_Calculados]
        return nums[1], nums[4], "telurómetro_multicolumna"

    if len(nums) == 3:
        return nums[0], nums[1], "tres_columnas"

    return nums[0], nums[1], "dos_primeras_columnas"


def _validate_manual_curve(L: np.ndarray, rho: np.ndarray) -> list[str]:
    warnings: list[str] = []
    if len(L) < 2:
        return warnings

    order = np.argsort(L)
    Ls = L[order]
    rhos = rho[order]

    if np.any(np.diff(Ls) <= 0):
        warnings.append(
            "Hay valores de L repetidos o desordenados. Revisa que la primera columna sea AB/2 [m]."
        )

    lecture_like = len(L) >= 4 and np.allclose(Ls, np.arange(1, len(Ls) + 1), atol=0.01)
    if lecture_like and float(np.max(rhos)) < 20:
        warnings.append(
            "Los valores de L parecen números de lectura (1, 2, 3…) y ρ muy bajas. "
            "¿Pegaste filas completas del telurómetro? Usa solo **L, ρ** o deja que la app lea columnas 2 y 5."
        )

    log_rho = np.log10(np.maximum(rhos, 1e-6))
    log_l = np.log10(np.maximum(Ls, 1e-6))
    jumps = np.abs(np.diff(log_rho) / np.maximum(np.diff(log_l), 1e-6))
    if np.any(jumps > 8):
        warnings.append(
            "La curva tiene saltos muy abruptos entre puntos vecinos. "
            "Eso no es típico en SEV: suele indicar columnas mal elegidas al pegar datos."
        )

    if float(np.max(rhos) / max(float(np.min(rhos)), 1e-3)) > 50:
        ratios = rhos[1:] / np.maximum(rhos[:-1], 1e-6)
        if np.any(ratios > 3) and np.any(ratios < 1 / 3):
            warnings.append(
                "ρ sube y baja bruscamente al aumentar L. Una curva SEV real suele ser suave en escala log-log."
            )

    return warnings


def parse_manual_sev_text(text: str) -> ManualParseResult:
    """
    Interpreta texto manual SEV.
    Acepta:
      - Dos columnas: L, ρ
      - Filas de telurómetro pegadas: N, L, a, d, R_Medidas, ...
    """
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        raise ValueError("No hay líneas para interpretar.")

    parsed: list[tuple[float, float, str]] = []
    for line in lines:
        if line.lower().startswith(("l", "n", "dist", "ab")) and any(c.isalpha() for c in line[:6]):
            continue
        nums = _extract_numbers_from_line(line)
        if len(nums) < 2:
            continue
        L_val, rho_val, fmt = _pick_l_rho_from_numbers(nums)
        if L_val <= 0 or rho_val <= 0:
            continue
        parsed.append((L_val, rho_val, fmt))

    if not parsed:
        raise ValueError(
            "No se encontraron pares válidos L, ρ. Formato: `0.6, 339` por línea "
            "o pega filas completas del telurómetro (la app usará DISTANCIA_AB_2 y R_Medidas)."
        )

    formats = [p[2] for p in parsed]
    dominant_fmt = max(set(formats), key=formats.count)
    L_med = np.array([p[0] for p in parsed], dtype=float)
    rho_med = np.array([p[1] for p in parsed], dtype=float)

    warnings: list[str] = []
    if dominant_fmt == "telurómetro_multicolumna":
        warnings.append(
            "Detectado formato telurómetro (varias columnas). Se usaron **DISTANCIA_AB_2** (col. 2) "
            "y **R_Medidas** (col. 5), no el número de lectura."
        )
    warnings.extend(_validate_manual_curve(L_med, rho_med))

    order = np.argsort(L_med)
    return ManualParseResult(
        L_med=L_med[order],
        rho_med=rho_med[order],
        warnings=warnings,
        format_detected=dominant_fmt,
        n_lines_parsed=len(parsed),
    )


def parse_sev_file(path: str, col_l: str | None = None, col_rho: str | None = None) -> SevImportResult:
    with open(path, "rb") as fh:
        data = fh.read()
    buffer = BytesIO(data)
    return parse_sev_upload(buffer, path, col_l=col_l, col_rho=col_rho)