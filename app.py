import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import json

from core import calc_rho_a
from optimizer import run_optimization
from malla_export import (
    build_malla_bt_payload,
    format_malla_bt_csv,
    format_malla_bt_csv_completo,
    format_malla_bt_json,
)
from sev_import import (
    assess_column_selection,
    build_colored_preview,
    detect_l_rho_columns,
    extract_reference_benchmark,
    get_column_role_hint,
    get_import_format_help,
    get_sev_transparency_help,
    load_dataframe_from_upload,
    numeric_columns,
    parse_manual_sev_text,
    parse_sev_upload,
)
from sev_feasibility import assess_feasibility
from model_init import build_data_signature, build_initial_model_for_layers, estimate_initial_model
from sev_geometry import inspect_electrode_geometry
from sev_report import build_sev_pdf_report
from sev_data import clear_active_dataset, get_active_dataset, get_active_L_rho, store_active_dataset
from sev_metrics import (
    ACCEPTANCE_ERROR_PCT,
    assess_fit,
    log_axis_ticks,
    style_results_table,
)
from layer_state import (
    apply_model_init_to_session,
    bump_layer_widget_generation,
    extend_layers_from_data,
    read_layer_model_from_widgets,
    set_layer_model,
    sync_lists_from_widgets,
    widget_key,
    ensure_layer_lengths,
)

st.set_page_config(page_title="App SEV", page_icon="⚡", layout="wide")

st.title("Sondeo Eléctrico Vertical (SEV)")
st.markdown("Modelado y ajuste de curvas de resistividad aparente (Mooney-Orellana / Filtro Digital 1D)")

# === VARIABLES DE SESION ===
MOONEY_ORELLANA_REF = {
    "Personalizado": None,
    "2 Capas - Ascendente": {"rho": [10.0, 100.0], "h": [5.0]},
    "2 Capas - Descendente": {"rho": [100.0, 10.0], "h": [5.0]},
    "3 Capas - Tipo H (Mínimo) ρ1>ρ2<ρ3": {"rho": [100.0, 10.0, 100.0], "h": [2.0, 10.0]},
    "3 Capas - Tipo K (Máximo) ρ1<ρ2>ρ3": {"rho": [10.0, 100.0, 10.0], "h": [2.0, 10.0]},
    "3 Capas - Tipo A (Ascendente) ρ1<ρ2<ρ3": {"rho": [10.0, 50.0, 200.0], "h": [2.0, 10.0]},
    "3 Capas - Tipo Q (Descendente) ρ1>ρ2>ρ3": {"rho": [200.0, 50.0, 10.0], "h": [2.0, 10.0]}
}

if 'rho' not in st.session_state:
    st.session_state.rho = [100.0, 50.0, 200.0]
if 'h' not in st.session_state:
    st.session_state.h = [2.0, 10.0]
if 'fixed_rho' not in st.session_state:
    st.session_state.fixed_rho = [False, False, False]
if 'fixed_h' not in st.session_state:
    st.session_state.fixed_h = [False, False]
if 'n_layers' not in st.session_state:
    st.session_state.n_layers = len(st.session_state.rho)
if 'layer_widget_generation' not in st.session_state:
    st.session_state.layer_widget_generation = 0

# === SIDEBAR Y NAVEGACIÓN ===
with st.sidebar:
    nav = st.radio("Navegación", ["📚 Tutorial y Guía de Uso", "⚡ Herramienta SEV", "🏗️ Diseño Malla BT y Reporte"])
    st.markdown("---")

if nav == "📚 Tutorial y Guía de Uso":
    st.header("Tutorial de Mediciones de Tierra y Uso de la Aplicación")
    st.markdown("""
    Bienvenido a la herramienta profesional para **Sondeo Eléctrico Vertical (SEV)**. Esta guía te enseñará cómo realizar las mediciones en campo y cómo utilizar cada función de esta aplicación para interpretar tus datos.

    ---

    ### 📍 1. ¿Cómo realizar una medición SEV en campo?
    El Sondeo Eléctrico Vertical busca determinar la resistividad del subsuelo a diferentes profundidades. El arreglo más común es el **Schlumberger**:
    1. **Configuración de Electrodos:** Se clavan 4 electrodos alineados en el suelo. Los dos exteriores (A y B) inyectan corriente, y los dos interiores (M y N) miden la diferencia de potencial.
    2. **Expansión:** Para investigar a mayor profundidad, se aumenta progresivamente la distancia entre los electrodos de corriente (A y B), manteniendo L = AB/2.
    3. **Toma de Datos:** Para cada separación L, se anota la resistividad aparente $\\rho_a$ medida por el telurómetro.

    ---

    ### 💻 2. Guía paso a paso de la Aplicación

    #### Paso 1: Ingresar Datos
    En la barra lateral izquierda, selecciona tu "Fuente de datos":
    - **Cargar archivo:** Sube un CSV o Excel con al menos **L (AB/2)** y **ρ medida**. La app reconoce encabezados como `DISTANCIA_AB_2`, `R_Medidas`, `Rho Medido`, etc. Abre **¿Qué debe traer el archivo?** para ver el formato completo.
    - **Ingreso manual:** Escribe tus puntos medidos directamente en la caja de texto.
    - **Generar teóricos:** Útil si solo deseas simular cómo se vería la curva de un terreno hipotético sin datos de campo.

    #### Paso 2: Seleccionar Curva de Referencia (Opcional)
    Si no sabes qué valores iniciales darle a tu modelo, usa el menú **Curvas de Referencia (Mooney-Orellana)**. Escoge un perfil típico (por ejemplo, Tipo H donde la capa intermedia es muy conductora) y la app cargará valores de referencia automáticamente.

    #### Paso 3: Configurar Modelo de Capas
    Define el **Número de capas** que intuyes que tiene el terreno (entre 2 y 10). Para cada capa, puedes modificar su resistividad ($\\rho$) y su espesor ($h$).
    - Si conoces el valor exacto de una capa (por ejemplo, por una perforación previa), marca la casilla **"Fijar"** para que el algoritmo no la modifique durante la optimización.

    #### Paso 4: Optimización Automática
    Haz clic en el botón azul **"Ajustar automáticamente"**. 
    La aplicación utilizará un algoritmo avanzado en dos pasos (*Evolución Diferencial* + *Mínimos Cuadrados*) para encontrar la combinación perfecta de resistividades y espesores que mejor se adapte a tus datos de campo.

    #### Paso 5: Analizar y Exportar
    - Observa el **Gráfico Principal** (escala log-log) para verificar visualmente el ajuste entre tus puntos (amarillos) y la curva teórica (línea azul oscuro).
    - Revisa la **Sección Geoeléctrica** debajo para ver un perfil de cómo está estructurado tu terreno.
    - Utiliza los botones de **Exportar Resultados** para descargar tu tabla de errores en Excel/CSV o guardar el modelo en formato JSON para uso futuro.
    """)

