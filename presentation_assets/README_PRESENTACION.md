# Material de presentación · NGSIM Peachtree / AgentPy

Este paquete contiene las figuras, tablas y evidencias de la versión actual del dashboard. La ciencia está congelada: baseline validado con limitaciones, escenarios BASE/E1/E2/E3 evaluados y E1 recomendado dentro del alcance.

## Archivos principales

- [Manifest de los 17 requisitos](presentation_manifest.json): orden sugerido, fuentes, tablas, imágenes y notas de exposición.
- [Reporte de Simulación](simulation_layout_report.json): configuración, horizontes, QA de ocho combinaciones y exportaciones.
- [Auditoría de gráficas](presentation_chart_audit.json): legibilidad sin hover y trazabilidad.
- PNG de presentación: archivos de imagen en la raíz de este paquete.
- Tablas generales: carpeta `tables/`.
- Gráficas y CSV descargados desde Simulación: carpeta `simulation_exports/`.
- Especificaciones Plotly: carpeta `charts/`.

Las figuras exportadas tienen tamaño 1920×1080, salvo la captura del Canvas, que conserva sus dimensiones de captura. Las imágenes y CSV registran `source_artifact`. La captura muestra estados simulados, no trayectorias reales reproducidas.

## Uso del dashboard

El código se encuentra en el repositorio `ngsim-agentpy`, fuera de este paquete. Desde su raíz:

```bash
python -m pip install -r requirements-presentation.txt
python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8510
```

En Simulación seleccionar contexto, escenario y ventana visual. La opción predeterminada, 180 s, finaliza la demostración a 03:00. Seleccionar Completa permite ver el horizonte oficial: B1 16:09.3; B2 15:39.3.

Iniciar/Pausar/Continuar/Reiniciar y playback controlan exclusivamente estados AgentPy guardados de la seed ilustrativa 7000. No generan nuevos experimentos. Las series de esa corrida están separadas de los resultados oficiales de 30 réplicas.

## Interpretación

B1 corresponde a validación y B2 a calibración/TRAIN. E1 aumenta nominalmente el verde Through; E2 coordina la progresión SB; E3 combina ambas intervenciones. E1 mejora ambos contextos; E2/E3 dependen del contexto.

La validación conserva la declaración TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE. Permanecen los sesgos de headway y detenciones, diferencias de distribución B1 y límites de demanda cerrada; el material no constituye un plan listo para campo.

QA de interfaz guardado: 24 pruebas UI aprobadas, ocho combinaciones en Chrome y descargas PNG/CSV comprobadas. El reporte general de trabajo posterior registra 246 casos, con 2 fallos y 6 errores, y no debe confundirse con ese QA de interfaz. Los datasets originales grandes no se incluyen aquí.
