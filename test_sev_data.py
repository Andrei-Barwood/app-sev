import numpy as np

from sev_data import clear_active_dataset, get_active_L_rho, store_active_dataset


class _FakeSession(dict):
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


def test_active_dataset_is_single_source_for_plots():
    session = _FakeSession()
    L = np.array([0.6, 1.0, 10.0, 12.0])
    rho = np.array([339.0, 123.1, 0.79, 0.39])
    store_active_dataset(
        session,
        L,
        rho,
        source="Cargar archivo (CSV/Excel)",
        filename="05.csv",
        col_l="AB_2",
        col_rho="Resistividad_Aparente",
        df=None,
    )
    L_out, rho_out = get_active_L_rho(session)
    assert np.allclose(L_out, np.sort(L))
    assert np.allclose(rho_out[np.argsort(L)], rho[np.argsort(L)])
    assert session.sev_import_panel["L_med"][0] == L_out[0]
    assert session.sev_import_panel["rho_med"][0] == rho_out[0]
    clear_active_dataset(session)
    assert get_active_L_rho(session) == (None, None)