import numpy as np

from core import calc_rho_a
from sev_import import parse_sev_file
from sev_metrics import assess_fit
from sev_report import build_sev_pdf_report


def test_pdf_report_generates_bytes():
    result = parse_sev_file(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/01.csv"
    )
    rho_layers = [184.7, 611.8, 132.1]
    h_layers = [1.8, 38.8]
    rho_calc = calc_rho_a(result.L_med, rho_layers, h_layers)
    fit = assess_fit(result.L_med, result.rho_med, rho_calc)
    pdf = build_sev_pdf_report(
        filename="01.csv",
        col_l=result.col_l,
        col_rho=result.col_rho,
        L_med=result.L_med,
        rho_med=result.rho_med,
        rho_calc=rho_calc,
        rho_layers=rho_layers,
        h_layers=h_layers,
        fit=fit,
        curve_type="K",
    )
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 5000