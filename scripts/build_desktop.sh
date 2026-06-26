#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PLATFORM="${1:-$(uname -s | tr '[:upper:]' '[:lower:]')}"
case "$PLATFORM" in
  darwin|macos)  OUT_NAME="app-sev-macos" ;;
  linux)         OUT_NAME="app-sev-linux" ;;
  windows|mingw*) OUT_NAME="app-sev-windows" ;;
  *) echo "Plataforma no soportada: $PLATFORM"; exit 1 ;;
esac

python -m pip install -q -r requirements-build.txt

ICON_ARG=()
if [[ -f browser_extension/icons/icon128.png ]]; then
  ICON_ARG=(--icon browser_extension/icons/icon128.png)
fi

streamlit-desktop-app build desktop_entry.py \
  --name AppSEV \
  "${ICON_ARG[@]}" \
  --pyinstaller-options --onefile --noconfirm \
  --streamlit-options --theme.base=light

DIST_DIR="dist/release/$OUT_NAME"
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

if [[ "$PLATFORM" == windows* ]] || [[ "$PLATFORM" == mingw* ]]; then
  cp dist/AppSEV.exe "$DIST_DIR/"
  powershell -NoProfile -Command "Compress-Archive -Path '${DIST_DIR}' -DestinationPath 'dist/release/${OUT_NAME}.zip' -Force"
else
  cp dist/AppSEV "$DIST_DIR/"
  chmod +x "$DIST_DIR/AppSEV"
  if [[ "$PLATFORM" == darwin || "$PLATFORM" == macos ]]; then
    (cd dist/release && zip -r "${OUT_NAME}.zip" "$OUT_NAME")
  else
    (cd dist/release && tar -czf "${OUT_NAME}.tar.gz" "$OUT_NAME")
  fi
fi

echo "Build completado: dist/release/${OUT_NAME}.*"