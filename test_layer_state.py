class _FakeSession(dict):
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


def test_set_layer_model_invalidates_old_widget_keys():
    from layer_state import set_layer_model, widget_key

    session = _FakeSession(
        rho=[100.0, 50.0, 200.0],
        h=[2.0, 10.0],
        fixed_rho=[False, False, False],
        fixed_h=[False, False],
        n_layers=3,
        layer_widget_generation=0,
    )
    session["layer_rho_0_0"] = 999.0
    set_layer_model(session, [10.0, 100.0], [5.0])
    assert session.rho == [10.0, 100.0]
    assert session.n_layers == 2
    assert "layer_rho_0_0" not in session
    assert widget_key(session, "rho", 0).startswith("layer_rho_1_")


def test_sync_reads_widget_values():
    from layer_state import set_layer_model, sync_lists_from_widgets, widget_key

    session = _FakeSession(
        rho=[10.0, 100.0],
        h=[5.0],
        fixed_rho=[False, False],
        fixed_h=[False],
        n_layers=2,
        layer_widget_generation=1,
    )
    session[widget_key(session, "rho", 0)] = 25.0
    session[widget_key(session, "rho", 1)] = 75.0
    session[widget_key(session, "h", 0)] = 8.0
    session[widget_key(session, "frho", 0)] = True
    session[widget_key(session, "frho", 1)] = False
    session[widget_key(session, "fh", 0)] = True
    sync_lists_from_widgets(session, 2)
    assert session.rho == [25.0, 75.0]
    assert session.h == [8.0]
    assert session.fixed_rho == [True, False]
    assert session.fixed_h == [True]