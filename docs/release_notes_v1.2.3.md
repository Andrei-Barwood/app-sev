## App SEV v1.2.3

Parche sobre **v1.2.2**. Mismo servicio (SEV + malla BT).

### Novedades

- **Modo estricto de optimización:** opción en el panel de ajuste para penalizar cada punto fuera del 5 %, no solo el error promedio. Recomendado con búsqueda global en curvas exigentes.
- **Curva de referencia del CSV:** si el archivo trae `Ro_Calculados` o `Rho Calculado`, se puede superponer en el gráfico (violeta) como referencia visual del telurómetro — distinta del modelo de capas (azul).
- **Inicialización automática con más capas:** curvas de alto contraste (p. ej. `04.csv`) arrancan con 4 capas sin pulsar el botón manual.
- **Ingreso manual depurado (tandas 3–4):** parser telurómetro, firma estable del texto, viabilidad previa y gráfico sin zigzag cuando hay advertencias de formato.

### Criterio de aceptación (sin cambios)

- **ACEPTADO:** error promedio ≤ 5 %
- **ACEPTADO con reservas:** promedio OK pero algún punto > 5 %
- **RECHAZADO:** promedio > 5 %

El modo estricto ayuda a acercarse al criterio estricto (todos los puntos), pero el veredicto oficial sigue siendo el error **promedio**.

### Versiones anteriores

Solo **v1.2.3** permanece publicada para descarga de binarios standalone.