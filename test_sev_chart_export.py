import numpy as np

from core import calc_rho_a
from sev_chart_export import build_sev_chart_pdf
from sev_import import parse_sev_file
from sev_metrics import log_axis_ticks


def test_chart_pdf_transparent_export():
    result = parse_sev_file(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/04.csv"
    )
    rho_layers = [120.0, 400.0, 180.0]
    h_layers = [1.0, 5.0]
    rho_calc = calc_rho_a(result.L_med, rho_layers, h_layers)
    L_smooth = np.logspace(np.log10(result.L_med.min()), np.log10(result.L_med.max()), 50)
    rho_smooth = calc_rho_a(L_smooth, rho_layers, h_layers)
    pdf = build_sev_chart_pdf(
        result.L_med,
        result.rho_med,
        L_smooth,
        rho_smooth,
        title="Curva SEV — 04.csv",
        measured_label="Datos medidos (04.csv)",
        x_ticks=log_axis_ticks(result.L_med),
        y_ticks=log_axis_ticks(np.concatenate([result.rho_med, rho_calc, rho_smooth])),
    )
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 2000