elif nav == "⚡ Herramienta SEV":
    with st.sidebar:
        st.header("1. Datos de Entrada")
        data_source = st.radio("Fuente de datos:", ["Cargar archivo (CSV/Excel)", "Generar teóricos", "Ingreso manual"])
        if st.session_state.get("sev_data_source") != data_source:
            clear_active_dataset(st.session_state)
            st.session_state.sev_data_source = data_source

        if data_source == "Generar teóricos":
            l_min = st.number_input("L inicial (m)", min_value=0.1, value=1.0)
            l_max = st.number_input("L final (m)", min_value=1.0, value=1000.0)
            pts_dec = st.number_input("Puntos por década", min_value=3, value=10)
            decades = np.log10(l_max) - np.log10(l_min)
            num_pts = int(decades * pts_dec) + 1
            L_teo = np.logspace(np.log10(l_min), np.log10(l_max), num_pts)
            rho_teo = calc_rho_a(L_teo, st.session_state.rho, st.session_state.h)
            store_active_dataset(
                st.session_state,
                L_teo,
                rho_teo,
                source=data_source,
            )
        elif data_source == "Cargar archivo (CSV/Excel)":
            with st.expander("¿Qué debe traer el archivo?", expanded=False):
                st.markdown(get_import_format_help())

            uploaded_file = st.file_uploader("Sube tu archivo", type=['csv', 'txt', 'xlsx', 'xls'])
            if uploaded_file is not None:
                try:
                    uploaded_file.seek(0)
                    df_upload = load_dataframe_from_upload(uploaded_file, uploaded_file.name)
                    numeric_options = numeric_columns(df_upload)
                    if len(numeric_options) < 2:
                        raise ValueError("El archivo debe tener al menos dos columnas numéricas.")

                    suggested_l, suggested_rho, _, _ = detect_l_rho_columns(df_upload)
                    l_index = numeric_options.index(suggested_l) if suggested_l in numeric_options else 0
                    rho_index = (
                        numeric_options.index(suggested_rho)
                        if suggested_rho in numeric_options
                        else min(1, len(numeric_options) - 1)
                    )

                    st.caption("Elige qué columnas representan el experimento SEV. Verde = L (AB/2), amarillo = ρ medida.")
                    pick1, pick2 = st.columns(2)
                    with pick1:
                        col_l_selected = st.selectbox(
                            "Eje L — AB/2 [m]",
                            numeric_options,
                            index=l_index,
                            key=f"col_l_{uploaded_file.name}",
                            help=get_column_role_hint(suggested_l),
                        )
                    with pick2:
                        col_rho_selected = st.selectbox(
                            "Eje ρ — medida en campo [Ω·m]",
                            numeric_options,
                            index=rho_index,
                            key=f"col_rho_{uploaded_file.name}",
                            help=get_column_role_hint(suggested_rho),
                        )

                    uploaded_file.seek(0)
                    import_result = parse_sev_upload(
                        uploaded_file,
                        uploaded_file.name,
                        col_l=col_l_selected,
                        col_rho=col_rho_selected,
                    )
                    assessments = assess_column_selection(
                        import_result.col_l,
                        import_result.col_rho,
                        import_result.L_med,
                        import_result.rho_med,
                        import_result.suggested_col_l,
                        import_result.suggested_col_rho,
                    )

                    L_med, rho_med = import_result.L_med, import_result.rho_med
                    feasibility = (
                        assess_feasibility(L_med, rho_med)
                        if not any(item.level == "error" for item in assessments)
                        else None
                    )
                    reference_benchmark = extract_reference_benchmark(
                        import_result.df,
                        import_result.col_l,
                        import_result.col_rho,
                        L_med,
                        rho_med,
                    )
                    store_active_dataset(
                        st.session_state,
                        L_med,
                        rho_med,
                        source=data_source,
                        filename=uploaded_file.name,
                        col_l=import_result.col_l,
                        col_rho=import_result.col_rho,
                        df=import_result.df,
                        assessments=assessments,
                        feasibility=feasibility,
                        reference_benchmark=reference_benchmark,
                    )
                    L_med, rho_med = get_active_L_rho(st.session_state)

                    for item in assessments:
                        if item.level == "success":
                            st.success(f"**{item.title}:** {item.message}")
                        elif item.level == "error":
                            st.error(f"**{item.title}:** {item.message}")
                        elif item.level == "warning":
                            st.warning(f"**{item.title}:** {item.message}")
                        else:
                            st.info(f"**{item.title}:** {item.message}")

                    for warning in import_result.warnings:
                        st.warning(warning)

                    geometry = inspect_electrode_geometry(import_result.df, import_result.col_l)
                    if geometry:
                        for msg in geometry.get("messages", []):
                            st.info(f"**Geometría de electrodos:** {msg}")

                    data_signature = build_data_signature(
                        uploaded_file.name,
                        import_result.col_l,
                        import_result.col_rho,
                    )
                    has_column_errors = any(item.level == "error" for item in assessments)
                    if st.session_state.get("sev_data_signature") != data_signature:
                        st.session_state["sev_data_signature"] = data_signature
                        if not has_column_errors:
                            model_init = estimate_initial_model(L_med, rho_med)
                            apply_model_init_to_session(model_init, st.session_state)
                            st.session_state["auto_optimize_global"] = model_init.use_global_search
                        else:
                            st.session_state.pop("model_init_report", None)
                except Exception as e:
                    clear_active_dataset(st.session_state)
                    st.error(f"Error al leer el archivo: {e}")
            else:
                active = get_active_dataset(st.session_state)
                if active and active.get("source") == data_source:
                    st.info(
                        f"Datos activos en memoria: **{active.get('filename', 'archivo')}** "
                        f"({active['n_points']} puntos) · L=`{active.get('col_l', '')}` · "
                        f"ρ=`{active.get('col_rho', '')}`"
                    )
                    L_med, rho_med = get_active_L_rho(st.session_state)
                else:
                    clear_active_dataset(st.session_state)
                    L_med, rho_med = None, None
        elif data_source == "Ingreso manual":
            st.caption(
                "Una línea = un punto. Formato simple: `L, ρ` (ej. `0.6, 339`). "
                "También puedes pegar filas completas del telurómetro; la app tomará DISTANCIA_AB/2 y R_Medidas."
            )
            manual_default = (
                "0.6, 339\n0.7, 236.7\n1, 123.1\n2, 31.6\n3, 14.95\n"
                "5, 4.77\n10, 0.79\n12, 0.39"
            )
            manual_data = st.text_area("Datos", manual_default, height=180)
            try:
                manual_result = parse_manual_sev_text(manual_data)
                for warning in manual_result.warnings:
                    st.warning(warning)
                st.caption(
                    f"Interpretado: {manual_result.n_lines_parsed} puntos "
                    f"({manual_result.format_detected})."
                )
                store_active_dataset(
                    st.session_state,
                    manual_result.L_med,
                    manual_result.rho_med,
                    source=data_source,
                )
                manual_sig = f"manual|{manual_result.n_lines_parsed}|{manual_result.format_detected}|{float(manual_result.L_med[0])}"
                if st.session_state.get("sev_data_signature") != manual_sig:
                    st.session_state["sev_data_signature"] = manual_sig
                    model_init = estimate_initial_model(
                        manual_result.L_med, manual_result.rho_med
                    )
                    apply_model_init_to_session(model_init, st.session_state)
                    st.session_state["auto_optimize_global"] = model_init.use_global_search
            except Exception as e:
                clear_active_dataset(st.session_state)
                st.error(f"Error en datos manuales: {e}")

        L_med, rho_med = get_active_L_rho(st.session_state)

        st.header("2. Curvas de Referencia (Mooney-Orellana)")
        
        suggested_index = 0
        if rho_med is not None and len(rho_med) >= 3:
            model_report = st.session_state.get("model_init_report")
            if model_report and model_report.get("mooney_key") in MOONEY_ORELLANA_REF:
                suggested_index = list(MOONEY_ORELLANA_REF.keys()).index(model_report["mooney_key"])
                st.info(
                    f"💡 **Detector de coherencia:** curva tipo **{model_report['curve_type']}** "
                    f"({model_report['mooney_key'].split(' - ', 1)[-1]}). "
                    f"Coherencia {model_report['coherence_score']:.0%}."
                )
            elif len(rho_med) >= 4:
                init_preview = estimate_initial_model(np.asarray(L_med), np.asarray(rho_med))
                suggested_index = list(MOONEY_ORELLANA_REF.keys()).index(init_preview.mooney_key)
                st.info(
                    f"💡 **Sugerencia:** la forma de tus datos se parece a **{init_preview.mooney_key.split(' - ', 1)[-1]}**."
                )

        ref_choice = st.selectbox("Seleccionar modelo base:", list(MOONEY_ORELLANA_REF.keys()), index=suggested_index)
        if st.button("Cargar Curva de Referencia", key="btn_load_ref_curve"):
            if ref_choice != "Personalizado":
                ref = MOONEY_ORELLANA_REF[ref_choice]
                set_layer_model(
                    st.session_state,
                    ref["rho"].copy(),
                    ref["h"].copy(),
                )
                st.session_state.pop("model_init_report", None)
                st.rerun()
            else:
                st.warning("Selecciona un modelo Mooney-Orellana distinto de Personalizado.")
        st.header("3. Modelo de Capas")
        if (
            data_source == "Cargar archivo (CSV/Excel)"
            and rho_med is not None
            and len(rho_med) >= 3
        ):
            recalc_cols = st.columns([2, 1])
            with recalc_cols[0]:
                if st.session_state.get("model_init_report"):
                    report = st.session_state["model_init_report"]
                    st.caption(
                        f"Inicialización desde datos: R² inicial {report['init_r2']:.3f} | "
                        f"RMSE inicial {report['init_rmse']:.2f} Ω·m"
                    )
                    for note in report.get("notes", []):
                        st.caption(f"• {note}")
            with recalc_cols[1]:
                if st.button("Recalcular desde CSV", key="btn_recalc_csv", help="Vuelve a estimar ρ y h a partir de la tabla importada"):
                    model_init = estimate_initial_model(np.asarray(L_med), np.asarray(rho_med))
                    apply_model_init_to_session(model_init, st.session_state)
                    st.session_state["auto_optimize_global"] = model_init.use_global_search
                    st.rerun()

        model_report = st.session_state.get("model_init_report", {})
        recommended_layers = int(model_report.get("recommended_n_layers", st.session_state.n_layers))
        feasibility_panel = (
            st.session_state.get("sev_import_panel", {}).get("feasibility")
            if st.session_state.get("sev_import_panel")
            else None
        )
        if feasibility_panel is not None:
            recommended_layers = max(recommended_layers, int(feasibility_panel.suggested_n_layers))
        if (
            recommended_layers > int(st.session_state.n_layers)
            and rho_med is not None
            and len(rho_med) >= 3
        ):
            if st.button(
                f"Probar con {recommended_layers} capas (curva difícil)",
                key="btn_use_recommended_layers",
                help="Inicializa el modelo con más capas para datos de alto contraste.",
            ):
                model_init = build_initial_model_for_layers(
                    np.asarray(L_med), np.asarray(rho_med), recommended_layers
                )
                apply_model_init_to_session(model_init, st.session_state)
                st.session_state["auto_optimize_global"] = True
                st.rerun()

        ensure_layer_lengths(st.session_state, int(st.session_state.n_layers))
        n_layers = st.number_input(
            "Número de capas",
            min_value=2,
            max_value=10,
            value=int(st.session_state.n_layers),
            key=widget_key(st.session_state, "n", 0),
        )
        n_layers = int(n_layers)
        if n_layers != int(st.session_state.n_layers):
            st.session_state.n_layers = n_layers
            if n_layers > len(st.session_state.rho):
                extend_layers_from_data(
                    st.session_state,
                    n_layers,
                    np.asarray(L_med) if L_med is not None else None,
                    np.asarray(rho_med) if rho_med is not None else None,
                )
            else:
                st.session_state.rho = st.session_state.rho[:n_layers]
                st.session_state.h = st.session_state.h[: n_layers - 1]
                st.session_state.fixed_rho = st.session_state.fixed_rho[:n_layers]
                st.session_state.fixed_h = st.session_state.fixed_h[: n_layers - 1]
            ensure_layer_lengths(st.session_state, n_layers)
            bump_layer_widget_generation(st.session_state)
            st.rerun()

        st.markdown("---")
        for i in range(n_layers):
            st.write(f"**Capa {i+1}**")
            col1, col2 = st.columns(2)
            with col1:
                st.number_input(
                    f"ρ_{i+1} (Ω·m)",
                    min_value=0.01,
                    value=max(0.01, float(st.session_state.rho[i])),
                    format="%.3f",
                    key=widget_key(st.session_state, "rho", i),
                )
                st.checkbox(
                    "Fijar ρ",
                    value=bool(st.session_state.fixed_rho[i]),
                    key=widget_key(st.session_state, "frho", i),
                )
            with col2:
                if i < n_layers - 1:
                    st.number_input(
                        f"h_{i+1} (m)",
                        min_value=0.001,
                        value=max(0.001, float(st.session_state.h[i])),
                        format="%.4f",
                        key=widget_key(st.session_state, "h", i),
                    )
                    st.checkbox(
                        "Fijar h",
                        value=bool(st.session_state.fixed_h[i]),
                        key=widget_key(st.session_state, "fh", i),
                    )
                else:
                    st.write("h = ∞")

        sync_lists_from_widgets(st.session_state, n_layers)

        st.header("4. Optimización")
        difficult_curve = bool(st.session_state.get("model_init_report", {}).get("use_global_search"))
        if difficult_curve:
            st.info(
                "Curva difícil detectada: se recomienda **Búsqueda Global** "
                "(contraste alto o forma compleja en los datos importados)."
            )
        opt_method = st.radio(
            "Método de Ajuste:",
            ["Refinamiento Local (Recomendado)", "Búsqueda Global (Automático)"],
            index=1 if difficult_curve else 0,
            key="opt_method_radio",
            help="El Refinamiento Local usa los valores actuales del modelo de capas. La Búsqueda Global explora un rango más amplio.",
        )
        run_opt = st.button("Ajustar", type="primary", key="btn_run_opt")
            
        if 'opt_success_msg' in st.session_state:
            st.success(st.session_state['opt_success_msg'])
            del st.session_state['opt_success_msg']
        if 'opt_rejected_msg' in st.session_state:
            st.error(st.session_state['opt_rejected_msg'])
            del st.session_state['opt_rejected_msg']
        if 'opt_error_msg' in st.session_state:
            st.error(st.session_state['opt_error_msg'])
            del st.session_state['opt_error_msg']
        if st.session_state.pop('opt_fit_warning', False):
            st.warning(
                "El modelo 1D no alcanzó el criterio de aceptación (≤5 % en todos los puntos). "
                "Revisa columnas, número de capas o la calidad de las mediciones en campo."
            )
            
        st.markdown("---")
        st.markdown(
            "<div style='text-align: center; color: #63627C; font-size: 0.9em;'>"
            "<strong>Desarrollo:</strong> Kirtan Teg Singh (ਕੀਰਤਨ ਤੇਗ ਸਿੰਘ)<br>"
            "<strong>Propietario:</strong> snocomm<br>"
            "<span style='color: red; font-weight: bold;'>⚠️ PROHIBIDA SU VENTA</span>"
            "</div>", 
            unsafe_allow_html=True
        )
    # === CALCULOS ===
    active_dataset = get_active_dataset(st.session_state)
    if active_dataset is None:
        st.warning("Por favor ingresa datos de L para continuar.")
        st.stop()

    L_med = active_dataset["L_med"]
    rho_med = active_dataset["rho_med"]
    data_source = active_dataset.get("source", data_source)
    model_report = st.session_state.get("model_init_report", {})

    if data_source == "Cargar archivo (CSV/Excel)" and st.session_state.get("sev_import_panel"):
        panel = st.session_state["sev_import_panel"]
        st.subheader("Importación transparente del archivo")
        st.markdown(get_sev_transparency_help())

        meta1, meta2, meta3, meta4 = st.columns(4)
        meta1.metric("Archivo", panel["filename"])
        meta2.metric("Puntos válidos", panel["n_points"])
        meta3.metric("Columnas activas", f"L: `{panel['col_l']}` · ρ: `{panel['col_rho']}`")
        meta4.metric(
            "ρ medida (max → min)",
            f"{float(np.max(rho_med)):.2g} → {float(np.min(rho_med)):.2g} Ω·m",
        )

        st.caption(
            "Las columnas resaltadas en la tabla alimentan el gráfico y la optimización. "
            "No hay una segunda curva oculta: el gráfico único de abajo usa exactamente estos datos."
        )

        feasibility = panel.get("feasibility")
        if feasibility is not None:
            if feasibility.level == "success":
                st.success(f"**{feasibility.title}:** {feasibility.message}")
            elif feasibility.level == "error":
                st.error(f"**{feasibility.title}:** {feasibility.message}")
            else:
                st.warning(f"**{feasibility.title}:** {feasibility.message}")

        ref_bench = panel.get("reference_benchmark")
        if ref_bench is not None:
            st.info(
                f"**Referencia del archivo** (`{ref_bench['col_calc']}`): error prom. "
                f"{ref_bench['mean_error_pct']:.2f} %, máx {ref_bench['max_error_pct']:.2f} % "
                f"({ref_bench['n_over_5pct']}/{ref_bench['n_points']} puntos > 5 %). "
                "Esa es la mejor curva documentada en el CSV del curso; tu optimización debería acercarse."
            )

        legend1, legend2, legend3 = st.columns(3)
        legend1.markdown("🟩 **Verde** → L (AB/2)")
        legend2.markdown("🟨 **Amarillo** → ρ medida")
        legend3.markdown("⬜ **Gris** → no usadas en el SEV")

        st.dataframe(
            build_colored_preview(panel["df"], panel["col_l"], panel["col_rho"]),
            width="stretch",
        )

        with st.expander("Guía de columnas detectadas en el archivo"):
            hint_rows = [
                {"Columna": col, "Rol sugerido": get_column_role_hint(col)}
                for col in panel["df"].columns
            ]
            st.dataframe(pd.DataFrame(hint_rows), width="stretch", hide_index=True)

        st.markdown("---")

    if run_opt:
        with st.spinner("Optimizando modelo... (esto puede tardar unos segundos)"):
            try:
                use_global = (
                    opt_method == "Búsqueda Global (Automático)"
                    or st.session_state.get("auto_optimize_global", False)
                )
                st.session_state["auto_optimize_global"] = False
                opt_rho, opt_h, opt_fixed_rho, opt_fixed_h = read_layer_model_from_widgets(
                    st.session_state, int(st.session_state.n_layers)
                )
                best_rho, best_h, rmse, r2 = run_optimization(
                    L_med,
                    rho_med,
                    opt_rho,
                    opt_h,
                    opt_fixed_rho,
                    opt_fixed_h,
                    use_global=use_global,
                    try_alternate_layers=True,
                )
                n_best = len(best_rho)
                set_layer_model(
                    st.session_state,
                    best_rho,
                    best_h,
                    fixed_rho=[False] * n_best,
                    fixed_h=[False] * max(n_best - 1, 0),
                )
                rho_opt = calc_rho_a(L_med, best_rho, best_h)
                fit = assess_fit(L_med, rho_med, rho_opt)
                st.session_state["last_fit_report"] = {
                    "accepted": fit.accepted,
                    "mean_error_pct": fit.mean_error_pct,
                    "max_error_pct": fit.max_error_pct,
                    "n_over_threshold": fit.n_over_threshold,
                    "n_points": fit.n_points,
                    "r2_log": fit.r2_log,
                    "rmse_linear": fit.rmse_linear,
                    "n_layers": n_best,
                }
                summary = (
                    f"{n_best} capas · RMSE {fit.rmse_linear:.2f} Ω·m · "
                    f"R²(log) {fit.r2_log:.4f} · Error prom. {fit.mean_error_pct:.2f} % · "
                    f"Máx {fit.max_error_pct:.2f} %"
                )
                if fit.accepted and fit.strict_accepted:
                    st.session_state["opt_success_msg"] = (
                        f"Ajuste ACEPTADO (promedio y todos los puntos ≤ {ACCEPTANCE_ERROR_PCT:.0f} %). {summary}"
                    )
                elif fit.accepted:
                    st.session_state["opt_success_msg"] = (
                        f"Ajuste ACEPTADO con reservas: promedio ≤ {ACCEPTANCE_ERROR_PCT:.0f} %, "
                        f"pero {fit.n_over_threshold} punto(s) lo superan. {summary}"
                    )
                    st.session_state["opt_fit_warning"] = True
                else:
                    st.session_state["opt_rejected_msg"] = (
                        f"Ajuste RECHAZADO: error promedio {fit.mean_error_pct:.2f} % "
                        f"> {ACCEPTANCE_ERROR_PCT:.0f} % permitido. {summary}"
                    )
                    st.session_state["opt_fit_warning"] = True
                st.rerun()
            except Exception as e:
                st.session_state['opt_error_msg'] = f"Error en la optimización: {e}"
                st.rerun()
    # Calcular curva teórica con los parámetros actuales
    rho_calc = calc_rho_a(L_med, st.session_state.rho, st.session_state.h)
    # === PLOT (único gráfico: datos medidos + modelo de capas) ===
    fig = go.Figure()
    if data_source != "Generar teóricos":
        measured_label = "Datos medidos"
        if data_source == "Cargar archivo (CSV/Excel)" and active_dataset.get("filename"):
            measured_label = f"Datos medidos ({active_dataset['filename']})"
        fig.add_trace(go.Scatter(
            x=L_med, y=rho_med,
            mode="markers+lines",
            name=measured_label,
            marker=dict(color="#FFB000", size=9, line=dict(color="#63627C", width=1)),
            line=dict(color="#A7B7CF", width=1, dash="dot"),
        ))
    L_smooth = np.logspace(np.log10(min(L_med)), np.log10(max(L_med)), 100)
    rho_smooth = calc_rho_a(L_smooth, st.session_state.rho, st.session_state.h)
    fig.add_trace(go.Scatter(
        x=L_smooth, y=rho_smooth,
        mode='lines',
        name='Modelo de capas (teórico)',
        line=dict(color='#485199', width=3)
    ))
    chart_title = "Curva de Sondeo Eléctrico Vertical"
    if data_source == "Cargar archivo (CSV/Excel)" and active_dataset.get("filename"):
        chart_title = f"Curva SEV — {active_dataset['filename']}"
    x_ticks = log_axis_ticks(L_med)
    y_ticks = log_axis_ticks(np.concatenate([rho_med, rho_calc, rho_smooth]))
    fig.update_layout(
        title=chart_title,
        xaxis_title='Distancia L (AB/2) [m]',
        yaxis_title='Resistividad Aparente [Ω·m]',
        xaxis_type="log",
        yaxis_type="log",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#FFFFFF',
        font=dict(color='#63627C'),
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(
        gridcolor='#EAEEF4',
        zerolinecolor='#A7B7CF',
        tickmode="array",
        tickvals=x_ticks,
        ticktext=[f"{t:g}" for t in x_ticks],
    )
    fig.update_yaxes(
        gridcolor='#EAEEF4',
        zerolinecolor='#A7B7CF',
        tickmode="array",
        tickvals=y_ticks,
        ticktext=[f"{t:g}" for t in y_ticks],
    )
    st.plotly_chart(fig, width="stretch")
    if data_source != "Generar teóricos":
        st.caption(
            f"**Amarillo** = {len(L_med)} puntos medidos en campo "
            f"(ρ {float(np.max(rho_med)):.2g}→{float(np.min(rho_med)):.2g} Ω·m). "
            f"**Azul** = respuesta teórica del modelo de capas (no es otra lectura del archivo)."
        )
    else:
        st.caption(f"Curva teórica generada ({len(L_med)} puntos). Fuente: {data_source}.")
    # === TABLA DE RESULTADOS ===
    st.subheader("Resultados y Error")
    fit_report = assess_fit(L_med, rho_med, rho_calc)
    df_results = fit_report.results_df
    st.session_state['sev_results_df'] = df_results

    if fit_report.accepted and fit_report.strict_accepted:
        st.success(
            f"Ajuste ACEPTADO: error promedio {fit_report.mean_error_pct:.2f} % "
            f"(≤ {ACCEPTANCE_ERROR_PCT:.0f} %) y los {fit_report.n_points} puntos cumplen."
        )
    elif fit_report.accepted:
        st.warning(
            f"Ajuste ACEPTADO con reservas: promedio {fit_report.mean_error_pct:.2f} % "
            f"(≤ {ACCEPTANCE_ERROR_PCT:.0f} %), pero {fit_report.n_over_threshold} punto(s) lo superan "
            f"(máximo {fit_report.max_error_pct:.2f} %)."
        )
    else:
        st.error(
            f"Ajuste RECHAZADO: error promedio {fit_report.mean_error_pct:.2f} % "
            f"supera el {ACCEPTANCE_ERROR_PCT:.0f} % permitido "
            f"(máximo {fit_report.max_error_pct:.2f} %, "
            f"{fit_report.n_over_threshold}/{fit_report.n_points} puntos fuera de tolerancia)."
        )

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("RMSE (Ω·m)", f"{fit_report.rmse_linear:.2f}")
    col_m2.metric("R² en escala log", f"{fit_report.r2_log:.4f}")
    col_m3.metric(
        f"Error prom. (≤{ACCEPTANCE_ERROR_PCT:.0f}%)",
        f"{fit_report.mean_error_pct:.2f} %",
        delta=f"{fit_report.mean_error_pct - ACCEPTANCE_ERROR_PCT:.2f} %",
        delta_color="inverse" if fit_report.mean_error_pct > ACCEPTANCE_ERROR_PCT else "normal",
    )
    col_m4.metric(
        "Error máximo",
        f"{fit_report.max_error_pct:.2f} %",
        delta=f"{fit_report.max_error_pct - ACCEPTANCE_ERROR_PCT:.2f} %",
        delta_color="inverse",
    )
    st.caption(
        "Verde en la tabla = punto dentro del 5 % · Rojo = fuera de tolerancia. "
        "«Error log (%)» complementa la lectura en curvas log-log."
    )
    ref_bench = None
    if st.session_state.get("sev_import_panel"):
        ref_bench = st.session_state["sev_import_panel"].get("reference_benchmark")
    if ref_bench is not None:
        bench_delta = fit_report.mean_error_pct - ref_bench["mean_error_pct"]
        st.info(
            f"Comparación con referencia del CSV: tu error prom. {fit_report.mean_error_pct:.2f} % "
            f"vs referencia {ref_bench['mean_error_pct']:.2f} % "
            f"({'mejor' if bench_delta < -0.05 else 'similar' if abs(bench_delta) <= 0.1 else 'peor'} "
            f"por {abs(bench_delta):.2f} p.p.)."
        )
    st.dataframe(style_results_table(df_results), width="stretch")
    # === EXPORTAR ===
    st.subheader("Exportar Resultados")
    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        csv = df_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Descargar tabla (CSV)",
            csv,
            "resultados_sev.csv",
            "text/csv",
            key='download-csv'
        )
    with col_e2:
        params_dict = {
            "n_layers": len(st.session_state.rho),
            "rho": st.session_state.rho,
            "h": st.session_state.h,
            "fit_accepted": fit_report.accepted,
            "fit_mean_error_pct": fit_report.mean_error_pct,
        }
        json_str = json.dumps(params_dict, indent=4)
        st.download_button(
            "Descargar modelo (JSON)",
            json_str,
            "modelo_sev.json",
            "application/json"
        )
    with col_e3:
        ref_note = ""
        if ref_bench is not None:
            ref_note = (
                f"Referencia CSV: error prom. {ref_bench['mean_error_pct']:.2f} % "
                f"(tu ajuste {fit_report.mean_error_pct:.2f} %)."
            )
        pdf_bytes = build_sev_pdf_report(
            filename=active_dataset.get("filename", ""),
            col_l=active_dataset.get("col_l", ""),
            col_rho=active_dataset.get("col_rho", ""),
            L_med=L_med,
            rho_med=rho_med,
            rho_calc=rho_calc,
            rho_layers=list(st.session_state.rho),
            h_layers=list(st.session_state.h),
            fit=fit_report,
            curve_type=model_report.get("curve_type", ""),
            reference_note=ref_note,
        )
        st.download_button(
            "Descargar informe (PDF)",
            pdf_bytes,
            "informe_sev.pdf",
            "application/pdf",
            key="download-pdf-report",
        )
    # Sección transversal del terreno
    st.subheader("Sección Geoeléctrica")
    fig_bar = go.Figure()
    # Para el gráfico, limitamos la profundidad de la última capa a un 30% del espesor total
    total_h = sum(st.session_state.h) if len(st.session_state.h) > 0 else 10.0
    last_h = total_h * 0.3 if total_h > 0 else 10.0
    h_plot = list(st.session_state.h) + [last_h]
    depths = [0]
    for h_val in h_plot:
        depths.append(depths[-1] + h_val)
    # Dibujar barras horizontales para cada capa
    y_centers = []
    h_texts = []
    for i in range(len(st.session_state.rho)):
        y_center = -(depths[i] + depths[i+1]) / 2
        y_centers.append(y_center)
        fig_bar.add_trace(go.Bar(
            y=[0],
            x=[st.session_state.rho[i]],
            orientation='h',
            name=f'Capa {i+1} (ρ={st.session_state.rho[i]:.1f})',
            marker=dict(color='#A6A4D7', line=dict(color='#485199', width=1)),
            text=f'ρ={st.session_state.rho[i]:.1f} Ω·m<br>h={st.session_state.h[i] if i < len(st.session_state.h) else "∞"} m',
            textposition='inside',
            insidetextanchor='middle'
        ))
    fig_bar.update_layout(
        barmode='stack',
        title="Resistividades por Capa",
        xaxis_title="Resistividad [Ω·m]",
        yaxis=dict(showticklabels=False),
        height=200,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#63627C')
    )
    st.plotly_chart(fig_bar, width="stretch")

