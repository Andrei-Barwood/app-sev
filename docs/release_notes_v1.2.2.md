## App SEV v1.2.2

Parche crítico sobre v1.2.1. Mismo servicio (SEV + malla BT).

### Corrección principal

- **Un solo dataset activo** (`sev_active_dataset`) alimenta vista previa, gráfico principal, modelo de capas y optimización.
- Corrige el caso en que el gráfico inferior mostraba puntos ~100 Ω·m sintéticos mientras la vista previa mostraba correctamente el CSV (p. ej. `05.csv` con ρ hasta 339 Ω·m).
- Los datos importados **persisten en memoria** entre reruns aunque el widget de archivo no se reenvíe.

### Versiones anteriores

Solo **v1.2.2** permanece publicada para descarga de binarios standalone.