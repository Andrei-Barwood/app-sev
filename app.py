import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import json

from core import calc_rho_a
from optimizer import run_optimization

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
    - **Cargar archivo:** Sube un CSV o Excel con dos columnas: `L (AB/2)` y `Rho_med`.
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
        data_source = st.radio("Fuente de datos:", ["Generar teóricos", "Cargar archivo (CSV/Excel)", "Ingreso manual"])
        L_med = None
        rho_med = None
        if data_source == "Generar teóricos":
            l_min = st.number_input("L inicial (m)", min_value=0.1, value=1.0)
            l_max = st.number_input("L final (m)", min_value=1.0, value=1000.0)
            pts_dec = st.number_input("Puntos por década", min_value=3, value=10)
            decades = np.log10(l_max) - np.log10(l_min)
            num_pts = int(decades * pts_dec) + 1
            L_med = np.logspace(np.log10(l_min), np.log10(l_max), num_pts)
        elif data_source == "Cargar archivo (CSV/Excel)":
            uploaded_file = st.file_uploader("Sube tu archivo", type=['csv', 'txt', 'xlsx', 'xls'])
            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith('.csv') or uploaded_file.name.endswith('.txt'):
                        try:
                            # 1. Intentamos leerlo asumiendo que viene de Excel español (separado por Tabuladores o Punto y Coma)
                            # Usamos regex [;\t] para separar. Esto evita que los decimales con coma confundan al parser.
                            df_upload = pd.read_csv(uploaded_file, sep=r'[;\t]', engine='python')
                            
                            # Si no se separó en al menos 2 columnas, asumimos que es un CSV tradicional (separado por comas)
                            if df_upload.shape[1] < 2:
                                uploaded_file.seek(0)
                                df_upload = pd.read_csv(uploaded_file, sep=None, engine='python')
                        except Exception:
                            uploaded_file.seek(0)
                            df_upload = pd.read_csv(uploaded_file, sep=None, engine='python')
                    else:
                        df_upload = pd.read_excel(uploaded_file)
                        
                    # Buscamos inteligentemente las dos primeras columnas que contengan datos numéricos reales
                    # Esto ignora columnas vacías al principio (muy común al exportar desde Excel)
                    valid_cols = []
                    for col in df_upload.columns:
                        temp_col = pd.to_numeric(df_upload[col].astype(str).str.replace(',', '.'), errors='coerce')
                        if temp_col.notna().sum() > 0:
                            valid_cols.append(col)
                        if len(valid_cols) == 2:
                            break
                            
                    if len(valid_cols) < 2:
                        raise ValueError("No se encontraron dos columnas con datos numéricos válidos en el archivo.")
                        
                    col1, col2 = valid_cols[0], valid_cols[1]
                    
                    # Limpiamos strings, reemplazamos comas decimales por puntos y forzamos a numérico
                    df_upload[col1] = pd.to_numeric(df_upload[col1].astype(str).str.replace(',', '.'), errors='coerce')
                    df_upload[col2] = pd.to_numeric(df_upload[col2].astype(str).str.replace(',', '.'), errors='coerce')
                    
                    # Eliminamos filas que hayan resultado en NaN (nulos o strings inválidos)
                    df_upload = df_upload.dropna(subset=[col1, col2])
                    
                    if len(df_upload) == 0:
                        raise ValueError(f"Las columnas detectadas ({col1} y {col2}) no tienen datos en las mismas filas, o los datos son inválidos. Asegúrate de que L y Rho estén lado a lado.")
                    
                    L_med = df_upload[col1].values
                    rho_med = df_upload[col2].values
                    st.success("Archivo cargado correctamente.")
                    
                    # Flujo Automático: Si es un archivo nuevo, marcamos para auto-optimizar
                    if st.session_state.get('last_uploaded_csv') != uploaded_file.name:
                        st.session_state['last_uploaded_csv'] = uploaded_file.name
                        st.session_state['auto_optimize_pending'] = True
                except Exception as e:
                    st.error(f"Error al leer el archivo: {e}")
        elif data_source == "Ingreso manual":
            st.write("Formato: L, Rho_med (un punto por línea)")
            manual_data = st.text_area("Datos", "1.0, 100\n3.0, 80\n10.0, 50\n30.0, 60\n100.0, 120")
            try:
                import re
                lines = manual_data.strip().split('\n')
                parsed_data = []
                for line in lines:
                    # Extraer todos los números de la línea (soporta puntos o comas decimales)
                    nums = re.findall(r'[-+]?\d+(?:[.,]\d+)?', line)
                    if len(nums) >= 2:
                        val1 = float(nums[0].replace(',', '.'))
                        val2 = float(nums[1].replace(',', '.'))
                        parsed_data.append([val1, val2])
                
                if len(parsed_data) == 0:
                    raise ValueError("No se encontraron números válidos")
                    
                data = np.array(parsed_data)
                L_med = data[:, 0]
                rho_med = data[:, 1]
            except Exception as e:
                st.error("Error en formato de datos. Asegúrate de ingresar números válidos para L y Rho.")
        st.header("2. Curvas de Referencia (Mooney-Orellana)")
        
        # Analizar los datos para sugerir el tipo de curva
        suggested_index = 0
        if rho_med is not None and len(rho_med) >= 4:
            # Suavizado básico (media móvil) para ignorar picos de ruido
            smoothed = np.convolve(rho_med, np.ones(3)/3, mode='valid') if len(rho_med) >= 5 else rho_med
            
            idx_max = np.argmax(smoothed)
            idx_min = np.argmin(smoothed)
            n = len(smoothed)
            margin = max(1, int(n * 0.15)) # Ignoramos los extremos (15% inicial y final)
            
            keys_list = list(MOONEY_ORELLANA_REF.keys())
            suggested_key = None
            
            # ¿Hay una montaña en el medio?
            if margin <= idx_max <= n - 1 - margin:
                suggested_key = "3 Capas - Tipo K (Máximo) ρ1<ρ2>ρ3"
            # ¿Hay un valle en el medio?
            elif margin <= idx_min <= n - 1 - margin:
                suggested_key = "3 Capas - Tipo H (Mínimo) ρ1>ρ2<ρ3"
            else:
                # Si no hay picos ni valles claros en el centro, vemos la tendencia
                if smoothed[-1] > smoothed[0]:
                    suggested_key = "3 Capas - Tipo A (Ascendente) ρ1<ρ2<ρ3"
                else:
                    suggested_key = "3 Capas - Tipo Q (Descendente) ρ1>ρ2>ρ3"
                    
            if suggested_key and suggested_key in keys_list:
                suggested_index = keys_list.index(suggested_key)
                st.info(f"💡 **Sugerencia de la App:** Según la forma de tus datos, tu terreno parece coincidir con una curva **{suggested_key.split(' - ')[1]}**.")
                
                # Auto-cargar la curva si venimos de un archivo nuevo
                if st.session_state.get('auto_optimize_pending', False):
                    # Inyectar una estimación inteligente basada en los datos reales
                    # para que el Refinamiento Local comience MUY cerca de la solución real
                    rho1_smart = max(0.1, float(smoothed[0]))
                    rho3_smart = max(0.1, float(smoothed[-1]))
                    
                    if "Tipo K" in suggested_key:
                        rho2_smart = max(0.1, float(np.max(smoothed)) * 1.5)
                    elif "Tipo H" in suggested_key:
                        rho2_smart = max(0.1, float(np.min(smoothed)) * 0.5)
                    else:
                        rho2_smart = max(0.1, float((rho1_smart + rho3_smart) / 2.0))
                        
                    st.session_state.rho = [rho1_smart, rho2_smart, rho3_smart]
                    # Espesores iniciales razonables aproximados de L
                    st.session_state.h = [max(0.1, float(L_med[1])), max(0.1, float(L_med[-3]))] if len(L_med) > 4 else [2.0, 10.0]
                    
                    st.session_state.fixed_rho = [False] * len(st.session_state.rho)
                    st.session_state.fixed_h = [False] * len(st.session_state.h)
                    
                    # Forzar a los widgets a tomar los nuevos valores limpiando su estado interno
                    for k in list(st.session_state.keys()):
                        if k.startswith("rho_") or k.startswith("h_") or k.startswith("frho_") or k.startswith("fh_"):
                            del st.session_state[k]
                
        ref_choice = st.selectbox("Seleccionar modelo base:", list(MOONEY_ORELLANA_REF.keys()), index=suggested_index)
        if st.button("Cargar Curva de Referencia"):
            if ref_choice != "Personalizado":
                st.session_state.rho = MOONEY_ORELLANA_REF[ref_choice]["rho"].copy()
                st.session_state.h = MOONEY_ORELLANA_REF[ref_choice]["h"].copy()
                st.session_state.fixed_rho = [False] * len(st.session_state.rho)
                st.session_state.fixed_h = [False] * len(st.session_state.h)
                
                # Forzar a los widgets a tomar los nuevos valores
                for k in list(st.session_state.keys()):
                    if k.startswith("rho_") or k.startswith("h_") or k.startswith("frho_") or k.startswith("fh_"):
                        del st.session_state[k]
                st.rerun()
        st.header("3. Modelo de Capas")
        # Manejar cambios en el número de capas conservando datos si es posible
        n_layers = st.number_input("Número de capas", min_value=2, max_value=10, value=len(st.session_state.rho))
        if n_layers != len(st.session_state.rho):
            if n_layers > len(st.session_state.rho):
                st.session_state.rho.extend([100.0] * (n_layers - len(st.session_state.rho)))
                st.session_state.h.extend([10.0] * (n_layers - 1 - len(st.session_state.h)))
                st.session_state.fixed_rho.extend([False] * (n_layers - len(st.session_state.fixed_rho)))
                st.session_state.fixed_h.extend([False] * (n_layers - 1 - len(st.session_state.fixed_h)))
            else:
                st.session_state.rho = st.session_state.rho[:n_layers]
                st.session_state.h = st.session_state.h[:n_layers-1]
                st.session_state.fixed_rho = st.session_state.fixed_rho[:n_layers]
                st.session_state.fixed_h = st.session_state.fixed_h[:n_layers-1]
            
            # Limpiar widgets obsoletos
            for k in list(st.session_state.keys()):
                if k.startswith("rho_") or k.startswith("h_") or k.startswith("frho_") or k.startswith("fh_"):
                    del st.session_state[k]
            st.rerun()
        st.markdown("---")
        # Inputs para parámetros
        for i in range(n_layers):
            st.write(f"**Capa {i+1}**")
            col1, col2 = st.columns(2)
            with col1:
                val_rho = max(0.1, float(st.session_state.rho[i]))
                st.session_state.rho[i] = st.number_input(f"ρ_{i+1} (Ω·m)", min_value=0.1, value=val_rho, key=f"rho_{i}")
                st.session_state.fixed_rho[i] = st.checkbox("Fijar ρ", value=st.session_state.fixed_rho[i], key=f"frho_{i}")
            with col2:
                if i < n_layers - 1:
                    val_h = max(0.1, float(st.session_state.h[i]))
                    st.session_state.h[i] = st.number_input(f"h_{i+1} (m)", min_value=0.1, value=val_h, key=f"h_{i}")
                    st.session_state.fixed_h[i] = st.checkbox("Fijar h", value=st.session_state.fixed_h[i], key=f"fh_{i}")
                else:
                    st.write("h = ∞")
        st.header("4. Optimización")
        opt_method = st.radio("Método de Ajuste:", ["Refinamiento Local (Recomendado)", "Búsqueda Global (Automático)"], help="El Refinamiento Local usa tus valores manuales como punto de partida. La Búsqueda Global ignora tus valores y explora desde cero.")
        
        # Botón normal de ajuste
        run_opt = st.button("Ajustar", type="primary")
        
        # Disparo automático si viene de una nueva carga de archivo
        if st.session_state.get('auto_optimize_pending', False):
            run_opt = True
            st.session_state['auto_optimize_pending'] = False # Limpiar la bandera
            
        if 'opt_success_msg' in st.session_state:
            st.success(st.session_state['opt_success_msg'])
            del st.session_state['opt_success_msg']
        if 'opt_error_msg' in st.session_state:
            st.error(st.session_state['opt_error_msg'])
            del st.session_state['opt_error_msg']
            
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
    if L_med is None or len(L_med) == 0:
        st.warning("Por favor ingresa datos de L para continuar.")
        st.stop()
    # Si no hay datos medidos (modo teóricos), generamos unos dummy
    if rho_med is None:
        # Usamos el modelo actual para generar datos
        rho_med = calc_rho_a(L_med, st.session_state.rho, st.session_state.h)
    if run_opt:
        with st.spinner("Optimizando modelo... (esto puede tardar unos segundos)"):
            try:
                use_global = (opt_method == "Búsqueda Global (Automático)")
                best_rho, best_h, rmse, r2 = run_optimization(
                    L_med, rho_med, 
                    st.session_state.rho, st.session_state.h,
                    st.session_state.fixed_rho, st.session_state.fixed_h,
                    use_global=use_global
                )
                st.session_state.rho = list(best_rho)
                st.session_state.h = list(best_h)
                
                # Actualizar el estado de los widgets para que la UI los muestre
                for k in list(st.session_state.keys()):
                    if k.startswith("rho_") or k.startswith("h_"):
                        del st.session_state[k]
                
                st.session_state['opt_success_msg'] = f"Optimización finalizada. RMSE: {rmse:.2f} | R²: {r2:.4f}"
                st.rerun()
            except Exception as e:
                st.session_state['opt_error_msg'] = f"Error en la optimización: {e}"
                st.rerun()
    # Calcular curva teórica con los parámetros actuales
    rho_calc = calc_rho_a(L_med, st.session_state.rho, st.session_state.h)
    # === PLOT ===
    fig = go.Figure()
    # Datos medidos
    if data_source != "Generar teóricos":
        fig.add_trace(go.Scatter(
            x=L_med, y=rho_med,
            mode='markers',
            name='Datos Medidos',
            marker=dict(color='#FFFFB8', size=8, line=dict(color='#63627C', width=1.5))
        ))
    # Curva teórica
    # Generamos una curva teórica más suave si es necesario, pero usaremos L_med para coincidir puntos
    # Para que la curva se vea bien, agregamos puntos interpolados
    L_smooth = np.logspace(np.log10(min(L_med)), np.log10(max(L_med)), 100)
    rho_smooth = calc_rho_a(L_smooth, st.session_state.rho, st.session_state.h)
    fig.add_trace(go.Scatter(
        x=L_smooth, y=rho_smooth,
        mode='lines',
        name='Curva Teórica',
        line=dict(color='#485199', width=3)
    ))
    fig.update_layout(
        title='Curva de Sondeo Eléctrico Vertical',
        xaxis_title='Distancia L (AB/2) [m]',
        yaxis_title='Resistividad Aparente [Ω·m]',
        xaxis_type="log",
        yaxis_type="log",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#FFFFFF',
        font=dict(color='#63627C'),
        height=500
    )
    fig.update_xaxes(gridcolor='#EAEEF4', zerolinecolor='#A7B7CF')
    fig.update_yaxes(gridcolor='#EAEEF4', zerolinecolor='#A7B7CF')
    st.plotly_chart(fig, use_container_width=True)
    # === TABLA DE RESULTADOS ===
    st.subheader("Resultados y Error")
    df_results = pd.DataFrame({
        'L (AB/2) [m]': L_med,
        'Rho Medido [Ω·m]': rho_med,
        'Rho Calculado [Ω·m]': rho_calc,
    })
    df_results['Error (%)'] = np.abs((df_results['Rho Medido [Ω·m]'] - df_results['Rho Calculado [Ω·m]']) / df_results['Rho Medido [Ω·m]']) * 100
    col_m1, col_m2, col_m3 = st.columns(3)
    rmse_current = np.sqrt(np.mean((rho_med - rho_calc)**2))
    col_m1.metric("RMSE Actual", f"{rmse_current:.2f}")
    col_m2.metric("Error Promedio", f"{df_results['Error (%)'].mean():.2f} %")
    col_m3.metric("Error Máximo", f"{df_results['Error (%)'].max():.2f} %")
    st.dataframe(df_results.style.format("{:.2f}"))
    # === EXPORTAR ===
    st.subheader("Exportar Resultados")
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        # CSV Export
        csv = df_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Descargar tabla (CSV)",
            csv,
            "resultados_sev.csv",
            "text/csv",
            key='download-csv'
        )
    with col_e2:
        # Parámetros Export (JSON)
        params_dict = {
            "n_layers": len(st.session_state.rho),
            "rho": st.session_state.rho,
            "h": st.session_state.h
        }
        json_str = json.dumps(params_dict, indent=4)
        st.download_button(
            "Descargar modelo (JSON)",
            json_str,
            "modelo_sev.json",
            "application/json"
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
    st.plotly_chart(fig_bar, use_container_width=True)

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
        
        # Cálculos Malla
        st.markdown("---")
        st.markdown("**Cálculos de la Malla**")
        
        n_L = int(ancho / separacion) + 1
        n_W = int(largo / separacion) + 1
        Lt = n_L * largo + n_W * ancho
        area = largo * ancho
        
        st.write(f"- Conductores paralelos al largo: **{n_L}**")
        st.write(f"- Conductores paralelos al ancho: **{n_W}**")
        st.write(f"- Longitud total de conductor horizontal ($L_T$): **{Lt:.2f} m**")
        st.write(f"- Área de la malla ($A$): **{area:.2f} m²**")
        
        # Formula Laurent-Niemann
        if Lt > 0 and area > 0:
            Rg = rho_diseno * (1.0 / Lt + 1.0 / np.sqrt(20.0 * area))
            st.info(f"Resistencia estimada de la Malla ($R_g$): **{Rg:.2f} Ω**\\n\\n*(Fórmula de Laurent y Niemann)*")
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
        st.plotly_chart(fig_malla, use_container_width=True)

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
- **Cantidad de barras verticales:** {n_barras}
- **Longitud total estimada de conductor horizontal ($L_T$):** {Lt:.2f} m
- **Resistencia calculada ($R_g$) (Fórmula de Laurent y Niemann):** **{Rg:.2f} Ω**

## 4.10 Conclusiones técnicas
- El transformador de {potencia_str} {unidad_p} fue adecuadamente dimensionado y evaluado mediante las corrientes de operación calculadas ({I_pri:.2f} A en primario y {I_sec:.2f} A en secundario).
- La resistividad medida del terreno (ρ={rho_diseno:.2f} Ω·m) afecta de forma directa las dimensiones del sistema de puesta a tierra.
- Con el arreglo de retícula propuesto de {largo}x{ancho}m, se logra una resistencia teórica de puesta a tierra de {Rg:.2f} Ω.
- Como limitación de diseño, se utiliza una fórmula simplificada (Laurent-Niemann) que asume un terreno homogéneo con la resistividad adoptada.
"""
        st.text_area("Copia el siguiente texto para tu informe:", value=reporte, height=400)
