import os

with open("app.py", "r") as f:
    content = f.read()

# Dividir el contenido
parts = content.split("# === SIDEBAR ===")
header_part = parts[0]
main_part = parts[1]

# Preparar la nueva sección de navegación y tutorial
nav_code = """# === SIDEBAR Y NAVEGACIÓN ===
with st.sidebar:
    nav = st.radio("Navegación", ["📚 Tutorial y Guía de Uso", "⚡ Herramienta SEV"])
    st.markdown("---")

if nav == "📚 Tutorial y Guía de Uso":
    st.header("Tutorial de Mediciones de Tierra y Uso de la Aplicación")
    st.markdown(\"""
    Bienvenido a la herramienta profesional para **Sondeo Eléctrico Vertical (SEV)**. Esta guía te enseñará cómo realizar las mediciones en campo y cómo utilizar cada función de esta aplicación para interpretar tus datos.

    ---

    ### 📍 1. ¿Cómo realizar una medición SEV en campo?
    El Sondeo Eléctrico Vertical busca determinar la resistividad del subsuelo a diferentes profundidades. El arreglo más común es el **Schlumberger**:
    1. **Configuración de Electrodos:** Se clavan 4 electrodos alineados en el suelo. Los dos exteriores (A y B) inyectan corriente, y los dos interiores (M y N) miden la diferencia de potencial.
    2. **Expansión:** Para investigar a mayor profundidad, se aumenta progresivamente la distancia entre los electrodos de corriente (A y B), manteniendo L = AB/2.
    3. **Toma de Datos:** Para cada separación L, se anota la resistividad aparente $\\\\rho_a$ medida por el telurómetro.

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
    Define el **Número de capas** que intuyes que tiene el terreno (entre 2 y 10). Para cada capa, puedes modificar su resistividad ($\\\\rho$) y su espesor ($h$).
    - Si conoces el valor exacto de una capa (por ejemplo, por una perforación previa), marca la casilla **"Fijar"** para que el algoritmo no la modifique durante la optimización.

    #### Paso 4: Optimización Automática
    Haz clic en el botón azul **"Ajustar automáticamente"**. 
    La aplicación utilizará un algoritmo avanzado en dos pasos (*Evolución Diferencial* + *Mínimos Cuadrados*) para encontrar la combinación perfecta de resistividades y espesores que mejor se adapte a tus datos de campo.

    #### Paso 5: Analizar y Exportar
    - Observa el **Gráfico Principal** (escala log-log) para verificar visualmente el ajuste entre tus puntos (amarillos) y la curva teórica (línea azul oscuro).
    - Revisa la **Sección Geoeléctrica** debajo para ver un perfil de cómo está estructurado tu terreno.
    - Utiliza los botones de **Exportar Resultados** para descargar tu tabla de errores en Excel/CSV o guardar el modelo en formato JSON para uso futuro.
    \""")

elif nav == "⚡ Herramienta SEV":
"""

# Indentar el código de main_part original
indented_main = ""
for line in main_part.splitlines(True):
    if line.strip() == "":
        indented_main += "\\n"
    else:
        # El bloque "with st.sidebar:" original necesita estar indentado
        indented_main += "    " + line

new_content = header_part + nav_code + indented_main

with open("app.py", "w") as f:
    f.write(new_content)
