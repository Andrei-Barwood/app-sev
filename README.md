# App SEV - Sondeo Eléctrico Vertical ⚡

![SEV App](https://img.shields.io/badge/Python-3.10-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red)
![License](https://img.shields.io/badge/License-Proprietary-red)

Herramienta profesional para el modelado y ajuste automático de curvas de Sondeo Eléctrico Vertical (SEV) utilizando el formalismo de Mooney-Orellana y la transformada de Hankel con el filtro digital de Ghosh. 

**Desarrollo:** Kirtan Teg Singh (ਕੀਰਤਨ ਤੇਗ ਸਿੰਘ)  
**Propietario:** snocomm  
⚠️ **PROHIBIDA SU VENTA**

## Características

- 📊 **Cálculos Precisos:** Resolución del problema directo de resistividad para arreglos Schlumberger de hasta 10 capas.
- 🎯 **Ajuste Automático:** Combinación de Evolución Diferencial (optimización global) y Mínimos Cuadrados (refinamiento local) para encontrar los mejores espesores y resistividades a partir de datos de campo.
- 💾 **Curvas de Referencia:** Diccionario precargado con curvas maestras de Mooney-Orellana (Tipo H, K, A, Q y de 2 capas).
- 📈 **Visualización Interactiva:** Gráficos Log-Log y sección geoeléctrica transversal utilizando Plotly.

## App en acción

![Herramienta SEV — gráfico log-log y ajuste de curvas](docs/screenshots/01.jpg)

![Herramienta SEV — sección geoeléctrica y modelo de capas](docs/screenshots/02.jpg)

## Descarga (binarios standalone)

**Versión actual: [v1.2.3](https://github.com/Andrei-Barwood/app-sev/releases/tag/v1.2.3)**

En [Releases](https://github.com/Andrei-Barwood/app-sev/releases) están los ejecutables listos para usar, sin instalar Python ni dependencias:

| Plataforma | Archivo |
|------------|---------|
| **Windows** | `app-sev-windows.zip` |
| **macOS** | `app-sev-macos.zip` |
| **Linux** | `app-sev-linux.tar.gz` |

> **Versiones anteriores ya no se publican.** Descarga siempre **v1.2.3**; es el mismo servicio (SEV + malla BT), con importación, optimización, modelo de capas y exportación AutoCAD corregidos.

1. Descarga el archivo de **v1.2.3** para tu sistema operativo.
2. Descomprime el archivo.

**Windows — ejecutar antes del binario:**

El ejecutable standalone usa una ventana de escritorio nativa que depende de **.NET Framework 4.8+** y **Microsoft Edge WebView2 Runtime**. Antes de abrir `AppSEV.exe`, ejecuta el script de preconfiguración incluido en el `.zip`:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1
```

El script solicitará permisos de administrador, comprobará si los componentes ya están instalados y, si faltan, los descargará e instalará automáticamente (vía `winget` o instalador directo de Microsoft).

3. Ejecuta `AppSEV.exe` (Windows) o `AppSEV` (macOS/Linux).
4. La aplicación se abrirá en una ventana de escritorio nativa.

> **Windows (instalación manual):** si prefieres no usar el script, instala [.NET Framework 4.8](https://dotnet.microsoft.com/download/dotnet-framework/net48) y [Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2) manualmente antes de abrir el ejecutable.

## Instalación Local

> **Requisito:** Python **3.10** (recomendado) con [pyenv](https://github.com/pyenv/pyenv).  
> Las versiones 3.11 y 3.12 también funcionan. **No uses Python 3.13+** para desarrollo ni builds desktop: `streamlit-desktop-app` y PyInstaller no son compatibles y el empaquetado fallará.

### Opción A — Configuración automática (recomendada)

El script `scripts/setup_env.zsh` hace todo el proceso por ti:

1. Instala Python 3.10 con pyenv (si no lo tienes).
2. Crea el entorno virtual `app-sev`.
3. Lo activa en el proyecto con `pyenv local`.
4. Instala las dependencias de `requirements.txt`.

```bash
git clone https://github.com/Andrei-Barwood/app-sev.git
cd app-sev
chmod +x scripts/setup_env.zsh
./scripts/setup_env.zsh
```

Para además instalar las dependencias de build y generar el binario desktop local:

```bash
./scripts/setup_env.zsh --build
```

Cuando termine, ejecuta la aplicación:

```bash
streamlit run app.py
```

### Opción B — Configuración manual con pyenv

Si prefieres hacerlo paso a paso:

1. Clona el repositorio:
   ```bash
   git clone https://github.com/Andrei-Barwood/app-sev.git
   cd app-sev
   ```

2. Instala Python 3.10 con pyenv:
   ```bash
   pyenv install 3.10.16
   ```

3. Crea y activa el entorno virtual:
   ```bash
   pyenv virtualenv 3.10.16 app-sev
   pyenv local app-sev
   pyenv activate app-sev
   ```

4. Instala las dependencias:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Ejecuta la aplicación:
   ```bash
   streamlit run app.py
   ```

### Construir binario desktop localmente (opcional)

Solo si necesitas generar el ejecutable en tu máquina (con Python 3.10–3.12 activo):

```bash
pip install -r requirements-build.txt
bash scripts/build_desktop.sh macos    # macOS
bash scripts/build_desktop.sh linux    # Linux
bash scripts/build_desktop.sh windows  # Windows (desde Git Bash)
```

El resultado queda en `dist/release/`. En Windows y Linux los builds multi-plataforma se generan automáticamente en GitHub Actions al publicar un tag `v*`.

## Alojamiento en Streamlit Cloud (Recomendado)
Esta aplicación está diseñada para ser hosteada de manera gratuita en **Streamlit Community Cloud**. 
1. Conecta este repositorio en tu cuenta de GitHub a [share.streamlit.io](https://share.streamlit.io).
2. Obtén la URL de tu aplicación (ej. `https://tu-app-sev.streamlit.app`).
3. (Opcional) Usa la extensión de navegador provista en los "Releases" para acceder a la app desde la barra de tareas de tu navegador con un solo clic.

## Extensión Web
En los *Releases* de este repositorio o en la carpeta `browser_extension/` encontrarás una extensión para Google Chrome/Edge que te permitirá lanzar la aplicación rápidamente. Simplemente carga la carpeta como "Extensión Descomprimida" o instala el `.zip` en tu navegador y configura la URL de tu app.