"""Exportación del gráfico SEV (solo curva) para presentaciones."""

from __future__ import annotations

from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np


def build_sev_chart_pdf(
    L_med: np.ndarray,
    rho_med: np.ndarray,
    L_smooth: np.ndarray,
    rho_smooth: np.ndarray,
    *,
    title: str,
    measured_label: str = "Datos medidos",
    marker_mode: str = "markers+lines",
    x_ticks: list[float] | None = None,
    y_ticks: list[float] | None = None,
    ref_L: np.ndarray | None = None,
    ref_rho: np.ndarray | None = None,
    ref_label: str | None = None,
) -> bytes:
    """Genera un PDF del gráfico log-log con fondo transparente."""
    L_med = np.asarray(L_med, dtype=float)
    rho_med = np.asarray(rho_med, dtype=float)
    L_smooth = np.asarray(L_smooth, dtype=float)
    rho_smooth = np.asarray(rho_smooth, dtype=float)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)

    if marker_mode == "markers":
        ax.loglog(
            L_med,
            rho_med,
            linestyle="none",
            marker="o",
            color="#FFB000",
            markeredgecolor="#63627C",
            markeredgewidth=0.8,
            markersize=7,
            label=measured_label,
            zorder=3,
        )
    else:
        ax.loglog(
            L_med,
            rho_med,
            marker="o",
            color="#FFB000",
            markeredgecolor="#63627C",
            markeredgewidth=0.8,
            markersize=7,
            linestyle=":",
            linewidth=1,
            label=measured_label,
            zorder=3,
        )

    ax.loglog(
        L_smooth,
        rho_smooth,
        color="#485199",
        linewidth=2.5,
        label="Modelo de capas (teórico)",
        zorder=2,
    )

    if ref_L is not None and ref_rho is not None:
        ref_L = np.asarray(ref_L, dtype=float)
        ref_rho = np.asarray(ref_rho, dtype=float)
        mask = np.isfinite(ref_rho) & (ref_rho > 0)
        if np.any(mask):
            ax.loglog(
                ref_L[mask],
                ref_rho[mask],
                color="#7B68A6",
                linestyle="--",
                linewidth=1,
                marker="D",
                markersize=5,
                label=ref_label or "Referencia CSV",
                zorder=1,
            )

    ax.set_title(title, color="#63627C", fontsize=13, pad=12)
    ax.set_xlabel("Distancia L (AB/2) [m]", color="#63627C")
    ax.set_ylabel("Resistividad Aparente [Ω·m]", color="#63627C")
    ax.tick_params(colors="#63627C", which="both")
    for spine in ax.spines.values():
        spine.set_color("#A7B7CF")

    if x_ticks:
        ax.set_xticks(x_ticks)
        ax.set_xticklabels([f"{t:g}" for t in x_ticks])
    if y_ticks:
        ax.set_yticks(y_ticks)
        ax.set_yticklabels([f"{t:g}" for t in y_ticks])

    ax.grid(True, which="both", color="#EAEEF4", alpha=0.85, linewidth=0.8)
    ax.legend(
        loc="upper right",
        framealpha=0.85,
        facecolor="white",
        edgecolor="#A7B7CF",
        fontsize=9,
    )

    buffer = BytesIO()
    fig.savefig(
        buffer,
        format="pdf",
        transparent=True,
        bbox_inches="tight",
        pad_inches=0.15,
    )
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()