## App SEV v1.2.0

Misma aplicación de siempre (sondeo eléctrico vertical, modelo de capas, diseño de malla BT y reporte), con correcciones importantes en importación de datos y optimización.

### Novedades

- **Importación CSV/Excel transparente:** vista previa del archivo, selectores de columnas L (AB/2) y ρ medida, y validación de coherencia del sondeo.
- **Inicialización automática del modelo de capas** a partir de la tabla importada (detector de curva H/K/A/Q y estimación de ρ y h).
- **Optimización corregida:** límites físicos y búsqueda en escala logarítmica (evita resultados absurdos en ρ y h).
- **Exportación AutoCAD:** archivos `malla_bt.csv` / `malla_bt.json` compatibles con `MALLABTCSV` / `MALLABTJSON` (Dibujar_Malla_BT.lsp).

### Descargas de esta versión

| Plataforma | Archivo |
|------------|---------|
| Windows | `app-sev-windows.zip` (incluye `setup_windows.ps1`) |
| macOS | `app-sev-macos.zip` |
| Linux | `app-sev-linux.tar.gz` |
| Extensión navegador | `release_extension_v1.2.0.zip` |

### Versiones anteriores

**v1.0, v1.1 y v1.1.1 ya no están disponibles para descarga.** Contenían errores en la lectura de CSV con varias columnas y en la optimización del modelo de capas. Si tenías una copia local antigua, reemplázala por **v1.2.0**.

El servicio sigue siendo el mismo: herramienta educativa/profesional de SEV y malla de puesta a tierra BT desarrollada por Kirtan Teg Singh (propietario: snocomm).