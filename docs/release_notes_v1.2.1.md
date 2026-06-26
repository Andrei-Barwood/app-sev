## App SEV v1.2.1

Parche sobre **v1.2.0**. Mismo servicio (SEV + malla BT + exportación AutoCAD), con corrección crítica del **modelo de capas**.

### Corrección principal

- **Modelo de capas estable:** los botones *Cargar curva de referencia*, *Recalcular desde CSV* y *Ajustar* ya no mezclan valores viejos de los widgets con el estado real del modelo.
- **Estado unificado** con invalidación de widgets al cambiar ρ, h o número de capas.
- **Sin optimización automática** al importar CSV (solo inicializa el modelo; el usuario decide cuándo optimizar).
- **Nuevas capas** se estiman desde los datos importados, no con valores fijos arbitrarios (100 / 10).

### Descargas

| Plataforma | Archivo |
|------------|---------|
| Windows | `app-sev-windows.zip` |
| macOS | `app-sev-macos.zip` |
| Linux | `app-sev-linux.tar.gz` |
| Extensión navegador | `release_extension_v1.2.1.zip` |

### Versiones anteriores

**v1.2.0 y anteriores ya no están disponibles para descarga.** Usa **v1.2.1** como única versión publicada de binarios standalone.