elif nav == "🏗️ Diseño Malla BT y Reporte":
    st.header("🏗️ Diseño Malla BT y Reporte")
    st.markdown("Completa los datos de tu transformador y malla para generar el reporte técnico según la rúbrica de CFT Los Ríos.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Datos del Transformador")
        marca = st.text_input("Marca / Fabricante", "Ej: Rhona")
        modelo = st.text_input("Modelo / Código Comercial", "Ej: TR-10KVA-220")
        
        tipo_trafo = st.text_input("Tipo de Transformador", "Monofásico de control")
        
        col_p, col_pu = st.columns([3, 1])
        with col_p:
            potencia_str = st.text_input("Potencia Aparente Nominal", "100")
        with col_pu:
            unidad_p = st.selectbox("Unidad S", ["VA", "kVA", "MVA"], index=0)
            
        col_vp, col_vpu = st.columns([3, 1])
        with col_vp:
            voltaje_pri_str = st.text_input("Voltaje Primario", "230")
        with col_vpu:
            unidad_vp = st.selectbox("Unidad Vp", ["V", "kV"], index=0)
            
        col_vs, col_vsu = st.columns([3, 1])
        with col_vs:
            voltaje_sec_str = st.text_input("Voltaje Secundario", "24")
        with col_vsu:
            unidad_vs = st.selectbox("Unidad Vs", ["V", "kV"], index=0)
        
        frecuencia = st.text_input("Frecuencia Nominal (Hz)", "50 (rango 47-63)")
        refrigeracion = st.text_input("Tipo de Refrigeración", "Natural por aire (seco)")
        
        st.markdown("**Pérdidas e Información Adicional**")
        perdidas_vacio = st.text_input("Pérdidas en Vacío (W)", "6,7")
        perdidas_carga = st.text_input("Pérdidas en Carga (W)", "~13,8")
        eficiencia = st.text_input("Eficiencia / Rendimiento (%)", "83")
        aplicacion = st.text_input("Aplicación Principal", "Bobinas, PLC, señalización")
        
        # Cálculos de corriente
        st.markdown("---")
        st.markdown("**Cálculos Eléctricos Automáticos**")
        fase_calc = st.radio("Sistema para cálculos eléctricos", ["Monofásico/Bifásico", "Trifásico"])
        
        def extract_float(text):
            import re
            match = re.search(r"[-+]?\d*[.,]?\d+", text)
            if match:
                return float(match.group().replace(',', '.'))
            return 0.0
            
        S_val = extract_float(potencia_str)
        if unidad_p == "kVA": S_va = S_val * 1000.0
        elif unidad_p == "MVA": S_va = S_val * 1000000.0
        else: S_va = S_val
        
        V_pri_val = extract_float(voltaje_pri_str)
        V_pri = V_pri_val * 1000.0 if unidad_vp == "kV" else V_pri_val
        
        V_sec_val = extract_float(voltaje_sec_str)
        V_sec = V_sec_val * 1000.0 if unidad_vs == "kV" else V_sec_val
        
        if V_pri > 0:
            I_pri = S_va / (np.sqrt(3) * V_pri) if fase_calc == "Trifásico" else S_va / V_pri
        else: I_pri = 0.0
        
        if V_sec > 0:
            I_sec = S_va / (np.sqrt(3) * V_sec) if fase_calc == "Trifásico" else S_va / V_sec
        else: I_sec = 0.0
            
        st.info(f"Corriente Nominal Primaria: **{I_pri:.2f} A**\\n\\nCorriente Nominal Secundaria: **{I_sec:.2f} A**")
        
    with col2:
        st.subheader("2. Diseño Simplificado de Malla BT")
        
        # Extraer resistividad de diseño
        if 'rho' in st.session_state and len(st.session_state.rho) > 0:
            rho_def = float(st.session_state.rho[0])
            st.success("✅ Datos SEV detectados. Se ha importado la resistividad del terreno (Capa 1).")
        else:
            rho_def = 100.0
            st.warning("⚠️ No se detectaron datos SEV. Ingresa la resistividad manualmente.")
            
        rho_diseno = st.number_input("Resistividad de Diseño (ρ en Ω·m)", min_value=0.1, value=rho_def, help="Valor adoptado a partir del modelo SEV (usualmente la Capa 1).")
        
        largo = st.number_input("Largo de la malla (L en m)", min_value=1.0, value=5.0)
        ancho = st.number_input("Ancho de la malla (W en m)", min_value=1.0, value=5.0)
        separacion = st.number_input("Separación entre conductores (D en m)", min_value=0.5, value=1.0)
        profundidad = st.number_input("Profundidad de enterramiento (h en m)", min_value=0.1, value=0.6)
        
        n_barras = st.number_input("Cantidad de barras/electrodos verticales", min_value=0, value=0, step=1)
        longitud_barra = st.number_input("Longitud de cada barra vertical (m)", min_value=0.5, value=1.5) if n_barras > 0 else 0.0
        diametro_barra = st.number_input("Diámetro de las barras (mm)", min_value=1.0, value=16.0) if n_barras > 0 else 0.0
        
        R_objetivo = st.number_input("Resistencia Objetivo (Ω)", min_value=0.1, value=10.0, help="Ej: < 10 Ω o < 5 Ω para BT")
        
        # Cálculos Malla
        st.markdown("---")
        st.markdown("**Cálculos y Resultados de la Malla**")
        
        if separacion > min(largo, ancho):
            st.error(f"Error: La separación D ({separacion} m) no puede ser mayor que las dimensiones de la malla.")
            Rg = 0.0
            n_L = n_W = 0
            Lt = 0.0
            area = largo * ancho
            L_barras = 0.0
        else:
            n_L = int(ancho / separacion) + 1
            n_W = int(largo / separacion) + 1
            Lt = n_L * largo + n_W * ancho
            area = largo * ancho
            L_barras = n_barras * longitud_barra
            
            # Formula Laurent-Niemann
            if Lt > 0 and area > 0:
                Rg = rho_diseno / (4.0 * np.sqrt(area)) + rho_diseno / Lt
                
                # Formula con corrección por profundidad (Aproximación Sverak simple)
                Rg_prof = rho_diseno * (1.0 / Lt + 1.0 / np.sqrt(20.0 * area) * (1 + 1.0 / (1 + profundidad * np.sqrt(20.0 / area))))
                
                col_m1, col_m2 = st.columns(2)
                col_m1.metric("Área de la Malla (A)", f"{area:.2f} m²")
                col_m1.metric("Longitud Horizontal ($L_T$)", f"{Lt:.2f} m")
                col_m2.metric("Longitud Vertical", f"{L_barras:.2f} m")
                col_m2.metric("Resistencia Calculada ($R_g$)", f"{Rg:.2f} Ω", 
                              f"{Rg - R_objetivo:.2f} Ω vs Obj", 
                              delta_color="inverse")
                
                if Rg <= R_objetivo:
                    st.success(f"✅ ¡El diseño CUMPLE con el objetivo de {R_objetivo} Ω!")
                else:
                    st.error(f"❌ El diseño NO CUMPLE con el objetivo de {R_objetivo} Ω. Reduce la resistividad, aumenta el área o agrega conductor.")
                    
                st.caption("Fórmula usada: $R_g \\approx \\frac{\\rho}{4 \\sqrt{A}} + \\frac{\\rho}{L_T}$ (Laurent-Niemann simplificada)")
                st.caption(f"Nota: Alternativa teórica con corrección por profundidad daría: {Rg_prof:.2f} Ω")
            else:
                st.error("Dimensiones inválidas para calcular Rg.")
                Rg = 0.0
            
        # Dibujar malla
        fig_malla = go.Figure()
        
        # Lineas a lo largo de W (horizontales en el grafico, de x=0 a L)
        for i in range(n_L):
            y_pos = i * separacion
            fig_malla.add_trace(go.Scatter(x=[0, largo], y=[y_pos, y_pos], mode='lines', line=dict(color='orange', width=2)))
            
        # Lineas a lo largo de L (verticales en el grafico, de y=0 a W)
        for j in range(n_W):
            x_pos = j * separacion
            fig_malla.add_trace(go.Scatter(x=[x_pos, x_pos], y=[0, ancho], mode='lines', line=dict(color='orange', width=2)))
            
        fig_malla.update_layout(
            title="Esquema de la Malla de Puesta a Tierra",
            xaxis_title="Largo (m)",
            yaxis_title="Ancho (m)",
            width=400,
            height=400,
            showlegend=False,
            yaxis=dict(scaleanchor="x", scaleratio=1), # Cuadricula perfecta
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0.05)',
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_malla, width="stretch")

        st.markdown("---")
        st.subheader("Exportar para AutoCAD")
        st.caption(
            "Genera archivos compatibles con **MALLABTCSV** y **MALLABTJSON** "
            "(script Dibujar_Malla_BT.lsp v1.6+). Formato tabular como resultados_sev.csv."
        )

        etiqueta_default = " ".join(part for part in (marca.strip(), modelo.strip()) if part) or "Malla BT"
        etiqueta_malla = st.text_input("Etiqueta de la malla", etiqueta_default, key="malla_etiqueta")
        col_autocad_1, col_autocad_2 = st.columns(2)
        with col_autocad_1:
            modo_3d_export = st.checkbox("Modo 3D (malla enterrada)", value=False, key="malla_modo_3d")
        with col_autocad_2:
            agregar_picas_export = st.checkbox(
                "Agregar picas en esquinas",
                value=True,
                key="malla_agregar_picas",
            )

        longitud_picas_export = (
            float(longitud_barra) if n_barras > 0 else 3.0
        )

        export_valid = separacion <= min(largo, ancho) and Lt > 0 and area > 0
        if export_valid:
            malla_payload = build_malla_bt_payload(
                largo=largo,
                ancho=ancho,
                separacion=separacion,
                profundidad=profundidad,
                resistividad=rho_diseno,
                etiqueta=etiqueta_malla,
                modo_3d=modo_3d_export,
                agregar_picas=agregar_picas_export,
                longitud_picas=longitud_picas_export,
                rg=Rg,
                longitud_total=Lt,
                area=area,
            )
            col_exp_csv, col_exp_json, col_exp_full = st.columns(3)
            with col_exp_csv:
                st.download_button(
                    "Descargar malla (CSV)",
                    format_malla_bt_csv(malla_payload).encode("utf-8"),
                    "malla_bt.csv",
                    "text/csv",
                    key="download-malla-csv",
                )
            with col_exp_json:
                st.download_button(
                    "Descargar malla (JSON)",
                    format_malla_bt_json(malla_payload).encode("utf-8"),
                    "malla_bt.json",
                    "application/json",
                    key="download-malla-json",
                )
            with col_exp_full:
                sev_df = st.session_state.get("sev_results_df")
                st.download_button(
                    "Descargar estudio completo (CSV)",
                    format_malla_bt_csv_completo(malla_payload, sev_df).encode("utf-8"),
                    "estudio_malla_bt.csv",
                    "text/csv",
                    key="download-malla-csv-completo",
                    disabled=sev_df is None,
                    help="Incluye parametros de malla y tabla SEV (requiere haber analizado el sondeo).",
                )
        else:
            st.warning(
                "Corrige las dimensiones de la malla (D debe ser menor que largo y ancho) "
                "para habilitar la exportación a AutoCAD."
            )

    st.markdown("---")
    st.header("3. Generación del Reporte Técnico")
    st.markdown("Haz clic en el botón para compilar toda la información y generar el reporte en formato texto/markdown para copiar a tu procesador de textos.")
    
    if st.button("Generar Reporte", type="primary"):
        # Construir reporte
        capas_str = ""
        if 'rho' in st.session_state and len(st.session_state.rho) > 0:
            for i, (r, h) in enumerate(zip(st.session_state.rho, st.session_state.h)):
                capas_str += f"- Capa {i+1}: ρ = {r:.2f} Ω·m, h = {h:.2f} m\\n"
            if len(st.session_state.rho) > len(st.session_state.h):
                capas_str += f"- Capa {len(st.session_state.rho)}: ρ = {st.session_state.rho[-1]:.2f} Ω·m, h = ∞\\n"
            
        sqrt_3_str = "(√3 · " if tipo_trafo == "Trifásico" else ""
        close_paren_str = ")" if tipo_trafo == "Trifásico" else ""
        sqrt_3_str = "(√3 · " if fase_calc == "Trifásico" else ""
        close_paren_str = ")" if fase_calc == "Trifásico" else ""
        
        reporte = f"""# REPORTE TÉCNICO
        
## 4.3 Identificación del transformador comercial
- **Marca o fabricante:** {marca}
- **Modelo o código comercial:** {modelo}
- **Tipo de transformador:** {tipo_trafo}
- **Fuente de información:** Catálogo de fabricante / Ficha técnica

## 4.4 Datos técnicos del transformador
- **Potencia aparente nominal:** {potencia_str} {unidad_p}
- **Voltaje primario:** {voltaje_pri_str} {unidad_vp}
- **Voltaje secundario:** {voltaje_sec_str} {unidad_vs}
- **Frecuencia nominal:** {frecuencia}
- **Tipo de refrigeración:** {refrigeracion}
- **Eficiencia:** {eficiencia}%
- **Pérdidas en vacío:** {perdidas_vacio}
- **Pérdidas en carga:** {perdidas_carga}
- **Aplicación principal:** {aplicacion}

## 4.5 Cálculos eléctricos del transformador
Fórmulas utilizadas:
- Monofásico/Bifásico: `I = S / V`
- Trifásico: `I = S / (√3 · V)`

Cálculos:
- **Corriente Nominal Primaria:** {S_va} VA / {sqrt_3_str}{V_pri} V{close_paren_str} = **{I_pri:.2f} A**
- **Corriente Nominal Secundaria:** {S_va} VA / {sqrt_3_str}{V_sec} V{close_paren_str} = **{I_sec:.2f} A**

## 4.6 Aplicación técnica del transformador
- **Función principal:** Transferir energía eléctrica alterando los niveles de tensión (reductor).
- **Importancia tensión:** Permite conectar equipos BT a la red ({voltaje_pri_str}{unidad_vp} a {voltaje_sec_str}{unidad_vs}).
- **Potencia aparente ({potencia_str} {unidad_p}):** Define la carga máxima que puede soportar sin daño térmico.

## 4.7 Interpretación de pérdidas y refrigeración
- La diferencia entre pérdidas en carga ({perdidas_carga}) y vacío ({perdidas_vacio}) radica en que las de vacío (en el núcleo de hierro) son constantes mientras el equipo está energizado, y las de carga (en el cobre/devanados) varían con el cuadrado de la corriente consumida.
- El sistema de refrigeración ({refrigeracion}) es vital para disipar el calor generado por estas pérdidas y mantener la temperatura dentro de márgenes seguros para el aislamiento térmico.

## 4.8 Interpretación de resistividad del terreno (SEV)
Resultados obtenidos de la optimización del modelo IPI2Win/App:
{capas_str if capas_str else "- No se detectaron datos SEV en la sesión actual."}

La resistividad del terreno representa la oposición del suelo al paso de corriente eléctrica. Este dato es absolutamente clave para el diseño, ya que un suelo altamente resistivo obliga a construir una malla de mayores dimensiones (más conductor) para alcanzar el nivel de resistencia seguro normativo.

## 4.9 Diseño simplificado de malla de puesta a tierra BT
- **Resistividad de diseño adoptada (ρ):** {rho_diseno:.2f} Ω·m
- **Dimensiones de la malla:** {largo} m x {ancho} m (Área: {area:.2f} m²)
- **Separación entre conductores (D):** {separacion} m
- **Profundidad de enterramiento:** {profundidad} m
- **Barras verticales:** {n_barras} barras de {longitud_barra} m (Diámetro: {diametro_barra} mm)
- **Longitud total estimada de conductor horizontal ($L_T$):** {Lt:.2f} m
- **Resistencia objetivo:** {R_objetivo:.2f} Ω
- **Resistencia calculada ($R_g$) (Laurent-Niemann simplificada):** **{Rg:.2f} Ω**

## 4.10 Conclusiones técnicas
- El transformador de {potencia_str} {unidad_p} fue adecuadamente dimensionado y evaluado mediante las corrientes de operación calculadas ({I_pri:.2f} A en primario y {I_sec:.2f} A en secundario).
- La resistividad medida del terreno (ρ={rho_diseno:.2f} Ω·m) afecta de forma directa las dimensiones del sistema de puesta a tierra.
- Con el arreglo de retícula propuesto de {largo}x{ancho}m, se logra una resistencia teórica de puesta a tierra de {Rg:.2f} Ω, lo cual {"CUMPLE" if Rg <= R_objetivo else "NO CUMPLE"} con el objetivo de {R_objetivo:.2f} Ω.
- Como limitación de diseño, se utiliza una fórmula simplificada que asume un terreno homogéneo con la resistividad adoptada.
"""
        st.text_area("Copia el siguiente texto para tu informe:", value=reporte, height=400)
