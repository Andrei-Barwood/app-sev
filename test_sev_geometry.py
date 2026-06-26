import pandas as pd

from sev_geometry import inspect_electrode_geometry


def test_inspect_geometry_04_csv():
    df = pd.read_csv(
        "/Users/andreibarwood/Documents/CFT/2026/01 - Semestre 1/02 - Taller de Energía/"
        "03 - Unidad 3 - Puesta a Tierra/Evaluación 4 - Unidad 3/tests/04.csv"
    )
    info = inspect_electrode_geometry(df, "DISTANCIA_AB_2")
    assert info is not None
    assert info["col_a"] == "a"
    assert abs(info["delta_l_minus_a_mean"] - 0.5) < 0.05
    assert any("DISTANCIA_AB_2" in msg for msg in info["messages"])