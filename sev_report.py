"""Generación de informe PDF del ajuste SEV."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

from sev_metrics import ACCEPTANCE_ERROR_PCT, FitReport


def _verdict_text(fit: FitReport) -> tuple[str, str]:
    if fit.accepted and fit.strict_accepted:
        return "ACEPTADO", "#1b5e20"
    if fit.accepted:
        return "ACEPTADO CON RESERVAS", "#e65100"
    return "RECHAZADO", "#b71c1c"


def build_sev_pdf_report(
    *,
    filename: str,
    col_l: str,
    col_rho: str,
    L_med: np.ndarray,
    rho_med: np.ndarray,
    rho_calc: np.ndarray,
    rho_layers: list[float],
    h_layers: list[float],
    fit: FitReport,
    curve_type: str = "",
    reference_note: str = "",
) -> bytes:
    buffer = BytesIO()
    verdict, verdict_color = _verdict_text(fit)

    with PdfPages(buffer) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.patch.set_facecolor("white")
        fig.text(0.5, 0.94, "Informe de Ajuste SEV", ha="center", fontsize=18, weight="bold")
        fig.text(0.5, 0.90, f"Archivo: {filename or '—'}", ha="center", fontsize=11)
        fig.text(0.5, 0.87, datetime.now().strftime("%Y-%m-%d %H:%M"), ha="center", fontsize=9, color="#555")

        fig.text(0.08, 0.80, f"VEREDICTO: {verdict}", fontsize=16, weight="bold", color=verdict_color)
        fig.text(
            0.08,
            0.75,
            f"Criterio: error promedio ≤ {ACCEPTANCE_ERROR_PCT:.0f} %",
            fontsize=10,
        )
        fig.text(0.08, 0.71, f"Columnas: L = `{col_l}` · ρ = `{col_rho}`", fontsize=10)
        if curve_type:
            fig.text(0.08, 0.67, f"Tipo de curva detectado: {curve_type}", fontsize=10)

        y = 0.60
        metrics = [
            ("Puntos", str(fit.n_points)),
            ("RMSE (Ω·m)", f"{fit.rmse_linear:.2f}"),
            ("R² (log)", f"{fit.r2_log:.4f}"),
            ("Error promedio (%)", f"{fit.mean_error_pct:.2f}"),
            ("Error máximo (%)", f"{fit.max_error_pct:.2f}"),
            ("Puntos > 5 %", f"{fit.n_over_threshold}/{fit.n_points}"),
        ]
        for label, value in metrics:
            fig.text(0.08, y, f"{label}: {value}", fontsize=10)
            y -= 0.035

        y -= 0.02
        fig.text(0.08, y, "Modelo de capas", fontsize=12, weight="bold")
        y -= 0.04
        for i, rho_v in enumerate(rho_layers):
            fig.text(0.10, y, f"ρ_{i + 1} = {rho_v:.4g} Ω·m", fontsize=10)
            y -= 0.03
        for i, h_v in enumerate(h_layers):
            fig.text(0.10, y, f"h_{i + 1} = {h_v:.4g} m", fontsize=10)
            y -= 0.03
        fig.text(0.10, y, f"h_{len(rho_layers)} = ∞", fontsize=10)

        if reference_note:
            fig.text(0.08, 0.18, reference_note, fontsize=9, color="#333", wrap=True)

        fig.text(
            0.08,
            0.08,
            "Generado por App SEV · Modelo 1D Mooney-Orellana / Ghosh",
            fontsize=8,
            color="#666",
        )
        plt.axis("off")
        pdf.savefig(fig)
        plt.close(fig)

        fig2, ax = plt.subplots(figsize=(8.27, 5.5))
        ax.loglog(L_med, rho_med, "o-", color="#FFB000", label="Datos medidos", markersize=6)
        ax.loglog(L_med, rho_calc, "s--", color="#485199", label="Modelo ajustado", markersize=5)
        ax.set_xlabel("L (AB/2) [m]")
        ax.set_ylabel("ρ aparente [Ω·m]")
        ax.set_title("Curva SEV — comparación medido vs modelo")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend()
        pdf.savefig(fig2)
        plt.close(fig2)

        fig3, ax3 = plt.subplots(figsize=(8.27, 6))
        ax3.axis("off")
        df_show = fit.results_df.head(20)
        cols = [c for c in df_show.columns if c != "Cumple ≤5%"]
        df_show = df_show[cols]
        table_data = [
            [f"{v:.2f}" if isinstance(v, (float, np.floating)) else str(v) for v in row]
            for row in df_show.values
        ]
        table = ax3.table(
            cellText=table_data,
            colLabels=cols,
            loc="center",
            cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.2)
        ax3.set_title("Tabla de errores (primeras filas)", pad=20)
        pdf.savefig(fig3)
        plt.close(fig3)

    buffer.seek(0)
    return buffer.getvalue()