#!/usr/bin/env zsh
# Configura automáticamente un entorno pyenv con Python 3.10 para App SEV.
# Uso:
#   ./scripts/setup_env.zsh          → instala Python, crea entorno e instala dependencias
#   ./scripts/setup_env.zsh --build  → lo anterior + dependencias de build + binario desktop
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON_VERSION="${PYTHON_VERSION:-3.10.16}"
VENV_NAME="${VENV_NAME:-app-sev}"
DO_BUILD=false

for arg in "$@"; do
  case "$arg" in
    --build) DO_BUILD=true ;;
    -h|--help)
      cat <<'EOF'
Uso: ./scripts/setup_env.zsh [--build]

  --build   Instala requirements-build.txt y genera el binario desktop local.

Variables opcionales:
  PYTHON_VERSION   Versión de Python a instalar (por defecto: 3.10.16)
  VENV_NAME        Nombre del entorno virtual pyenv (por defecto: app-sev)
EOF
      exit 0
      ;;
    *)
      echo "Opción desconocida: $arg (usa --help)" >&2
      exit 1
      ;;
  esac
done

if ! command -v pyenv &>/dev/null; then
  echo "Error: pyenv no está instalado." >&2
  echo "Instálalo desde https://github.com/pyenv/pyenv#installation" >&2
  exit 1
fi

eval "$(pyenv init - zsh)"
if command -v pyenv &>/dev/null && pyenv commands 2>/dev/null | grep -q virtualenv-init; then
  eval "$(pyenv virtualenv-init - zsh)"
fi

echo "==> Comprobando Python ${PYTHON_VERSION}..."
if ! pyenv versions --bare | grep -qx "${PYTHON_VERSION}"; then
  echo "==> Instalando Python ${PYTHON_VERSION} con pyenv (puede tardar unos minutos)..."
  pyenv install -s "${PYTHON_VERSION}"
else
  echo "    Python ${PYTHON_VERSION} ya está instalado."
fi

echo "==> Comprobando entorno virtual '${VENV_NAME}'..."
if ! pyenv versions --bare | grep -qx "${VENV_NAME}"; then
  echo "==> Creando entorno virtual '${VENV_NAME}'..."
  pyenv virtualenv "${PYTHON_VERSION}" "${VENV_NAME}"
else
  echo "    Entorno '${VENV_NAME}' ya existe."
fi

echo "==> Activando entorno en este proyecto (pyenv local)..."
pyenv local "${VENV_NAME}"

PYTHON_BIN="$(pyenv which python)"
PY_VER="$("${PYTHON_BIN}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

if [[ "${PY_VER}" != "3.10" && "${PY_VER}" != "3.11" && "${PY_VER}" != "3.12" ]]; then
  echo "Error: se requiere Python 3.10, 3.11 o 3.12 (detectado: ${PY_VER})." >&2
  exit 1
fi

echo "==> Usando: $("${PYTHON_BIN}" --version) en $(dirname "${PYTHON_BIN}")"
echo "==> Actualizando pip..."
"${PYTHON_BIN}" -m pip install --upgrade pip

echo "==> Instalando dependencias de la aplicación..."
"${PYTHON_BIN}" -m pip install -r requirements.txt

if [[ "${DO_BUILD}" == true ]]; then
  echo "==> Instalando dependencias de build desktop..."
  "${PYTHON_BIN}" -m pip install -r requirements-build.txt

  PLATFORM="$(uname -s | tr '[:upper:]' '[:lower:]')"
  case "${PLATFORM}" in
    darwin) BUILD_PLATFORM="macos" ;;
    linux)  BUILD_PLATFORM="linux" ;;
    *)      BUILD_PLATFORM="${PLATFORM}" ;;
  esac

  echo "==> Construyendo binario desktop (${BUILD_PLATFORM})..."
  bash scripts/build_desktop.sh "${BUILD_PLATFORM}"
fi

cat <<EOF

✓ Entorno listo.

  Entorno pyenv : ${VENV_NAME}
  Python        : $("${PYTHON_BIN}" --version)
  Directorio    : ${ROOT}

Para ejecutar la aplicación:
  cd ${ROOT}
  pyenv activate ${VENV_NAME}    # opcional si ya usas 'pyenv local'
  streamlit run app.py

EOF

if [[ "${DO_BUILD}" == true ]]; then
  echo "Binario desktop generado en: dist/release/"
  echo
fi